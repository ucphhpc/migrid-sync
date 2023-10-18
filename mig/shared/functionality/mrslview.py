#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mrslview - show user-friendly job info
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

"""Show a human readable version of the saved internal mRSL dictionary"""

from __future__ import absolute_import

import os
import glob

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.fileio import unpickle
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.init import initialize_main_variables
from mig.shared.mrslkeywords import get_keywords_dict
from mig.shared.parseflags import verbose
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'job_id': REJECT_UNSET, 'flags': ['']}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
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

    flags = accepted['flags']
    patterns = accepted['job_id']

    if not configuration.site_enable_jobs:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Job execution is not enabled on this system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = \
        os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                                     client_dir)) + os.sep

    mrsl_keywords_dict = get_keywords_dict(configuration)

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text':
                                   '%s using flag: %s' % (op_name, flag)})

    for pattern in patterns:

        # Add file extension

        pattern += '.mRSL'

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
            output_objects.append(
                {'object_type': 'file_not_found', 'name': pattern})
            status = returnvalues.FILE_NOT_FOUND

        for abs_path in match:
            output_lines = []
            relative_path = abs_path.replace(base_dir, '')
            try:
                mrsl_dict = unpickle(abs_path, logger)
                if not mrsl_dict:
                    raise Exception('could not load job mRSL')
                for (key, val) in mrsl_dict.items():
                    if not key in mrsl_keywords_dict:
                        continue
                    if not val:
                        continue
                    output_lines.append('::%s::\n' % key)
                    if 'multiplestrings' == mrsl_keywords_dict[key]['Type']:
                        for line in val:
                            output_lines.append('%s\n' % line)
                    elif 'multiplekeyvalues' == mrsl_keywords_dict[key]['Type']:
                        for (left, right) in val:
                            output_lines.append('%s=%s\n' % (left, right))
                    else:
                        output_lines.append('%s\n' % val)
                    output_lines.append('\n')
            except Exception as exc:
                output_objects.append({'object_type': 'error_text', 'text':
                                       "%s: can't show %r" % (op_name,
                                                              relative_path)})
                logger.error("%s: failed on %r: %s" % (op_name, abs_path, exc))
                status = returnvalues.SYSTEM_ERROR
                continue
            if verbose(flags):
                output_objects.append(
                    {'object_type': 'file_output', 'path': relative_path,
                     'lines': output_lines})
            else:
                output_objects.append(
                    {'object_type': 'file_output', 'lines': output_lines})

    return (output_objects, status)
