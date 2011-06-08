#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmvgridmember - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_member, \
     vgrid_remove_members


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'cert_id': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    defaults = signature()[1]
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

    vgrid_name = accepted['vgrid_name'][-1]
    cert_id = accepted['cert_id'][-1]
    cert_dir = client_id_dir(cert_id)

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, client_id, cert_id,
                                  'member', configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't remove if not a member

    if not vgrid_is_member(vgrid_name, cert_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is not a member of %s or a parent vgrid.'
                               % (cert_id, vgrid_name)})
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
    except Exception, exc:

        # ouch, not good. Email admin?

        pass

    if os.path.exists(dst):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not remove link to vgrid files!'
                              })
        logger.error('Removed member might still have access to vgrid files! %s'
                      % dst)
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

        list = range(len(vgrid_name_parts))
        list.reverse()
        reverse_list = list

        # remove first entry in reversed list (SUBVGRID in VGRID/SUBVGRID since we not it was the symbolic link and is not a dir)

        reverse_list = reverse_list[1:]

        # remove empty placeholder dirs in home dir, private_base and public_base dirs

        base_dirs = [user_dir]
        for base_dir in base_dirs:
            for loop_count in reverse_list:

                # note that loop_count is decreasing!

                current_vgrid_path = \
                    '/'.join(vgrid_name_parts[0:loop_count + 1])
                current_path = base_dir + current_vgrid_path
                if not os.path.isdir(current_path):
                    output_objects.append({'object_type': 'error_text',
                            'text'
                            : 'Error removing vgrid placeholder dirs: %s is not a directory, not going to remove.'
                             % current_vgrid_path})
                    continue

                # verify that == compares content not address of list
                # if [].append(not_allowed_here_filename) == os.listdir(current_path):

                if not os.listdir(current_path) == []:
                    output_objects.append({'object_type': 'error_text',
                            'text'
                            : 'Could not remove vgrid placeholder dirs: %s is not an empty directory (not critical)'
                             % current_vgrid_path})
                else:

                    # remove empty directory

                    try:
                        os.rmdir(current_path)
                    except Exception, exc:
                        output_objects.append({'object_type'
                                : 'error_text', 'text'
                                : 'Error removing vgrid placeholder dirs: exception removing empty directory %s'
                                 % exc})
                        return (output_objects,
                                returnvalues.SYSTEM_ERROR)

    # remove from list

    (rm_status, rm_msg) = vgrid_remove_members(configuration, vgrid_name,
                                               [cert_id])
    if not rm_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s of member of %s' % (rm_msg,
                              vgrid_name)})
        output_objects.append({'object_type': 'error_text', 'text'
                              : '(If Vgrid %s has sub-vgrids then removal must be performed from the most significant VGrid possible.)'
                               % vgrid_name})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : '%s successfully removed as member of %s vgrid!'
                           % (cert_id, vgrid_name)})
    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)


