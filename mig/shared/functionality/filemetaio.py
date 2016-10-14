#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# filemetaio - Managing MiG file meta io
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

"""Script to provide users with a means of listing file meta data from
their home directories.
"""

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import csrf_field
from shared.functional import validate_input_and_cert
from shared.handlers import safe_handler, get_csrf_limit, \
    make_csrf_token
from shared.imagemeta import __get_vgrid_name, \
    list_image_meta_settings, get_image_meta_setting, \
    create_image_meta_setting, update_image_meta_setting, \
    remove_image_meta_setting, reset_image_meta_setting_status, \
    get_image_meta
from shared.imagemetaio import allowed_settings_status
from shared.init import initialize_main_variables, find_entry
from shared.settings import load_settings
from shared.vgrid import vgrid_is_owner

get_actions = ['list', 'get_dir', 'get_file']
post_actions = ['put_dir', 'update_dir', 'remove_dir', 'reset_dir']
valid_actions = get_actions + post_actions


def signature():
    """Signature of the main function"""

    defaults = {
        'action': ['list'],
        'flags': [''],
        'path': ['.'],
        'extension': [''],
        'settings_status': [allowed_settings_status['pending']],
        'settings_recursive': ['False'],
        'image_type': [''],
        'data_type': [''],
        'volume_slice_filepattern': [''],
        'offset': ['0'],
        'x_dimension': ['0'],
        'y_dimension': ['0'],
        'z_dimension': ['0'],
        'preview_image_extension': ['png'],
        'preview_x_dimension': ['256'],
        'preview_y_dimension': ['256'],
        'preview_z_dimension': ['256'],
        'preview_cutoff_min': ['0.0'],
        'preview_cutoff_max': ['0.0'],
        }

    return ['filemetaio', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
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
        WARNING_MSG = str(accepted)
        output_objects.append({'object_type': 'warning',
                              'text': WARNING_MSG})
        return (accepted, returnvalues.CLIENT_ERROR)

    action = ''.join(accepted['action'])
    flags = ''.join(accepted['flags'])
    path = ''.join(accepted['path'])
    extension = ''.join(accepted['extension'])

    logger.debug('%s from %s: %s' % (op_name, client_id, accepted))

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text',
                              'text': 'Invalid action "%s" (supported: %s)'
                               % (action, ', '.join(valid_actions))})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action in post_actions:
        if not safe_handler(
            configuration,
            'post',
            op_name,
            client_id,
            get_csrf_limit(configuration),
            accepted,
            ):
            output_objects.append({'object_type': 'error_text',
                                  'text': '''Only accepting
                CSRF-filtered POST requests to prevent unintended updates'''
                                  })
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep
    abs_path = os.path.join(base_dir, path)

    settings_dict = load_settings(client_id, configuration)
    javascript = None

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'FILEMETAIO Management'
    title_entry['javascript'] = javascript
    output_objects.append({'object_type': 'header',
                          'text': 'FILEMETAIO Management'})
    status = returnvalues.ERROR

    if flags == 'i':
        vgrid_name = __get_vgrid_name(path)
        vgrid_owner = vgrid_is_owner(vgrid_name, client_id,
                configuration, recursive=False)

        if action == 'list':
            status = list_image_meta_settings(configuration, abs_path,
                    path, output_objects)
            logger.debug('list exit status: %s' % str(status))
        elif action == 'remove_dir':

            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change image settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
            else:
                status = remove_image_meta_setting(configuration,
                        abs_path, path, extension, output_objects)
            logger.debug('remove_dir exit status: %s' % str(status))
        elif action == 'get_dir':

            status = get_image_meta_setting(configuration, abs_path,
                    path, extension, output_objects)
            logger.debug('get_dir exit status: %s' % str(status))
        elif action == 'update_dir':

            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change image settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
            else:
                status = update_image_meta_setting(
                    configuration,
                    base_dir,
                    abs_path,
                    path,
                    extension,
                    accepted,
                    output_objects,
                    )
            logger.debug('update_dir exit status: %s' % str(status))
        elif action == 'put_dir':

            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change image settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
            else:
                status = create_image_meta_setting(
                    configuration,
                    client_id,
                    base_dir,
                    abs_path,
                    path,
                    extension,
                    accepted,
                    output_objects,
                    )
            logger.debug('put_dir exit status: %s' % str(status))
        elif action == 'reset_dir':

            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change image settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
            else:
                status = reset_image_meta_setting_status(configuration,
                        abs_path, path, extension, output_objects)
            logger.debug('put_dir exit status: %s' % str(status))
        elif action == 'get_file':

            status = get_image_meta(configuration, base_dir, path,
                                    output_objects)
            logger.debug('get_file exit status: %s' % str(status))
    else:

        ERROR_MSG = "Unsupported request: action: '%s', flags: '%s'" \
            % (action, flags)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('filemetaio.py: %s -> %s' % (action, ERROR_MSG))

    logger.debug('output_objects: %s' % str(output_objects))
    logger.debug('status: %s' % str(status))
    return (output_objects, status)


