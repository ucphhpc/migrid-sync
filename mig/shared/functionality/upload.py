#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# upload - Plain and efficient file upload back end
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

# Minimum Intrusion Grid

"""Plain file upload back end"""

import os
import glob

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.useradm import client_id_dir
from shared.validstring import valid_user_path

block_size = 1024 * 1024


def signature():
    """Signature of the main function"""

    defaults = {'path': REJECT_UNSET, 'fileupload': REJECT_UNSET, 
                'restrict':False}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]

    # IMPORTANT: the CGI front end forces the input extraction to be delayed
    # We must manually extract and parse input here to avoid memory explosion
    # for huge files!

    # TODO: explosions still happen sometimes!
    # Most likely because of Apache SSL renegotiations which have
    # no other way of storing input

    extract_input = user_arguments_dict['__DELAYED_INPUT__']
    logger.info('Extracting input in %s' % op_name)
    form = extract_input()
    file_item = None
    file_name = ''
    user_arguments_dict = {}
    if form.has_key('fileupload'):
        file_item = form['fileupload']
        file_name = file_item.filename
        user_arguments_dict['fileupload'] = 'true'
        user_arguments_dict['path'] = [file_name]
    if form.has_key('path'):
        user_arguments_dict['path'] = [form['path'].value]
    if form.has_key('restrict'):
        user_arguments_dict['restrict'] = [form['restrict'].value]
    logger.info('Filtered input is: %s' % user_arguments_dict)

    # Now validate parts as usual
    
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

    path = accepted['path'][-1]
    restrict = accepted['restrict'][-1]

    logger.info('Filtered input validated with result: %s' % accepted)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    output_objects.append({'object_type': 'header', 'text'
                          : 'Uploading file'})

    # Check directory traversal attempts before actual handling to avoid leaking
    # information about file system layout while allowing consistent error messages

    real_path = ''
    unfiltered_match = glob.glob(base_dir + path)
    for server_path in unfiltered_match:
        real_path = os.path.abspath(server_path)
        if not valid_user_path(real_path, base_dir, True):

            # ../*/* is technically allowed to match own files.

            logger.error('Warning: %s tried to %s outside own home! (path %s)'
                          % (client_id, op_name, path))
            output_objects.append({'object_type': 'error_text', 'text'
                                  : "You're only allowed to write your own files! (%s expands to an illegal path)"
                                   % path})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Do not allow modification of htaccess files

    if '.htaccess' == os.path.basename(real_path):
        logger.error('Warning: %s tried to %s htaccess! (path %s)'
                      % (client_id, op_name, path))
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Access to .htaccess files is prohibited!'
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if real_path == '':
        real_path = base_dir + path
        if not valid_user_path(real_path, base_dir, True):
            logger.error('Warning: %s tried to %s outside own home! (path %s)'
                          % (client_id, op_name, path))
            output_objects.append({'object_type': 'error_text', 'text'
                                  : "You're only allowed to write your own files! (%s expands to an illegal path)"
                                   % path})
            return (output_objects, returnvalues.CLIENT_ERROR)

    if os.path.isdir(real_path):
        real_path = os.path.join(real_path, os.path.basename(file_name))
        if not valid_user_path(real_path, base_dir, True):
            logger.error('Warning: %s tried to %s outside own home! (path %s)'
                          % (client_id, op_name, path))
            output_objects.append({'object_type': 'error_text', 'text'
                                  : "You're only allowed to write your own files! (%s expands to an illegal path)"
                                   % path})
            return (output_objects, returnvalues.CLIENT_ERROR)

    try:
        logger.info('Writing %s' % real_path)
        upload_fd = open(real_path, 'wb')
        while True:
            chunk = file_item.file.read(block_size)
            if not chunk:
                break
            upload_fd.write(chunk)
        upload_fd.close()
        logger.info('Wrote %s' % real_path)

        if restrict:
            os.chmod(real_path, 0600)

        # everything ok

        output_objects.append({'object_type': 'text', 'text'
                              : 'Saved changes to %s.' % path})
    except Exception, exc:

        # Don't give away information about actual fs layout

        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s could not be written! (%s)'
                               % (path, str(exc).replace(base_dir, ''
                              ))})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    return (output_objects, returnvalues.OK)


