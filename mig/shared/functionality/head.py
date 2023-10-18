#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# head - show initial lines of one or more files
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

from __future__ import absolute_import

import glob
import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.fileio import read_head_lines
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.init import initialize_main_variables, start_download
from mig.shared.parseflags import verbose, binary
from mig.shared.safeinput import valid_path_pattern
from mig.shared.userio import GDPIOLogError, gdp_iolog
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'flags': [''], 'lines': [20], 'path': REJECT_UNSET}
    return ['file_output', defaults]


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        # NOTE: path can use wildcards
        typecheck_overrides={'path': valid_path_pattern},
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    lines = int(accepted['lines'][-1])
    pattern_list = accepted['path']

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    status = returnvalues.OK

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text':
                                   '%s using flag: %s' % (op_name, flag)})

    src_mode = "rb"
    if binary(flags):
        force_file = True
    elif user_arguments_dict.get('output_format', ['txt'])[0] == 'file':
        force_file = True
    else:
        force_file = False
        src_mode = "r"

    for pattern in pattern_list:

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern)
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.warning('%s tried to %s restricted path %s ! (%s)'
                               % (client_id, op_name, abs_path, pattern))
                continue
            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append({'object_type': 'file_not_found',
                                   'name': pattern})
            status = returnvalues.FILE_NOT_FOUND

        for abs_path in match:
            relative_path = abs_path.replace(base_dir, '')
            output_lines = []
            try:
                gdp_iolog(configuration,
                          client_id,
                          environ['REMOTE_ADDR'],
                          'accessed',
                          [relative_path])

                content = read_head_lines(abs_path, lines, logger,
                                          mode=src_mode)
                if content is None:
                    raise Exception("could not read file")
                output_lines += content
            except Exception as exc:
                if not isinstance(exc, GDPIOLogError):
                    gdp_iolog(configuration,
                              client_id,
                              environ['REMOTE_ADDR'],
                              'accessed',
                              [relative_path],
                              failed=True,
                              details=exc)
                logger.error("%s: failed on '%s': %s" % (op_name,
                                                         relative_path, exc))
                output_objects.append({'object_type': 'error_text', 'text':
                                       "%s failed on %r" % (op_name,
                                                            relative_path)})
                status = returnvalues.SYSTEM_ERROR
                continue
            entry = {'object_type': 'file_output',
                     'lines': output_lines,
                     'wrap_binary': binary(flags),
                     'wrap_targets': ['lines']}
            if verbose(flags):
                entry['path'] = relative_path
            # Force download of files when output_format == 'file'
            if force_file:
                download_marker = start_download(configuration, abs_path,
                                                 output_lines)
                output_objects.append(download_marker)
            output_objects.append(entry)

    return (output_objects, status)
