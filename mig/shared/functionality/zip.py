#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# zip - [insert a few words of module description on this line]
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""Archiver used to pack a one or more files and directories in
the home directory of a MiG user into a zip file.
"""

import os
import zipfile
import glob

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables, find_entry
from shared.parseflags import verbose
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'src': REJECT_UNSET, 'flags': [''],
                'dst': REJECT_UNSET, 'current_dir': ['.']}
    return ['link', defaults]


def usage(output_objects):
    """Usage help"""

    output_objects.append({'object_type': 'header', 'text': 'zip usage:'})
    output_objects.append(
        {'object_type': 'text', 'text'
         : 'SERVER_URL/zip.py?[output_format=(html|txt|xmlrpc|..);]'
         '[flags=h;][src=src_path;[...]]src=src_path;dst=dst_path'})
    output_objects.append(
        {'object_type': 'text', 'text'
         : '- output_format specifies how the script should format the output'
         })
    output_objects.append(
        {'object_type': 'text', 'text'
         : '- flags is a string of character flags to be passed to the script'
         })
    output_objects.append(
        {'object_type': 'text', 'text'
         : '- each src specifies a path in your home to include in the archive'
         })
    output_objects.append(
        {'object_type': 'text', 'text'
         : '- dst is the path where the generated zip archive will be stored'
         })
    return (output_objects, returnvalues.OK)


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
        return (accepted, returnvalues.CLIENT_ERROR)

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    dst = accepted['dst'][-1]
    pattern_list = accepted['src']
    current_dir = accepted['current_dir'][-1]

    # All paths are relative to current_dir
    
    pattern_list = [os.path.join(current_dir, i) for i in pattern_list]
    dst = os.path.join(current_dir, dst)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Zip archiver'
    output_objects.append({'object_type': 'header', 'text'
                          : 'Zip archiver'})

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

    if 'h' in flags:
        usage(output_objects)

    real_dir = os.path.abspath(os.path.join(base_dir,
                                            current_dir.lstrip(os.sep)))
    if not valid_user_path(real_dir, base_dir, True):

        # out of bounds

        output_objects.append({'object_type': 'error_text', 'text'
                              : "You're not allowed to work in %s!"
                               % current_dir})
        logger.warning('%s tried to %s restricted path %s ! (%s)'
                       % (client_id, op_name, real_dir, current_dir))
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                           : "working in %s" % current_dir})

    real_dest = os.path.join(base_dir, dst.lstrip(os.sep))

    # Don't use real_path in output as it may expose underlying
    # fs layout.

    relative_dest = real_dest.replace(base_dir, '')
    if not valid_user_path(real_dest, base_dir, True):

        # out of bounds

        output_objects.append(
            {'object_type': 'error_text', 'text'
             : "Invalid path! (%s expands to an illegal path)" % dst})
        logger.warning('%s tried to %s restricted path %s !(%s)'
                       % (client_id, op_name, real_dest, dst))
        return (output_objects, returnvalues.CLIENT_ERROR)


    if not os.path.isdir(os.path.dirname(real_dest)):
        output_objects.append({'object_type': 'error_text', 'text'
                               : "No such destination directory: %s"
                               % os.path.dirname(relative_dest)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    status = returnvalues.OK

    # Force compression
    zip_file = zipfile.ZipFile(real_dest, 'w', zipfile.ZIP_DEFLATED)
    for pattern in pattern_list:

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern)
        match = []
        for server_path in unfiltered_match:
            real_path = os.path.abspath(server_path)
            if not valid_user_path(real_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.warning('%s tried to %s restricted path %s ! (%s)'
                               % (client_id, op_name, real_path, pattern))
                continue
            match.append(real_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append({'object_type': 'error_text', 'text'
                                   : "%s: cannot zip '%s': no valid src paths"
                                   % (op_name, pattern)})
            status = returnvalues.CLIENT_ERROR
            continue

        for real_path in match:
            relative_path = real_path.replace(base_dir, '')
            if real_dest == real_path:
                    output_objects.append({'object_type': 'text', 'text'
                                           : 'skipping destination file %s'
                                           % relative_dest})
                    continue
            if verbose(flags):
                output_objects.append({'object_type': 'file', 'name'
                                       : relative_path})

            try:
                if os.path.isdir(real_path):
                    for root, dirs, files in os.walk(real_path):
                        relative_root = root.replace(real_dir + os.sep, '')
                        for entry in files:
                            real_target = os.path.join(root, entry)
                            relative_target = os.path.join(relative_root,
                                                           entry)
                            if real_dest == real_target:
                                output_objects.append(
                                    {'object_type': 'text', 'text'
                                     : 'skipping destination file %s'
                                     % relative_dest})
                                continue
                            zip_file.write(real_target, relative_target)
                        if not files:
                            dir_info = zipfile.ZipInfo(relative_root + os.sep)
                            zip_file.writestr(dir_info, '')
                else:
                    zip_file.write(real_path, real_path.replace(real_dir, ''))
            except Exception, exc:
                output_objects.append({'object_type': 'error_text', 'text'
                                       : "%s: '%s': %s" % (op_name,
                                                           relative_path, exc)
                                       })
                logger.error("%s: failed on '%s': %s" % (op_name,
                                                         relative_path, exc))
                status = returnvalues.SYSTEM_ERROR
                continue

            output_objects.append({'object_type': 'text', 'text'
                                   : 'Added %s to %s'
                                   % (relative_path, relative_dest)})

    zip_file.close()

    # Verify CRC

    try:
        zip_file = zipfile.ZipFile(real_dest, 'r')
        err = zip_file.testzip()
        zip_file.close()
    except Exception, exc:
        err = "Could not open zip file: %s" % exc
    if err:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Zip file integrity check failed! (%s)'
                               % err})
        status = returnvalues.SYSTEM_ERROR
    else:
        output_objects.append({'object_type': 'text', 'text'
                              : 'Zip archive of %s is now available in %s'
                               % (', '.join(pattern_list), relative_dest)})
        output_objects.append({'object_type': 'link', 'text'
                               : 'Download zip archive', 'destination'
                               : os.path.join('..', client_dir,
                                              relative_dest)})

    return (output_objects, status)
