#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# upload - Plain and efficient file upload back end
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

"""Plain file upload back end"""

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables
from shared.parseflags import verbose
from shared.validstring import valid_user_path

block_size = 1024 * 1024


def signature():
    """Signature of the main function"""

    defaults = {
        'flags': [''],
        'path': REJECT_UNSET,
        'fileupload': REJECT_UNSET, 
        'restrict': [False],
        }
    return ['html_form', defaults]

def write_chunks(path, file_obj, restrict):
    """Write file_obj bytes to path and set strict permissions if restrict
    is set. Removes file if upload fails for some reason.
    """
    try:
        upload_fd = open(path, 'wb')
        while True:
            chunk = file_obj.read(block_size)
            if not chunk:
                break
            upload_fd.write(chunk)
        upload_fd.close()
        if restrict:
            os.chmod(path, 0600)
        return True
    except Exception, exc:
        os.remove(path)
        raise exc

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
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
    logger.info('After extracting input in %s' % op_name)
    file_item = None
    file_name = ''
    user_arguments_dict = {}
    if form.has_key('fileupload'):
        file_item = form['fileupload']
        file_name = file_item.filename
        user_arguments_dict['fileupload'] = ['true']
        user_arguments_dict['path'] = [file_name]
    if form.has_key('path'):
        user_arguments_dict['path'] = [form['path'].value]
    if form.has_key('restrict'):
        user_arguments_dict['restrict'] = [form['restrict'].value]
    else:
        user_arguments_dict['restrict'] = defaults['restrict']
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

    flags = ''.join(accepted['flags'])
    path = accepted['path'][-1]
    restrict = accepted['restrict'][-1]

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not configuration.site_enable_griddk:
        output_objects.append({'object_type': 'text', 'text':
                               '''Grid.dk features are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    logger.info('Filtered input validated with result: %s' % accepted)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

    output_objects.append({'object_type': 'header', 'text'
                          : 'Uploading file'})

    # Check directory traversal attempts before actual handling to avoid
    # leaking information about file system layout while allowing consistent
    # error messages

    real_path = os.path.realpath(os.path.join(base_dir, path))

    # Implicit destination

    if os.path.isdir(real_path):
        real_path = os.path.join(real_path, os.path.basename(file_name))

    if not valid_user_path(configuration, real_path, base_dir, True):
        logger.warning('%s tried to %s restricted path %s ! (%s)'
                       % (client_id, op_name, real_path, path))
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : "Invalid destination (%s expands to an illegal path)" % path})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not os.path.isdir(os.path.dirname(real_path)):
        output_objects.append({'object_type': 'error_text', 'text'
                               : "cannot write: no such file or directory: %s)"
                               % path})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # We fork off here and redirect the user to a progress page for user
    # friendly output and to avoid cgi timeouts from killing the upload.
    # We use something like the Active State python recipe for daemonizing
    # to properly detach from the CGI process and continue in the background.
    # Please note that we only close stdio file descriptors to avoid closing
    # the fileupload.

    file_item.file.seek(0, 2)
    total_size = file_item.file.tell()
    file_item.file.seek(0, 0)

    try:
        pid = os.fork()
        if pid == 0:
            os.setsid()
            pid = os.fork()
            if pid == 0:
                os.chdir('/')
                os.umask(0)
                for fno in range(3):
                    try: 
                        os.close(fno)
                    except OSError:
                        pass
            else:
                os._exit(0)
    except OSError, ose:
        output_objects.append({'object_type': 'error_text', 'text'
                               : '%s upload could not background! (%s)'
                               % (path, str(ose).replace(base_dir, ''
                                                         ))})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # The detached grand child takes care of writing and the original process
    # redirects to progress page

    if pid == 0:
        try:
            write_chunks(real_path, file_item.file, restrict)
        except Exception, exc:
            pass
    else:
        output_objects.append({'object_type': 'text', 'text'
                               : 'Upload of %s in progress' % path})
        progress_link = {'object_type': 'link', 'text': 'show progress',
                         'destination': 'uploadprogress.py?path=%s;size=%d'
                         % (path, total_size)}
        output_objects.append(progress_link)
                        
    return (output_objects, status)
