#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cat - [insert a few words of module description on this line]
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Emulate the un*x function with the same name"""

import os
import glob

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables
from shared.parseflags import verbose, binary
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'path': REJECT_UNSET, 'dst': [''], 'flags': ['']}
    return ['file_output', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    status = returnvalues.OK
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
    patterns = accepted['path']
    dst = accepted['dst'][-1].lstrip(os.sep)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

    if dst:
        if not safe_handler(configuration, 'post', op_name, client_id,
                            get_csrf_limit(configuration), accepted):
            output_objects.append(
                {'object_type': 'error_text', 'text': '''Only accepting
                CSRF-filtered POST requests to prevent unintended updates'''
                 })
            return (output_objects, returnvalues.CLIENT_ERROR)

        dst_mode = "wb"
        # IMPORTANT: path must be expanded to abs for proper chrooting
        abs_dest = os.path.abspath(os.path.join(base_dir, dst))
        relative_dst = abs_dest.replace(base_dir, '')
        if not valid_user_path(abs_dest, base_dir, True):
            logger.warning('%s tried to %s into restricted path %s ! (%s)'
                           % (client_id, op_name, abs_dest, dst))
            output_objects.append({'object_type': 'error_text',
                                   'text': "invalid destination: '%s'" % \
                                   dst})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
    for pattern in patterns:

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
            output_objects.append({'object_type': 'file_not_found',
                                  'name': pattern})
            status = returnvalues.FILE_NOT_FOUND

        for real_path in match:
            output_lines = []
            relative_path = real_path.replace(base_dir, '')
            try:
                fd = open(real_path, 'r')

                # use file directly as iterator for efficiency

                for line in fd:
                    output_lines.append(line)
                fd.close()
            except Exception, exc:
                output_objects.append({'object_type': 'error_text',
                        'text': "%s: '%s': %s" % (op_name,
                        relative_path, exc)})
                logger.error("%s: failed on '%s': %s" % (op_name,
                             relative_path, exc))
                status = returnvalues.SYSTEM_ERROR
                continue
            if dst:
                try:
                    out_fd = open(abs_dest, dst_mode)
                    out_fd.writelines(output_lines)
                    out_fd.close()
                except Exception, exc:
                    output_objects.append({'object_type': 'error_text',
                                           'text': "write failed: '%s'" % exc})
                    logger.error("%s: write failed on '%s': %s" % (op_name,
                                                               abs_dest, exc))
                    status = returnvalues.SYSTEM_ERROR
                    continue
                output_objects.append({'object_type': 'text',
                        'text': "wrote %s to %s" % (relative_path,
                                                    relative_dst)})
                # Prevent truncate after first write
                dst_mode = "ab+"
            else:
                entry = {'object_type': 'file_output',
                         'lines': output_lines,
                         'wrap_binary': binary(flags),
                         'wrap_targets': ['lines']}
                if verbose(flags):
                    entry['path'] = relative_path
                output_objects.append(entry)

                # TODO: rip this hack out into real download handler?
                # Force download of files when output_format == 'file_format'
                # This will only work for the first file matching a glob when
                # using file_format.
                # And it is supposed to only work for one file.
                if user_arguments_dict.has_key('output_format'):
                    output_format = user_arguments_dict['output_format'][0]
                    if output_format == 'file':
                        output_objects.append(
                            {'object_type': 'start', 'headers':
                             [('Content-Disposition',
                               'attachment; filename="%s";' % \
                               os.path.basename(real_path))]})
            
    return (output_objects, status)


