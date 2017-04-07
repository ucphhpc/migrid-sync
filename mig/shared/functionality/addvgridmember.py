#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addvgridmember - add one or more vgrid members
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Add one or more VGrid member"""

from binascii import unhexlify
import os

from shared.accessrequests import delete_access_request
from shared.base import client_id_dir
from shared.defaults import any_protocol, csrf_field
from shared.fileio import make_symlink
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from shared.init import initialize_main_variables, find_entry
from shared.useradm import expand_openid_alias
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
     vgrid_is_member, vgrid_list_subvgrids, vgrid_add_members, \
     allow_members_adm
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'cert_id': REJECT_UNSET,
                'request_name': [''], 'rank': ['']}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Add %s Member" % label
    output_objects.append({'object_type': 'header', 'text':
                           'Add %s Member(s)' % label})
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

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # make sure vgrid settings allow this owner to edit members

    (allow_status, allow_msg) = allow_members_adm(configuration, vgrid_name,
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
                                      'member', configuration)
        if not ret_val:
            output_objects.append({'object_type': 'error_text', 'text':
                                   msg})
            status = returnvalues.CLIENT_ERROR
            continue

        # don't add if already an owner

        if vgrid_is_owner(vgrid_name, cert_id, configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '%s is already an owner of %s or a parent %s.' % \
                 (cert_id, vgrid_name, label)})
            status = returnvalues.CLIENT_ERROR
            continue

        # don't add if already a member unless rank is given

        if rank is None and vgrid_is_member(vgrid_name, cert_id, configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '''%s is already a member of %s or a parent %s. Please remove
    the person first and then try this operation again.''' % \
                 (cert_id, vgrid_name, label)
                 })
            status = returnvalues.CLIENT_ERROR
            continue

        # owner or member of subvgrid?

        (list_status, subvgrids) = vgrid_list_subvgrids(vgrid_name,
                configuration)
        if not list_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Error getting list of sub%ss: %s' % \
                                   (label, subvgrids)})
            status = returnvalues.SYSTEM_ERROR
            continue

        # TODO: we DO allow ownership of sub vgrids with parent membership so we
        # should support the (cumbersome) relinking of vgrid shares here. Leave it
        # to user to do it manually for now with temporary removal of ownership

        skip_entity = False
        for subvgrid in subvgrids:
            if vgrid_is_owner(subvgrid, cert_id, configuration, recursive=False):
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     """%(cert_id)s is already an owner of a
sub-%(vgrid_label)s ('%(subvgrid)s'). While we DO support members being owners
of sub-%(vgrid_label)ss, we do not support adding parent %(vgrid_label)s
members at the moment. Please (temporarily) remove the person as owner of all
sub-%(vgrid_label)ss first and then try this operation again.""" % \
                     {'cert_id': cert_id, 'subvgrid': subvgrid,
                      'vgrid_label': label}})
                status = returnvalues.CLIENT_ERROR
                skip_entity = True
                break
            if vgrid_is_member(subvgrid, cert_id, configuration, recursive=False):
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     """%s is already a member of a sub-%s ('%s'). Please
remove the person first and then try this operation again.""" % \
                     (cert_id, label, subvgrid)})
                status = returnvalues.CLIENT_ERROR
                skip_entity = True
                break
        if skip_entity:
            continue

        # Check if only rank change was requested and apply if so

        if rank is not None:
            (add_status, add_msg) = vgrid_add_members(configuration,
                                                      vgrid_name,
                                                      [cert_id], rank=rank)
            if not add_status:
                output_objects.append({'object_type': 'error_text', 'text'
                                       : add_msg})
                status = returnvalues.SYSTEM_ERROR
            else:
                output_objects.append({'object_type': 'text', 'text':
                                       'changed %s to member %d' % (cert_id,
                                                                   rank)})
            # No further action after rank change as everything else exists
            continue

        # Getting here means cert_id is neither owner or member of any parent or
        # sub-vgrids.

        # Please note that base_dir must end in slash to avoid access to other
        # vgrid dirs when own name is a prefix of another name

        base_dir = os.path.abspath(os.path.join(configuration.vgrid_home,
                                   vgrid_name)) + os.sep
        user_dir = os.path.abspath(os.path.join(configuration.user_home,
                                   cert_dir)) + os.sep

        # make sure all dirs can be created (that a file or directory with the same
        # name do not exist prior to adding the member)

        if os.path.exists(user_dir + vgrid_name):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : '''Could not add member, a file or directory in the home
    directory called %s exists! (%s)''' % (vgrid_name, user_dir + vgrid_name)})
            status = returnvalues.CLIENT_ERROR
            continue

        # Add

        (add_status, add_msg) = vgrid_add_members(configuration, vgrid_name,
                                                  [cert_id])
        if not add_status:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : add_msg})
            status = returnvalues.SYSTEM_ERROR
            continue

        vgrid_name_parts = vgrid_name.split('/')
        is_subvgrid = len(vgrid_name_parts) > 1

        if is_subvgrid:
            try:

                # vgrid_name = IMADA/STUD/BACH
                # vgrid_name_last_fragment = BACH

                vgrid_name_last_fragment = \
                    vgrid_name_parts[len(vgrid_name_parts)
                                         - 1].strip()

                # vgrid_name_without_last_fragment = IMADA/STUD/

                vgrid_name_without_last_fragment = \
                    ('/'.join(vgrid_name_parts[0:len(vgrid_name_parts)
                      - 1]) + os.sep).strip()

                # create dirs if they do not exist

                dir1 = user_dir + vgrid_name_without_last_fragment
                if not os.path.isdir(dir1):
                    os.makedirs(dir1)
            except Exception, exc:

                # out of range? should not be possible due to is_subvgrid check

                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     ('Could not create needed dirs on %s server! %s'
                      % (configuration.short_title, exc))})
                logger.error('%s when looking for dir %s.' % (exc, dir1))
                status = returnvalues.SYSTEM_ERROR
                continue

        # create symlink from users home directory to vgrid file directory

        link_src = os.path.abspath(configuration.vgrid_files_home + os.sep
                                    + vgrid_name) + os.sep
        link_dst = user_dir + vgrid_name

        # create symlink to vgrid files

        if not make_symlink(link_src, link_dst, logger):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create link to %s files!' % \
                                   label
                                  })
            logger.error('Could not create link to %s files! (%s -> %s)' % \
                         (label, link_src, link_dst))
            status = returnvalues.SYSTEM_ERROR
            continue
        cert_id_added.append(cert_id)

    if request_name:
        request_dir = os.path.join(configuration.vgrid_home, vgrid_name)
        if not delete_access_request(configuration, request_dir, request_name):
                logger.error("failed to delete member request for %s in %s" % \
                             (vgrid_name, request_name))
                output_objects.append({
                    'object_type': 'error_text', 'text':
                    'Failed to remove saved request for %s in %s!' % \
                    (vgrid_name, request_name)})

    if cert_id_added:
        output_objects.append(
            {'object_type': 'html_form', 'text':
             'New member(s)<br />%s<br />successfully added to %s %s!''' % \
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
We have granted you membership access to our %(vgrid_name)s %(vgrid_label)s.
You can access the %(vgrid_label)s components and collaboration tools from your
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


