#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmvgridmember - remove vgrid member
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Remove a member from a vgrid"""

from __future__ import absolute_import

from builtins import range
import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.useradm import get_full_user_map
from mig.shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
    vgrid_is_member, vgrid_remove_members, vgrid_list_subvgrids, \
    allow_members_adm, vgrid_manage_allowed
from mig.shared.vgridaccess import unmap_inheritance


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'cert_id': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Remove %s Member" % label
    output_objects.append(
        {'object_type': 'header', 'text': 'Remove %s Member' % label})
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

    vgrid_name = accepted['vgrid_name'][-1]
    cert_id = accepted['cert_id'][-1]
    cert_dir = client_id_dir(cert_id)

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # always allow member to remove self
    if client_id != cert_id:
        user_map = get_full_user_map(configuration)
        user_dict = user_map.get(client_id, None)
        # Optional site-wide limitation of manage vgrid permission
        if not user_dict or \
                not vgrid_manage_allowed(configuration, user_dict):
            logger.warning("user %s is not allowed to manage vgrids!" %
                           client_id)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Only privileged users can manage %ss' % label})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # make sure vgrid settings allow this owner to edit other members
        (allow_status, allow_msg) = allow_members_adm(configuration,
                                                      vgrid_name, client_id)
        if not allow_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   allow_msg})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, _) = \
        init_vgrid_script_add_rem(vgrid_name, client_id, cert_id,
                                  'member', configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't remove if not a member

    if not vgrid_is_member(vgrid_name, cert_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               '%s is not a member of %s or a parent %s.' %
                               (cert_id, vgrid_name, label)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # owner of subvgrid?

    (list_status, subvgrids) = vgrid_list_subvgrids(vgrid_name,
                                                    configuration)
    if not list_status:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Error getting list of sub%ss: %s' %
                               (label, subvgrids)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # TODO: we DO allow ownership of sub vgrids with parent membership so we
    # should support the (cumbersome) relinking of vgrid shares here. Leave it
    # to user to do it manually for now with temporary removal of ownership

    for subvgrid in subvgrids:
        if vgrid_is_owner(subvgrid, cert_id, configuration, recursive=False):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 """%(cert_id)s is already an owner of a sub-%(vgrid_label)s
('%(subvgrid)s'). While we DO support members being owners of
sub-%(vgrid_label)ss, we do not support removing parent %(vgrid_label)s members
at the moment. Please (temporarily) remove the person as owner of all
sub-%(vgrid_label)ss first and then try this operation again.""" %
                 {'cert_id': cert_id, 'subvgrid': subvgrid,
                  'vgrid_label': label}})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # vgrid dirs when own name is a prefix of another name

    base_dir = os.path.abspath(os.path.join(configuration.vgrid_home,
                                            vgrid_name)) + os.sep

    # remove symlink from users home directory to vgrid directory

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    user_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            cert_dir)) + os.sep

    dst = user_dir + vgrid_name
    try:
        os.remove(dst)
    except Exception as exc:

        # ouch, not good. Email admin?

        pass

    if os.path.exists(dst):
        output_objects.append({'object_type': 'error_text', 'text':
                               'Could not remove link to %s files!' % label})
        logger.error('Removed member might still have access to %s files! %s'
                     % (label, dst))
        return (output_objects, returnvalues.SYSTEM_ERROR)

    vgrid_name_parts = vgrid_name.split('/')

    # make sure there are no "" entries in list

    while True:
        try:
            vgrid_name_parts.remove('')
            vgrid_name_parts.remove('/')
        except:

            # no such item

            break

    is_subvgrid = len(vgrid_name_parts) >= 2
    if is_subvgrid:

        # remove placeholder dirs (empty dirs created to hold subvgrid)

        # reverse list to remove files and directories of subdirs first

        list_range = list(range(len(vgrid_name_parts)))
        list_range.reverse()
        reverse_list = list_range

        # remove first entry in reversed list (SUBVGRID in VGRID/SUBVGRID since
        # we know it was the symbolic link and is not a dir)

        reverse_list = reverse_list[1:]

        # remove empty placeholder dirs in home dir, private_base and
        # public_base dirs

        base_dirs = [user_dir]
        for base_dir in base_dirs:
            for loop_count in reverse_list:

                # note that loop_count is decreasing!

                current_vgrid_path = \
                    '/'.join(vgrid_name_parts[0:loop_count + 1])
                current_path = base_dir + current_vgrid_path
                if not os.path.isdir(current_path):
                    output_objects.append(
                        {'object_type': 'error_text', 'text':
                         '''Error removing %s placeholder dirs:
%s is not a directory, not going to remove.''' % (label, current_vgrid_path)})
                    continue

                if os.listdir(current_path):
                    output_objects.append(
                        {'object_type': 'error_text', 'text':
                         '''Could not remove %s placeholder dirs:
%s is not an empty directory (not critical)''' % (label, current_vgrid_path)})
                else:

                    # remove empty directory

                    try:
                        os.rmdir(current_path)
                    except Exception as exc:
                        logger.error("could not remove %s: %s" % (current_path,
                                                                  exc))
                        output_objects.append(
                            {'object_type': 'error_text', 'text':
                             'Error removing %s empty(?) placeholder dirs' %
                             label})
                        return (output_objects,
                                returnvalues.SYSTEM_ERROR)

    # remove from list

    (rm_status, rm_msg) = vgrid_remove_members(configuration, vgrid_name,
                                               [cert_id])
    if not rm_status:
        output_objects.append({'object_type': 'error_text', 'text':
                               '%s of member of %s' % (rm_msg, vgrid_name)})
        output_objects.append({'object_type': 'error_text', 'text':
                               '''(If %(vgrid_label)s %(vgrid_name)s has
sub-%(vgrid_label)ss then removal must be performed from the most significant
%(vgrid_label)s possible.)''' % {'vgrid_name': vgrid_name,
                                 'vgrid_label': label}})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    unmap_inheritance(configuration, vgrid_name, cert_id)

    output_objects.append({'object_type': 'text', 'text':
                           '%s successfully removed as member of %s %s!'
                           % (cert_id, vgrid_name, label)})
    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)
