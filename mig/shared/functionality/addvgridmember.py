#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addvgridmember - add vgrid member
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

"""Add VGrid member"""

import os

from shared.base import client_id_dir
from shared.defaults import any_protocol
from shared.fileio import make_symlink
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.useradm import expand_openid_alias
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
    vgrid_is_member, vgrid_list_subvgrids, vgrid_add_members
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'cert_id': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Add %s Member' % configuration.site_vgrid_label})
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

    # Allow openid alias as subject if openid with alias is enabled
    if configuration.user_openid_providers and configuration.user_openid_alias:
        cert_id = expand_openid_alias(cert_id, configuration)

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, _) = \
        init_vgrid_script_add_rem(vgrid_name, client_id, cert_id,
                                  'member', configuration)
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

    # don't add if already a member

    if vgrid_is_member(vgrid_name, cert_id, configuration):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : '''%s is already a member of %s or a parent %s. Please remove
the person first and then try this operation again.''' % \
             (cert_id, vgrid_name, configuration.site_vgrid_label)
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # owner or member of subvgrid?

    (status, subvgrids) = vgrid_list_subvgrids(vgrid_name,
            configuration)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting list of sub%ss: %s'
                               % (configuration.site_vgrid_label, subvgrids)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # TODO: we DO allow ownership of sub vgrids with parent membership so we
    # should support the (cumbersome) relinking of vgrid shares here. Leave it
    # to user to do it manually for now with temporary removal of ownership

    for subvgrid in subvgrids:
        if vgrid_is_owner(subvgrid, cert_id, configuration, recursive=False):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : """%(cert_id)s is already an owner of a sub-%(_label)s
('%(subvgrid)s'). While we DO support members being owners of sub-%(_label)ss,
we do not support adding parent %(_label)s members at the moment. Please
(temporarily) remove the person as owner of all sub-%(_label)ss first and then
try this operation again.""" % {'cert_id': cert_id, 'subvgrid': subvgrid,
                                '_label': configuration.site_vgrid_label}})
            return (output_objects, returnvalues.CLIENT_ERROR)
        if vgrid_is_member(subvgrid, cert_id, configuration, recursive=False):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : """%s is already a member of a sub-%s ('%s'). Please
remove the person first and then try this operation again.""" % \
                 (cert_id, configuration.site_vgrid_label, subvgrid)})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # getting here means cert_id is neither owner or member of any parent or
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
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Add

    (add_status, add_msg) = vgrid_add_members(configuration, vgrid_name,
                                              [cert_id])
    if not add_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : add_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

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
                {'object_type': 'error_text', 'text'
                 : ('Could not create needed dirs on %s server! %s'
                    % (configuration.short_title, exc))})
            logger.error('%s when looking for dir %s.' % (exc, dir1))
            return (output_objects, returnvalues.SYSTEM_ERROR)

    # create symlink from users home directory to vgrid file directory

    link_src = os.path.abspath(configuration.vgrid_files_home + os.sep
                                + vgrid_name) + os.sep
    link_dst = user_dir + vgrid_name

    # create symlink to vgrid files

    if not make_symlink(link_src, link_dst, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create link to %s files!' % \
                               configuration.site_vgrid_label
                              })
        logger.error('Could not create link to %s files! (%s -> %s)'
                      % (configuration.site_vgrid_label, link_src, link_dst))
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : 'New member %s successfully added to %s %s!'
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
We have granted you membership access to our %(vgrid_name)s %(_label)s.
You can access the %(_label)s components and collaboration tools from your
%(_label)ss page on %(short_title)s.

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
       '_label': configuration.site_vgrid_label,
       'short_title': configuration.short_title}})
    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)


