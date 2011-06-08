#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addvgridowner - [insert a few words of module description on this line]
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

"""Add owner to a vgrid"""

import os

from shared.base import client_id_dir
from shared.fileio import make_symlink
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
    vgrid_is_member, vgrid_list_subvgrids, vgrid_add_owners
import shared.returnvalues as returnvalues


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
                                  'owner', configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't add if already an owner

    if vgrid_is_owner(vgrid_name, cert_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is already an owner of %s or a parent vgrid.'
                               % (cert_id, vgrid_name)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't add if already a member

    if vgrid_is_member(vgrid_name, cert_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is already a member of %s or a parent vgrid. Please remove the person first and then try this operation again.'
                               % (cert_id, vgrid_name)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # owner of subvgrid?

    (status, subvgrids) = vgrid_list_subvgrids(vgrid_name,
            configuration)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting list of subvgrids: %s'
                               % subvgrids})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    for subvgrid in subvgrids:
        if vgrid_is_owner(subvgrid, cert_id, configuration):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : "%s is already an owner of a sub vgrid ('%s'). Please remove the person first and then try this operation again."
                                   % (cert_id, subvgrid)})
            return (output_objects, returnvalues.CLIENT_ERROR)
        if vgrid_is_member(subvgrid, cert_id, configuration):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : "%s is already a member of a sub vgrid ('%s'). Please remove the person first and then try this operation again."
                                   % (cert_id, subvgrid)})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # getting here means cert_id is neither owner or member of any parent or sub-vgrids.

    # Please note that base_dir must end in slash to avoid access to other
    # vgrid dirs when own name is a prefix of another name

    base_dir = os.path.abspath(os.path.join(configuration.vgrid_home,
                               vgrid_name)) + os.sep

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

    # make sure all dirs can be created (that a file or directory with the same name
    # do not exist prior to adding the owner)

    if os.path.exists(user_public_base + vgrid_name):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not add owner, a file or directory in public_base exists with the same name! %s'
                               % user_dir + vgrid_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if os.path.exists(user_private_base + vgrid_name):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not add owner, a file or directory in private_base exists with the same name!'
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if os.path.exists(user_dir + vgrid_name):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not add owner, a file or directory in the home directory exists with the same name!'
                              })
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

            dir1 = user_dir + vgrid_name_without_last_fragment
            if not os.path.isdir(dir1):
                os.makedirs(dir1)
                dir2 = user_public_base\
                     + vgrid_name_without_last_fragment
            if not os.path.isdir(dir2):
                os.makedirs(dir2)
                dir3 = user_private_base\
                     + vgrid_name_without_last_fragment
            if not os.path.isdir(dir3):
                os.makedirs(dir3)
        except Exception, exc:

            # out of range? should not be possible due to is_subvgrid check

            output_objects.append({'object_type': 'error_text', 'text'
                                  : ('Could not create needed dirs on %s server! %s'
                                     % (configuration.short_title, exc))})
            logger.error('%s when looking for dir %s.' % (exc, dir1))
            return (output_objects, returnvalues.SYSTEM_ERROR)

    # create symlink from users home directory to vgrid file directory

    link_src = os.path.abspath(configuration.vgrid_files_home + os.sep
                                + vgrid_name) + os.sep
    link_dst = user_dir + vgrid_name
    not_allowed_here_filename = 'not_in_vgrid__writing_here_not_allowed'

    # create symlink to vgrid files

    if not make_symlink(link_src, link_dst, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create link to vgrid files!'
                              })
        logger.error('Could not create link to vgrid files link_src: %s link_dst: %s'
                      % (link_src, link_dst))
        return (output_objects, returnvalues.SYSTEM_ERROR)

    public_base_dst = user_public_base + vgrid_name

    # create symlink for public_base files

    if not make_symlink(public_base_dir, public_base_dst, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create link to public_base dir!'
                              })
        logger.error('Could not create link to public_base dir src: %s dst: %s'
                      % (public_base_dir, public_base_dst))
        return (output_objects, returnvalues.SYSTEM_ERROR)

    private_base_dst = user_private_base + vgrid_name

    # create symlink for private_base files

    if not make_symlink(private_base_dir, private_base_dst, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create link to private_base dir!'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : 'New owner %s successfully added to %s vgrid!'
                           % (cert_id, vgrid_name)})
    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)


