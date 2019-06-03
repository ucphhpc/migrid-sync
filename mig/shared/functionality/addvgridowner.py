#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addvgridowner - add one or more vgrid owners
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Add one or more owners to a vgrid"""

from binascii import unhexlify
import os

from shared.accessrequests import delete_access_request
from shared.base import client_id_dir, distinguished_name_to_user
from shared.defaults import any_protocol, csrf_field
from shared.fileio import make_symlink
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from shared.init import initialize_main_variables, find_entry
from shared.safeeval import subprocess_popen, subprocess_pipe, \
    subprocess_stdout
from shared.useradm import expand_openid_alias, get_full_user_map
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
    vgrid_is_member, vgrid_list_subvgrids, vgrid_add_owners, \
    vgrid_list_parents, allow_owners_adm, vgrid_manage_allowed
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'cert_id': REJECT_UNSET,
                'request_name': [''], 'rank': ['']}
    return ['text', defaults]


def add_tracker_admin(configuration, cert_id, vgrid_name, tracker_dir,
                      output_objects):
    """Add new Trac issue tracker owner"""
    cgi_tracker_var = os.path.join(tracker_dir, 'var')
    if not os.path.isdir(cgi_tracker_var):
        output_objects.append(
            {'object_type': 'text', 'text':
             'No tracker (%s) for %s %s - skipping tracker admin rights'
             % (tracker_dir, configuration.site_vgrid_label, vgrid_name)
             })
        return False

    # Trac requires tweaking for certain versions of setuptools
    # http://trac.edgewall.org/wiki/setuptools
    admin_env = {}
    # strip non-string args from env to avoid wsgi execv errors like
    # http://stackoverflow.com/questions/13213676
    for (key, val) in os.environ.items():
        if isinstance(val, basestring):
            admin_env[key] = val
    admin_env["PKG_RESOURCES_CACHE_ZIP_MANIFESTS"] = "1"

    try:
        admin_user = distinguished_name_to_user(cert_id)
        admin_id = admin_user.get(configuration.trac_id_field, 'unknown_id')
        # Give admin rights to owner using trac-admin command:
        # trac-admin tracker_dir deploy cgi_tracker_bin
        perms_cmd = [configuration.trac_admin_path, cgi_tracker_var,
                     'permission', 'add', admin_id, 'TRAC_ADMIN']
        configuration.logger.info('provide admin rights to owner: %s' %
                                  perms_cmd)
        # NOTE: We already verified command variables to be shell-safe
        proc = subprocess_popen(perms_cmd, stdout=subprocess_pipe,
                                stderr=subprocess_stdout, env=admin_env)
        proc.wait()
        if proc.returncode != 0:
            raise Exception("tracker permissions %s failed: %s (%d)" %
                            (perms_cmd, proc.stdout.read(),
                             proc.returncode))
        return True
    except Exception, exc:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Could not give %s tracker admin rights: %s' % (cert_id, exc)
             })
        return False


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Add %s Owner" % label
    output_objects.append(
        {'object_type': 'header', 'text': 'Add %s Owner(s)' % label})
    status = returnvalues.OK
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    vgrid_name = accepted['vgrid_name'][-1].strip()
    cert_id_list = accepted['cert_id']
    request_name = unhexlify(accepted['request_name'][-1])
    rank_list = accepted['rank'] + ['' for _ in cert_id_list]
    # inherited vgrid membership
    inherit_vgrid_member = False

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    # Optional site-wide limitation of manage vgrid permission
    if not user_dict or \
            not vgrid_manage_allowed(configuration, user_dict):
        logger.warning("user %s is not allowed to manage vgrids!" % client_id)
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Only privileged users can manage %ss' % label})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # make sure vgrid settings allow this owner to edit owners

    (allow_status, allow_msg) = allow_owners_adm(configuration, vgrid_name,
                                                 client_id)
    if not allow_status:
        output_objects.append({'object_type': 'error_text', 'text': allow_msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    cert_id_added = []
    for (cert_id, rank_str) in zip(cert_id_list, rank_list):
        cert_id = cert_id.strip()
        cert_dir = client_id_dir(cert_id)
        try:
            rank = int(rank_str)
        except ValueError:
            rank = None

        # Allow openid alias as subject if openid with alias is enabled
        if configuration.user_openid_providers and configuration.user_openid_alias:
            cert_id = expand_openid_alias(cert_id, configuration)

        # Validity of user and vgrid names is checked in this init function so
        # no need to worry about illegal directory traversal through variables

        (ret_val, msg, _) = \
            init_vgrid_script_add_rem(vgrid_name, client_id, cert_id,
                                      'owner', configuration)
        if not ret_val:
            output_objects.append({'object_type': 'error_text', 'text': msg})
            status = returnvalues.CLIENT_ERROR
            continue

        # don't add if already an owner unless rank is given

        if rank is None and vgrid_is_owner(vgrid_name, cert_id, configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '%s is already an owner of %s or a parent %s.' %
                 (cert_id, vgrid_name, label)})
            status = returnvalues.CLIENT_ERROR
            continue

        # don't add if already a direct member

        if vgrid_is_member(vgrid_name, cert_id, configuration, recursive=False):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '%s is already a member of %s - please remove first.'
                 % (cert_id, vgrid_name)})
            status = returnvalues.CLIENT_ERROR
            continue

        # owner of subvgrid?

        (list_status, subvgrids) = vgrid_list_subvgrids(vgrid_name,
                                                        configuration)
        if not list_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Error getting list of sub%ss: %s' %
                                   (label, subvgrids)})
            status = returnvalues.SYSTEM_ERROR
            continue

        skip_entity = False
        for subvgrid in subvgrids:
            if vgrid_is_owner(subvgrid, cert_id, configuration, recursive=False):
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     """%s is already an owner of a sub-%s ('%s'). Please
remove the person first and then try this operation again.""" %
                     (cert_id, label, subvgrid)})
                status = returnvalues.CLIENT_ERROR
                skip_entity = True
                break
            if vgrid_is_member(subvgrid, cert_id, configuration, recursive=False):
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     """%s is already a member of a sub-%s ('%s'). Please
remove the person first and then try this operation again.""" %
                     (cert_id, label, subvgrid)})
                status = returnvalues.CLIENT_ERROR
                skip_entity = True
                break
        if skip_entity:
            continue

        # we DO allow ownership if member of parent vgrid - only handle with care

        if vgrid_is_member(vgrid_name, cert_id, configuration):
            # list is in top-down order
            parent_vgrids = vgrid_list_parents(vgrid_name, configuration)
            inherit_vgrid_member = vgrid_name
            for parent in parent_vgrids:
                if vgrid_is_member(parent, cert_id, configuration,
                                   recursive=False):
                    inherit_vgrid_member = parent
                    break
            output_objects.append(
                {'object_type': 'text', 'text':
                 '''NOTE: %s is already a member of parent %s %s.''' %
                 (cert_id, label, inherit_vgrid_member)
                 })

        # Check if only rank change was requested and apply if so

        if rank is not None:
            (add_status, add_msg) = vgrid_add_owners(configuration, vgrid_name,
                                                     [cert_id], rank=rank)
            if not add_status:
                output_objects.append(
                    {'object_type': 'error_text', 'text': add_msg})
                status = returnvalues.SYSTEM_ERROR
            else:
                output_objects.append({'object_type': 'text', 'text':
                                       'changed %s to owner %d' % (cert_id,
                                                                   rank)})
            # No further action after rank change as everything else exists
            continue

        # Getting here means cert_id is not owner of any parent or child vgrids.
        # may still be member of a parent grid but not a child vgrid.

        public_base_dir = \
            os.path.abspath(os.path.join(configuration.vgrid_public_base,
                                         vgrid_name)) + os.sep
        private_base_dir = \
            os.path.abspath(os.path.join(configuration.vgrid_private_base,
                                         vgrid_name)) + os.sep

        # Please note that base_dir must end in slash to avoid access to other
        # user dirs when own name is a prefix of another user name

        user_dir = os.path.abspath(os.path.join(configuration.user_home,
                                                cert_dir)) + os.sep

        user_public_base = os.path.abspath(os.path.join(user_dir,
                                                        'public_base')) + os.sep
        user_private_base = os.path.abspath(os.path.join(user_dir,
                                                         'private_base')) + os.sep

        # make sure all dirs can be created (that a file or directory with the same
        # name do not exist prior to adding the owner)

        if os.path.exists(user_public_base + vgrid_name):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '''Could not add owner, a file or directory in public_base
    exists with the same name! %s''' % user_dir + vgrid_name})
            status = returnvalues.CLIENT_ERROR
            continue

        if os.path.exists(user_private_base + vgrid_name):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '''Could not add owner, a file or directory in private_base
exists with the same name!'''})
            status = returnvalues.CLIENT_ERROR
            continue

        # vgrid share already exists if user is a member of parent vgrid

        if not inherit_vgrid_member and os.path.exists(user_dir + vgrid_name):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '''Could not add owner, a file or directory in the home
directory exists with the same name!'''})
            status = returnvalues.CLIENT_ERROR
            continue

        # Add

        (add_status, add_msg) = vgrid_add_owners(configuration, vgrid_name,
                                                 [cert_id])
        if not add_status:
            output_objects.append(
                {'object_type': 'error_text', 'text': add_msg})
            status = returnvalues.SYSTEM_ERROR
            continue

        vgrid_name_parts = vgrid_name.split('/')
        is_subvgrid = len(vgrid_name_parts) > 1

        # create public_base in cert_ids home dir if it does not exists

        try:
            os.mkdir(user_public_base)
        except Exception, exc:
            pass

        # create private_base in cert_ids home dir if it does not exists

        try:
            os.mkdir(user_private_base)
        except Exception, exc:
            pass

        if is_subvgrid:
            share_dir = None
            try:

                # Example:
                #    vgrid_name = IMADA/STUD/BACH
                #    vgrid_name_last_fragment = BACH
                #    vgrid_name_without_last_fragment = IMADA/STUD/

                vgrid_name_last_fragment = \
                    vgrid_name_parts[len(vgrid_name_parts) - 1].strip()

                vgrid_name_without_last_fragment = \
                    ('/'.join(vgrid_name_parts[0:len(vgrid_name_parts) - 1]) +
                     os.sep).strip()

                # create dirs if they do not exist

                share_dir = user_dir + vgrid_name_without_last_fragment
                if not os.path.isdir(share_dir):
                    os.makedirs(share_dir)
                pub_dir = user_public_base + vgrid_name_without_last_fragment
                if not os.path.isdir(pub_dir):
                    os.makedirs(pub_dir)
                priv_dir = user_private_base + vgrid_name_without_last_fragment
                if not os.path.isdir(priv_dir):
                    os.makedirs(priv_dir)
            except Exception, exc:

                # out of range? should not be possible due to is_subvgrid check

                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     ('Could not create needed dirs on %s server! %s'
                      % (configuration.short_title, exc))})
                logger.error('%s when looking for dir %s.' % (exc, share_dir))
                status = returnvalues.SYSTEM_ERROR
                continue

        # create symlink from users home directory to vgrid file directory
        # unless member of parent vgrid so that it is included already

        link_src = os.path.abspath(configuration.vgrid_files_home + os.sep
                                   + vgrid_name) + os.sep
        link_dst = user_dir + vgrid_name

        if not inherit_vgrid_member and \
                not make_symlink(link_src, link_dst, logger):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create link to %s share!' %
                                   label})
            logger.error('Could not create link to %s files (%s -> %s)' %
                         (label, link_src, link_dst))
            status = returnvalues.SYSTEM_ERROR
            continue

        public_base_dst = user_public_base + vgrid_name

        # create symlink for public_base files

        if not make_symlink(public_base_dir, public_base_dst, logger):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create link to public_base dir!'
                                   })
            logger.error('Could not create link to public_base dir (%s -> %s)'
                         % (public_base_dir, public_base_dst))
            status = returnvalues.SYSTEM_ERROR
            continue

        private_base_dst = user_private_base + vgrid_name

        # create symlink for private_base files

        if not make_symlink(private_base_dir, private_base_dst, logger):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create link to private_base dir!'
                                   })
            status = returnvalues.SYSTEM_ERROR
            continue

        if configuration.trac_admin_path:
            public_tracker_dir = \
                os.path.abspath(os.path.join(
                    configuration.vgrid_public_base, vgrid_name, '.vgridtracker'))
            private_tracker_dir = \
                os.path.abspath(os.path.join(
                    configuration.vgrid_private_base, vgrid_name, '.vgridtracker'))
            vgrid_tracker_dir = \
                os.path.abspath(os.path.join(
                    configuration.vgrid_files_home, vgrid_name, '.vgridtracker'))
            for tracker_dir in [public_tracker_dir, private_tracker_dir,
                                vgrid_tracker_dir]:
                if not add_tracker_admin(configuration, cert_id, vgrid_name,
                                         tracker_dir, output_objects):
                    status = returnvalues.SYSTEM_ERROR
                    continue
        cert_id_added.append(cert_id)

    if request_name:
        request_dir = os.path.join(configuration.vgrid_home, vgrid_name)
        if not delete_access_request(configuration, request_dir, request_name):
            logger.error("failed to delete owner request for %s in %s" %
                         (vgrid_name, request_name))
            output_objects.append({
                'object_type': 'error_text', 'text':
                'Failed to remove saved request for %s in %s!' %
                (vgrid_name, request_name)})

    if cert_id_added:
        output_objects.append(
            {'object_type': 'html_form', 'text':
             'New owner(s)<br />%s<br />successfully added to %s %s!''' %
             ('<br />'.join(cert_id_added), vgrid_name, label)
             })
        cert_id_fields = ''
        for cert_id in cert_id_added:
            cert_id_fields += """<input type=hidden name=cert_id value='%s' />
