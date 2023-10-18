#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# statpath - file or directory stats
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

import os
import glob

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.init import initialize_main_variables
from mig.shared.parseflags import verbose
from mig.shared.safeinput import valid_path_pattern
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'path': REJECT_UNSET, 'flags': ['']}
    return ['stats', defaults]


def stat_path(real_path, logger):
    """Call OS stat on provided path"""
    try:
        stat_info = os.stat(real_path)
    except Exception as err:

        # Don't give away FS information - only log full failure reason

        logger.warning('ls failed to stat %s: %s' % (real_path, err))
        return (False, 'Internal error: stat failed!')

    stat = {}
    try:
        stat['device'] = stat_info.st_dev
        stat['inode'] = stat_info.st_ino
        stat['mode'] = stat_info.st_mode
        stat['nlink'] = stat_info.st_nlink
        stat['uid'] = stat_info.st_uid
        stat['gid'] = stat_info.st_gid
        stat['rdev'] = stat_info.st_rdev
        stat['size'] = stat_info.st_size
        stat['atime'] = stat_info.st_atime
        stat['mtime'] = stat_info.st_mtime
        stat['ctime'] = stat_info.st_ctime
    except Exception as exc:
        return (False, 'Could not get all stat info: %s' % exc)
    return (True, stat)


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

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

    flags = accepted['flags']
    patterns = accepted['path']

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    status = returnvalues.OK

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text': '%s using flag: %s' % (op_name,
                                                                                         flag)})

    for pattern in patterns:

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern)
        match = []

        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):
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
        stats = []
        for abs_path in match:
            relative_path = abs_path.replace(base_dir, '')

            try:
                (stat_status, stat) = stat_path(abs_path, logger)
                if stat_status:
                    if verbose(flags):
                        stat['name'] = relative_path
                    stat['object_type'] = 'stat'
                    stats.append(stat)
                else:
                    output_objects.append({'object_type': 'error_text',
                                           'text': stat})
                    status = returnvalues.SYSTEM_ERROR
            except Exception as exc:
                logger.error("%s: failed on %r: %s" % (op_name, relative_path,
                                                       exc))
                output_objects.append({'object_type': 'error_text',
                                       'text': "%s: %r" % (op_name,
                                                           relative_path)})
                status = returnvalues.SYSTEM_ERROR
                continue
            output_objects.append({'object_type': 'stats', 'stats': stats})
    return (output_objects, status)
