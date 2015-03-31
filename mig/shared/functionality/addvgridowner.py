#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addvgridowner - add vgrid owner
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Add owner to a vgrid"""

import os
import subprocess

from shared.base import client_id_dir
from shared.defaults import any_protocol
from shared.fileio import make_symlink
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.useradm import distinguished_name_to_user, expand_openid_alias
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
    vgrid_is_member, vgrid_list_subvgrids, vgrid_add_owners, vgrid_list_parents
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'cert_id': REJECT_UNSET}
    return ['text', defaults]

def add_tracker_admin(configuration, cert_id, vgrid_name, tracker_dir,
                      output_objects):
    """Add new Trac issue tracker owner"""
    cgi_tracker_var = os.path.join(tracker_dir, 'var')
    if not os.path.isdir(cgi_tracker_var):
        output_objects.append(
            {'object_type': 'text', 'text'
             : 'No tracker (%s) for %s %s - skipping tracker admin rights' \
             % (tracker_dir, configuration.site_vgrid_label, vgrid_name)
             })
        return (output_objects, returnvalues.SYSTEM_ERROR)
    try:
        admin_user = distinguished_name_to_user(cert_id)
        admin_id = admin_user.get(configuration.trac_id_field, 'unknown_id')
        # Give admin rights to owner using trac-admin command:
        # trac-admin tracker_dir deploy cgi_tracker_bin
        perms_cmd = [configuration.trac_admin_path, cgi_tracker_var,
                     'permission', 'add', admin_id, 'TRAC_ADMIN']
        configuration.logger.info('provide admin rights to owner: %s' % \
                                  perms_cmd)
        proc = subprocess.Popen(perms_cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
        proc.wait()
        if proc.returncode != 0:
            raise Exception("tracker permissions %s failed: %s (%d)" % \
                            (perms_cmd, proc.stdout.read(),
                             proc.returncode))
        return True
    except Exception, exc:
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Could not give %s tracker admin rights: %s' % (cert_id, exc)
             })
        return False

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Add %s Owner' % configuration.site_vgrid_label})
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

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    vgrid_name = accepted['vgrid_name'][-1].strip()
    cert_id = accepted['cert_id'][-1].strip()
    cert_dir = client_id_dir(cert_id)
    # inherited vgrid membership
    inherit_vgrid_member = False

    # Allow openid alias as subject if openid with alias is enabled
    if configuration.user_openid_providers and configuration.user_openid_alias:
        cert_id = expand_openid_alias(cert_id, configuration)

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, _) = \
        init_vgrid_script_add_rem(vgrid_name, client_id, cert_id,
                                  'owner', configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't add if already an owner

    if vgrid_is_owner(vgrid_name, cert_id, configuration):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : '%s is already an owner of %s or a parent %s.'
             % (cert_id, vgrid_name, configuration.site_vgrid_label)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't add if already a direct member

    if vgrid_is_member(vgrid_name, cert_id, configuration, recursive=False):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : '%s is already a member of %s - please remove first.'
             % (cert_id, vgrid_name)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # owner of subvgrid?

    (status, subvgrids) = vgrid_list_subvgrids(vgrid_name,
            configuration)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting list of sub%ss: %s'
                               % (configuration.site_vgrid_label, subvgrids)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    for subvgrid in subvgrids:
        if vgrid_is_owner(subvgrid, cert_id, configuration, recursive=False):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : """%s is already an owner of a sub-%s ('%s'). Please
remove the person first and then try this operation again.""" % \
                 (cert_id, configuration.site_vgrid_label, subvgrid)})
            return (output_objects, returnvalues.CLIENT_ERROR)
        if vgrid_is_member(subvgrid, cert_id, configuration, recursive=False):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : """%s is already a member of a sub-%s ('%s'). Please
remove the person first and then try this operation again.""" % \
                 (cert_id, configuration.site_vgrid_label, subvgrid)})
            return (output_objects, returnvalues.CLIENT_ERROR)

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
            {'object_type': 'text', 'text'
             : '''NOTE: %s is already a member of parent %s %s.''' % \
             (cert_id, configuration.site_vgrid_label, inherit_vgrid_member)
             })

    # getting here means cert_id is not owner of any parent or child vgrids.
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
            {'object_type': 'error_text', 'text'
             : '''Could not add owner, a file or directory in public_base
exists with the same name! %s''' % user_dir + vgrid_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if os.path.exists(user_private_base + vgrid_name):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : '''Could not add owner, a file or directory in private_base
exists with the same name!'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # vgrid share already exists if user is a member of parent vgrid
    
    if not inherit_vgrid_member and os.path.exists(user_dir + vgrid_name):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : '''Could not add owner, a file or directory in the home
directory exists with the same name!'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Add

    (add_status, add_msg) = vgrid_add_owners(configuration, vgrid_name,
                                             [cert_id])
    if not add_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : add_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

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
                vgrid_name_parts[len(vgrid_name_parts)- 1].strip()


            vgrid_name_without_last_fragment = \
                ('/'.join(vgrid_name_parts[0:len(vgrid_name_parts) - 1]) + \
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
                {'object_type': 'error_text', 'text'
                 : ('Could not create needed dirs on %s server! %s'
                    % (configuration.short_title, exc))})
            logger.error('%s when looking for dir %s.' % (exc, share_dir))
            return (output_objects, returnvalues.SYSTEM_ERROR)

    # create symlink from users home directory to vgrid file directory
    # unless member of parent vgrid so that it is included already

    link_src = os.path.abspath(configuration.vgrid_files_home + os.sep
                                + vgrid_name) + os.sep
    link_dst = user_dir + vgrid_name

    if not inherit_vgrid_member and \
           not make_symlink(link_src, link_dst, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create link to %s share!' % \
                               configuration.site_vgrid_label})
        logger.error('Could not create link to %s files (%s -> %s)'
                     % (configuration.site_vgrid_label, link_src, link_dst))
        return (output_objects, returnvalues.SYSTEM_ERROR)

    public_base_dst = user_public_base + vgrid_name

    # create symlink for public_base files

    if not make_symlink(public_base_dir, public_base_dst, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create link to public_base dir!'
                              })
        logger.error('Could not create link to public_base dir (%s -> %s)'
                     % (public_base_dir, public_base_dst))
        return (output_objects, returnvalues.SYSTEM_ERROR)

    private_base_dst = user_private_base + vgrid_name

    # create symlink for private_base files

    if not make_symlink(private_base_dir, private_base_dst, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create link to private_base dir!'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

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
                return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : 'New owner %s successfully added to %s %s!'
                           % (cert_id, vgrid_name,
                              configuration.site_vgrid_label)})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<form method='post' action='sendrequestaction.py'>
<input type=hidden name=request_type value='vgridaccept' />
<input type=hidden name=vgrid_name value='%(vgrid_name)s' />
<input type=hidden name=cert_id value='%(cert_id)s' />
<input type=hidden name=protocol value='%(protocol)s' />
<table>
<tr>
<td class='title'>Custom message to user</td>
</tr><tr>
<td><textarea name=request_text cols=72 rows=10>
We have granted you ownership access to our %(vgrid_name)s %(_label)s.
You can access the %(_label)s administration page from the %(_label)ss page.

Regards, the %(vgrid_name)s %(_label)s owners
</textarea></td>
</tr>
<tr>
<td><input type='submit' value='Inform user' /></td>
</tr>
</table>
</form>
<br />
""" % {'vgrid_name': vgrid_name, 'cert_id': cert_id, 'protocol': any_protocol,
       '_label': configuration.site_vgrid_label}})
    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)
