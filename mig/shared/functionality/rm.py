#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rm - [insert a few words of module description on this line]
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

"""Module that enables a user to delete files and directories
in his home directory.
It is possible to supply a recursive flag to enable recursive deletes.
"""

import os
import glob

import shared.returnvalues as returnvalues
from shared.base import client_id_dir, invisible_file
from shared.functional import validate_input, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.parseflags import verbose, recursive
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {
        'flags': [''],
        'iosessionid': [''],
        'path': REJECT_UNSET,
        'delete': [''],
        'allbox': [''],
        }
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    pattern_list = accepted['path']
    iosessionid = accepted['iosessionid'][-1]

    # output_objects.append({"object_type":"text", "text": "fil %s" % (pattern_list)})

    if not client_id:
        if not iosessionid.strip() or not iosessionid.isalnum():

            # deny

            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'No sessionid or invalid sessionid supplied!'
                                  })
            return (output_objects, returnvalues.CLIENT_ERROR)
        base_dir_no_sessionid = \
            os.path.realpath(configuration.webserver_home) + os.sep

        base_dir = \
            os.path.realpath(os.path.join(configuration.webserver_home,
                             iosessionid)) + os.sep
        if not os.path.isdir(base_dir):

            # deny

            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Invalid sessionid!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        if not valid_user_path(base_dir, base_dir_no_sessionid, True):

            # deny

            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Invalid sessionid!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
    else:

        # TODO: this is a hack to allow truncate - fix 'put' empty files

        # Please note that base_dir must end in slash to avoid access to other
        # user dirs when own name is a prefix of another user name

        base_dir = \
            os.path.abspath(os.path.join(configuration.user_home,
                            client_dir)) + os.sep

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

    for pattern in pattern_list:

        # Check directory traversal attempts before actual handling to avoid leaking
        # information about file system layout while allowing consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern)
        match = []
        for server_path in unfiltered_match:
            real_path = os.path.abspath(server_path)
            if not valid_user_path(real_path, base_dir, True):

                # out of bounds - save user warning for later to allow partial match:
                # ../*/* is technically allowed to match own files.

                logger.error('Warning: %s tried to %s restricted path %s! ( %s)'
                             % (client_id, op_name, real_path, pattern))
                continue
            match.append(real_path)

        # Now actually treat list of allowed matchings and notify if no (allowed) match

        if not match:
            output_objects.append({'object_type': 'file_not_found',
                                  'name': pattern})
            status = returnvalues.FILE_NOT_FOUND

        for real_path in match:
            relative_path = real_path.replace(base_dir, '')
            if verbose(flags):
                output_objects.append({'object_type': 'file', 'name'
                        : relative_path})

            # Make it harder to accidentially delete too much - e.g. do not delete
            # VGrid files without explicit selection of subdir contents

            if real_path == os.path.abspath(base_dir):
                output_objects.append({'object_type': 'warning', 'text'
                        : "You're not allowed to delete your entire home directory!"
                        })
                status = returnvalues.CLIENT_ERROR
                continue
            if os.path.islink(real_path):
                output_objects.append({'object_type': 'warning', 'text'
                        : "You're not allowed to delete entire VGrid dirs!"
                        })
                status = returnvalues.CLIENT_ERROR
                continue
            if os.path.isdir(real_path) and recursive(flags):

                # bottom up traversal of the file tree since rmdir is limited to
                # empty dirs

                for (root, dirs, files) in os.walk(real_path,
                        topdown=False):
                    for name in files:
                        path = os.path.join(root, name)
                        relative_path = path.replace(base_dir, '')
                        # Traversal may find additional invisible files to skip
                        if invisible_file(name):
                            continue
                        if verbose(flags):
                            output_objects.append({'object_type': 'file'
                                    , 'name': relative_path})
                        try:
                            os.remove(path)
                        except Exception, exc:
                            output_objects.append({'object_type'
                                    : 'error_text', 'text'
                                    : "%s: '%s': %s" % (op_name,
                                    relative_path, exc)})
                            logger.error("%s: failed on '%s': %s"
                                     % (op_name, relative_path, exc))
                            status = returnvalues.SYSTEM_ERROR

                    for name in dirs:
                        path = os.path.join(root, name)
                        relative_path = path.replace(base_dir, '')
                        if verbose(flags):
                            output_objects.append({'object_type': 'file'
                                    , 'name': relative_path})
                        try:
                            os.rmdir(path)
                        except Exception, exc:
                            output_objects.append({'object_type'
                                    : 'error_text', 'text'
                                    : "%s: '%s': %s" % (op_name,
                                    relative_path, exc)})
                            logger.error("%s: failed on '%s': %s"
                                     % (op_name, relative_path, exc))
                            status = returnvalues.SYSTEM_ERROR

                # Finally remove base directory

                relative_path = real_path.replace(base_dir, '')
                try:
                    os.rmdir(real_path)
                except Exception, exc:
                    output_objects.append({'object_type': 'error_text',
                            'text': "%s: '%s': %s" % (op_name,
                            relative_path, exc)})
                    logger.error("%s: failed on '%s': %s" % (op_name,
                                 relative_path, exc))
                    status = returnvalues.SYSTEM_ERROR
            else:
                relative_path = real_path.replace(base_dir, '')
                try:
                    os.remove(real_path)
                except Exception, exc:
                    output_objects.append({'object_type': 'error_text',
                            'text': "%s: '%s': %s" % (op_name,
                            relative_path, exc)})
                    logger.error("%s: failed on '%s'" % (op_name,
                                 relative_path))
                    status = returnvalues.SYSTEM_ERROR
                    continue

    return (output_objects, status)