""" % cert_id

        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        fill_helpers = {'vgrid_name': vgrid_name, 'cert_id': cert_id,
                        'protocol': any_protocol,
                        'short_title': configuration.short_title,
                        'vgrid_label': label,
                        'cert_id_fields': cert_id_fields,
                        'form_method': form_method,
                        'csrf_field': csrf_field,
                        'csrf_limit': csrf_limit}
        target_op = 'sendrequestaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': """
<form method='%(form_method)s' action='%(target_op)s.py'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<input type=hidden name=request_type value='vgridaccept' />
<input type=hidden name=vgrid_name value='%(vgrid_name)s' />
%(cert_id_fields)s
<input type=hidden name=protocol value='%(protocol)s' />
<table>
<tr>
<td class='title'>Custom message to user(s)</td>
</tr><tr>
<td><textarea name=request_text cols=72 rows=10>
We have granted you ownership access to our %(vgrid_name)s %(vgrid_label)s.
You can access the %(vgrid_label)s administration page from the
%(vgrid_label)ss page on %(short_title)s.

Regards, the %(vgrid_name)s %(vgrid_label)s owners
</textarea></td>
</tr>
<tr>
<td><input type='submit' value='Inform user(s)' /></td>
</tr>
</table>
</form>
<br />
""" % fill_helpers})

    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, status)
