#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# zip - [insert a few words of module description on this line]
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

"""Archiver used to pack a one or more files and directories in
the home directory of a MiG user into a zip file.
"""

import os
import sys
import zipfile
import time
import glob

from shared.validstring import valid_user_path
from shared.parseflags import verbose
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'path': [REJECT_UNSET], 'flags': [''],
                'dst': REJECT_UNSET}
    return ['link', defaults]


def usage(output_objects):
    output_objects.append({'object_type': 'header', 'text': 'zip usage:'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : 'SERVER_URL/cgi-bin/zip.py?[output_format=(html|txt|xmlrpc|..);][flags=h;][path=src_path;[...]]path=src_path;dst=dst_path'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : '- output_format specifies how the script should format the output'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : '- flags is a string of one character flags to be passed to the script'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : '- each path specifies a file or directory in your MiG home to include in the zip archive'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : '- dst is the path where the generated zip archive will be stored'
                          })
    return (output_objects, returnvalues.OK)


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)

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
    flags = ''.join(accepted['flags'])
    dst = accepted['dst'][-1]
    patterns = accepted['path']

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(configuration.user_home + os.sep
                                + cert_name_no_spaces) + os.sep
    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG zip archiver'})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG zip archiver'})

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

    if 'h' in flags:
        usage(output_objects)

    real_dest = base_dir + dst
    dst_list = glob.glob(real_dest)
    if not dst_list:

        # New destination?

        if not glob.glob(os.path.dirname(real_dest)):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Illegal dst path provided - directory part does not exist!'
                                  })
            return (output_objects, returnvalues.CLIENT_ERROR)
        else:
            dst_list = [real_dest]

    # Use last match in case of multiple matches

    dest = dst_list[-1]
    if len(dst_list) > 1:
        output_objects.append({'object_type': 'warning', 'text'
                              : 'dst (%s) matches multiple targets - using last: %s'
                               % (dst, dest)})

    real_dest = os.path.abspath(dest)

    # Don't use real_path in output as it may expose underlying
    # fs layout.

    relative_dest = real_dest.replace(base_dir, '')
    if not valid_user_path(real_dest, base_dir, True):

        # out of bounds

        output_objects.append({'object_type': 'error_text', 'text'
                              : "You're only allowed to write to your own home directory! dest (%s) expands to an illegal path (%s)"
                               % (dst, relative_dest)})
        logger.error('Warning: %s tried to %s file(s) to destination %s outside own home! (using pattern %s)'
                      % (cert_name_no_spaces, op_name, real_dest, dst))
        return (output_objects, returnvalues.CLIENT_ERROR)

    zip_file = zipfile.ZipFile(real_dest, 'w')

    status = returnvalues.OK

    for pattern in patterns:

        # Check directory traversal attempts before actual handling
        # to avoid leaking information about file system layout while
        # allowing consistent error messages
        # NB: Globbing disabled on purpose here

        unfiltered_match = [base_dir + pattern]
        match = []
        for server_path in unfiltered_match:
            real_path = os.path.abspath(server_path)
            if not valid_user_path(real_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.error('Warning: %s tried to %s %s outside own home! (%s)'
                              % (cert_name_no_spaces, op_name,
                             real_path, pattern))
                continue
            match.append(real_path)

    # Now actually treat list of allowed matchings and notify if
    # no (allowed) match

    if not match:
        output_objects.append({'object_type': 'error_text', 'text'
                              : "%s: cannot zip '%s': no valid paths"
                               % (op_name, pattern)})
        status = returnvalues.CLIENT_ERROR

    for real_path in match:
        relative_path = real_path.replace(base_dir, '')
        if verbose(flags):
            output_objects.append({'object_type': 'file', 'name'
                                  : relative_path})

        try:
            if os.path.isdir(real_path):

                # Directory write is not supported - add each file manually
                # TODO: This only catches subfiles not suddirs!

                for subpath in os.listdir(real_path):
                    zip_file.write(real_path + os.sep + subpath,
                                   relative_path + os.sep + subpath)
            else:
                zip_file.write(real_path, relative_path)
        except Exception, exc:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : "%s: '%s': %s" % (op_name,
                                  relative_path, exc.strerror)})
            logger.error("%s: failed on '%s': %s" % (op_name,
                         relative_path, exc))
            status = returnvalues.SYSTEM_ERROR

    zip_file.close()

    # Verify CRC

    zip_file = zipfile.ZipFile(real_dest, 'r')
    err = zip_file.testzip()
    zip_file.close()
    if err:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Zip file integrity check failed! (%s)'
                               % err})
        status = returnvalues.SYSTEM_ERROR
    else:
        output_objects.append({'object_type': 'text', 'text'
                              : 'Zip archive of %s is now available in %s'
                               % (', '.join(patterns), relative_path)})
        output_objects.append({'object_type': 'link', 'text'
                              : 'Download zip archive', 'destination'
                              : os.path.join('..', cert_name_no_spaces,
                              relative_dest)})

    return (output_objects, status)


