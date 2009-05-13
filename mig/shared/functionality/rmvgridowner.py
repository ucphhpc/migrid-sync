#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmvgridowner - [insert a few words of module description on this line]
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

"""Remove an owner from a given vgrid"""

import os
import sys

from shared.validstring import cert_name_format
from shared.listhandling import remove_item_from_pickled_list
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""
    defaults = {'vgrid_name': REJECT_UNSET, 'cert_name': REJECT_UNSET}
    return ['text', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        cert_name_no_spaces,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    vgrid_name = accepted['vgrid_name'][-1]
    cert_name = accepted['cert_name'][-1]
    cert_name = cert_name_format(cert_name)

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, cert_name_no_spaces,
                                  cert_name, 'owner', configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't add if already an owner

    if not vgrid_is_owner(vgrid_name, cert_name, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is not an owner of %s or a parent vgrid.'
                               % (cert_name, vgrid_name)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    base_dir = configuration.vgrid_home + os.sep + vgrid_name + os.sep
    owners_file = base_dir + 'owners'

    # remove symlink from users home directory to vgrid directory

    cert_name_home_dir = configuration.user_home + os.sep + cert_name\
         + os.sep

    dst = cert_name_home_dir + vgrid_name
    try:
        os.remove(dst)
    except Exception, exc:

        # ouch, not good. Email admin?

        pass

    if os.path.exists(dst):
        logger.error('Could not remove link to vgrid files! Removed owner might still have access to vgrid files! %s'
                      % dst)
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not remove link to vgrid files!'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # remove symlink to public_base

    public_base_dir = cert_name_home_dir + 'public_base' + os.sep\
         + vgrid_name
    try:
        os.remove(public_base_dir)
    except Exception, exc:
        logger.error('Could not remove symlink during vgrid owner removal %s, exc: %s'
                      % (public_base_dir, exc))

        # ouch, not good. Email admin?

        pass

    if os.path.exists(public_base_dir):
        logger.error('Could not remove link to vgrid public_basefiles! %s'
                      % public_base_dir)
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not remove link to vgrid public_basefiles!'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # remove symlink to private_base

    private_base_dir = cert_name_home_dir + 'private_base' + os.sep\
         + vgrid_name
    try:
        os.remove(private_base_dir)
    except Exception, exc:
        logger.error('Could not remove symlink during vgrid owner removal %s, exc: %s'
                      % (private_base_dir, exc))

        # ouch, not good. Send email to admins?

        pass

    if os.path.exists(private_base_dir):
        logger.error('Could not remove link to vgrid private_base files! %s'
                      % public_base_dir)
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not remove link to vgrid private_base files!'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    vgrid_name_splitted = vgrid_name.split('/')

    # make sure there are no "" entries in list

    while True:
        try:
            vgrid_name_splitted.remove('')
            vgrid_name_splitted.remove('/')
        except:

            # no such item

            break

    is_subvgrid = len(vgrid_name_splitted) >= 2
    if is_subvgrid:

        # remove placeholder dirs (empty dirs created to hold subvgrid)

        # reverse list to remove files and directories of subdirs first

        list = range(len(vgrid_name_splitted))
        list.reverse()
        reverse_list = list

        # remove first entry in reversed list (SUBVGRID in VGRID/SUBVGRID since we not it was the symbolic link and is not a dir)

        reverse_list = reverse_list[1:]

        # remove empty placeholder dirs in home dir, private_base and public_base dirs

        base_dirs = [cert_name_home_dir, cert_name_home_dir
                      + 'private_base' + os.sep, cert_name_home_dir
                      + 'public_base' + os.sep]
        for base_dir in base_dirs:
            for loop_count in reverse_list:

                # note that loop_count is decreasing!

                current_vgrid_path = \
                    '/'.join(vgrid_name_splitted[0:loop_count + 1])
                current_path = base_dir + current_vgrid_path
                if not os.path.isdir(current_path):
                    output_objects.append({'object_type': 'error_text',
                            'text'
                            : 'Removing vgrid placeholder dirs: %s is not a directory, not going to remove'
                             % current_vgrid_path})
                    continue

                # verify that == compares content not address of list
                # if [].append(not_allowed_here_filename) == os.listdir(current_path):

                if not os.listdir(current_path) == []:
                    output_objects.append({'object_type': 'warning',
                            'text'
                            : 'Could not remove vgrid placeholder dirs: %s is not an empty directory'
                             % current_vgrid_path})
                else:

                    # remove empty directory

                    try:
                        os.rmdir(current_path)
                    except Exception, exc:
                        output_objects.append({'object_type'
                                : 'error_text', 'text'
                                : 'Removing vgrid placeholder dirs: exception removing empty directory!'
                                })
                        return (output_objects,
                                returnvalues.SYSTEM_ERROR)

    # remove user from pickled list

    (status, msg) = remove_item_from_pickled_list(owners_file,
            cert_name, logger, False)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s of owners of %s' % (msg,
                              vgrid_name)})
        output_objects.append({'object_type': 'error_text', 'text'
                              : '(If Vgrid %s has sub-vgrids then removal must be performed from the most significant VGrid possible.)'
                               % vgrid_name})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : '%s successfully removed as owner of %s vgrid!'
                           % (cert_name, vgrid_name)})
    return (output_objects, returnvalues.OK)


