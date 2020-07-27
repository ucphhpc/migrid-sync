#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# imagepreview - Managing MiG imagepreview meta
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

"""Script to provide users with a means of listing file meta data from
their home directories.
"""
from __future__ import absolute_import

import os

from .shared import returnvalues
from .shared.base import client_id_dir
from .shared.defaults import csrf_field
from .shared.functional import validate_input_and_cert
from .shared.handlers import safe_handler, get_csrf_limit, \
    make_csrf_token
from .shared.imagemeta import list_settings, get_setting, \
    create_setting, update_setting, remove_setting, reset_settings, \
    get, refresh, remove, clean
from .shared.init import initialize_main_variables, find_entry
from .shared.vgrid import vgrid_is_owner, in_vgrid_share

get_actions = ['list_settings', 'get_setting', 'get']
post_actions = [
    'create_setting',
    'update_setting',
    'remove_setting',
    'reset_setting',
    'remove',
    'clean',
    'cleanrecursive',
    'refresh',
]
valid_actions = get_actions + post_actions


def signature():
    """Signature of the main function"""

    defaults = {
        'action': ['list_settings'],
        'flags': [''],
        'path': [''],
        'extension': [''],
        'settings_status': [],
        'settings_recursive': [],
        'image_type': [],
        'data_type': [],
        'volume_slice_filepattern': [],
        'offset': [],
        'x_dimension': [],
        'y_dimension': [],
        'z_dimension': [],
        'preview_image_extension': [],
        'preview_x_dimension': [],
        'preview_y_dimension': [],
        'preview_z_dimension': [],
        'preview_cutoff_min': [],
        'preview_cutoff_max': [],
    }

    return ['imagepreview', defaults]


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

    # Convert accpeted values to string and filter out NON-set values

    accepted_joined_values = {key: ''.join(value)
                              for (key, value) in accepted.iteritems() if len(value) > 0}

    action = accepted_joined_values['action']
    flags = accepted_joined_values['flags']
    path = accepted_joined_values['path']
    extension = accepted['extension'][-1].strip()

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
            logger.info('checkpoint2')
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

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'IMAGEPREVIEW Management'
    output_objects.append({'object_type': 'header',
                           'text': 'IMAGEPREVIEW Management'})
    status = returnvalues.ERROR

    vgrid_name = in_vgrid_share(configuration, abs_path)
    vgrid_owner = vgrid_is_owner(vgrid_name, client_id, configuration)

    status = returnvalues.OK
    if vgrid_name is None:
        status = returnvalues.ERROR
        ERROR_MSG = "No vgrid found for path: '%s'" % path
        output_objects.append({'object_type': 'error_text',
                               'text': ERROR_MSG})

    if status == returnvalues.OK:
        if action == 'list_settings':
            status = list_settings(configuration, abs_path, path,
                                   output_objects)
            logger.debug('list exit status: %s' % str(status))
        elif action == 'remove_setting':
            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change imagepreview settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                                       'text': ERROR_MSG})
            else:
                status = remove_setting(configuration, abs_path, path,
                                        extension, output_objects)
            logger.debug('remove_setting exit status: %s' % str(status))
        elif action == 'get_setting':
            status = get_setting(configuration, abs_path, path,
                                 extension, output_objects)
            logger.debug('get_setting exit status: %s' % str(status))
        elif action == 'update_setting':
            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change imagepreview settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                                       'text': ERROR_MSG})
            else:
                status = update_setting(
                    configuration,
                    base_dir,
                    abs_path,
                    path,
                    extension,
                    accepted_joined_values,
                    output_objects,
                )
                logger.debug('update_setting exit status: %s'
                             % str(status))
        elif action == 'create_setting':

            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change imagepreview settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                                       'text': ERROR_MSG})
            else:
                status = create_setting(
                    configuration,
                    client_id,
                    base_dir,
                    abs_path,
                    path,
                    extension,
                    accepted_joined_values,
                    output_objects,
                )
                status = returnvalues.OK
            logger.debug('create_setting exit status: %s' % str(status))
        elif action == 'reset_setting':
            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change imagepreview settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                                       'text': ERROR_MSG})
            else:
                status = reset_settings(configuration, abs_path, path,
                                        output_objects, extension)
            logger.debug('reset exit status: %s' % str(status))
        elif action == 'get':

            status = get(configuration, base_dir, path, output_objects)
            logger.debug('get exit status: %s' % str(status))
        elif action == 'remove':
            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change imagepreview settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                                       'text': ERROR_MSG})
            else:
                status = remove(configuration, base_dir, abs_path,
                                path, output_objects)
                logger.debug('remove exit status: %s' % str(status))
        elif action == 'clean':
            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change imagepreview settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                                       'text': ERROR_MSG})
            else:
                status = clean(configuration, base_dir, abs_path, path,
                               output_objects)
                logger.debug('clean exit status: %s' % str(status))
        elif action == 'cleanrecursive':

            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change imagepreview settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                                       'text': ERROR_MSG})
            else:
                status = clean(
                    configuration,
                    base_dir,
                    abs_path,
                    path,
                    output_objects,
                    recursive=True,
                )
                logger.debug('cleanrecursive exit status: %s'
                             % str(status))
        elif action == 'refresh':

            if vgrid_owner == False:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Ownership of vgrid: '%s' required to change imagepreview settings" \
                    % vgrid_name
                output_objects.append({'object_type': 'error_text',
                                       'text': ERROR_MSG})
            else:
                status = refresh(
                    configuration,
                    client_id,
                    base_dir,
                    abs_path,
                    path,
                    output_objects,
                )
                logger.debug('refresh exit status: %s' % str(status))
        else:
            ERROR_MSG = "action: '%s' _NOT_ implemented yet" \
                % str(action)
            output_objects.append({'object_type': 'error_text',
                                   'text': ERROR_MSG})

    logger.debug('output_objects: %s' % str(output_objects))
    logger.debug('status: %s' % str(status))
    return (output_objects, status)
