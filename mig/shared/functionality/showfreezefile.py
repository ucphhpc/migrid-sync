#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showfreezefile - View own frozen archive files
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

"""Show the requested file located in a given frozen archive belonging to the
client.
"""

from __future__ import absolute_import

import mimetypes
import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.fileio import read_file, read_file_lines
from mig.shared.freezefunctions import is_frozen_archive
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.init import initialize_main_variables
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'freeze_id': REJECT_UNSET, 'path': REJECT_UNSET}
    return ['file_output', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        # NOTE: path cannot use wildcards here
        typecheck_overrides={},
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    freeze_id = accepted['freeze_id'][-1]
    path = accepted['path'][-1]

    if not is_frozen_archive(client_id, freeze_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''No such archive %s owned by you''' %
                               freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    client_dir = client_id_dir(client_id)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.freeze_home,
                                            client_dir, freeze_id)) + os.sep

    # TODO: remove this legacy fall back when done migrating archives
    if not os.path.isdir(base_dir):
        base_dir = os.path.abspath(os.path.join(configuration.freeze_home,
                                                freeze_id)) + os.sep

    # Strip leading slashes to avoid join() throwing away prefix

    rel_path = path.lstrip(os.sep)
    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
    if not valid_user_path(configuration, abs_path, base_dir, True):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''You are not allowed to use paths outside the
archive dir.'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if user_arguments_dict.get('output_format', ['txt'])[0] == 'file':
        force_file = True
    else:
        force_file = False

    logger.debug('reading archive private file %s' % abs_path)
    output_lines = []
    try:
        if force_file:
            # NOTE: we need to preserve binary data
            output_lines = [read_file(abs_path, logger, mode='rb')]
        else:
            output_lines += read_file_lines(abs_path, logger, mode='r')
        entry = {'object_type': 'file_output',
                 'lines': output_lines,
                 'wrap_binary': True,
                 'wrap_targets': ['lines']}

        # NOTE: override normal delivery if download was requested
        if force_file:
            logger.info('return %db from archive private file %s of size %db' %
                        (len(output_lines[0]), abs_path,
                         os.path.getsize(abs_path)))
            # Cut away all the usual web page formatting to show only contents
            # Insert explicit content type for a better client experience and
            # to make sure clients don't break download early because they
            # think it is plain text and find a bogus EOF in binary data.
            (content_type, _) = mimetypes.guess_type(abs_path)
            if not content_type:
                content_type = 'application/octet-stream'
            # NOTE: we need to set content length to fit binary data
            output_objects = [{'object_type': 'start',
                               'headers': [
                                   ('Content-Type', content_type),
                                   ('Content-Length', "%d" %
                                    len(output_lines[0])),
                                   ('Content-Disposition',
                                    'attachment; filename="%s";' %
                                    os.path.basename(abs_path))
                               ]
                               }]

        # Always insert entry
        output_objects.append(entry)
    except Exception as exc:
        logger.error('Error reading archive private file %s' % exc)
        output_objects.append({'object_type': 'error_text', 'text':
                               'Error reading archive private file %s'
                               % rel_path})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    return (output_objects, returnvalues.OK)
