#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# chksum - Calculate a checksum for one or more files
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

"""Emulate the un*x functions like md5sum and sha1sum"""

from __future__ import absolute_import

import os
import glob

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import default_max_chunks
from mig.shared.fileio import md5sum_file, sha1sum_file, sha256sum_file, \
    sha512sum_file, write_file, check_write_access
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables
from mig.shared.parseflags import verbose
from mig.shared.safeinput import valid_path_pattern
from mig.shared.validstring import valid_user_path

_algo_map = {'md5': md5sum_file, 'sha1': sha1sum_file,
             'sha256': sha256sum_file, 'sha512': sha512sum_file}


def signature():
    """Signature of the main function"""

    defaults = {'flags': [''], 'hash_algo': ['md5'], 'max_chunks':
                [default_max_chunks], 'path': REJECT_UNSET, 'dst': [''],
                'current_dir': ['.']}
    return ['file_output', defaults]


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
        # NOTE: path can use wildcards, dst and current_dir cannot
        typecheck_overrides={'path': valid_path_pattern},
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    algo_list = accepted['hash_algo']
    max_chunks = int(accepted['max_chunks'][-1])
    pattern_list = accepted['path']
    dst = accepted['dst'][-1]
    current_dir = accepted['current_dir'][-1].lstrip(os.sep)

    # All paths are relative to current_dir

    pattern_list = [os.path.join(current_dir, i) for i in pattern_list]
    if dst:
        dst = os.path.join(current_dir, dst)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    status = returnvalues.OK

    if verbose(flags):
        for flag in flags:
            output_objects.append(
                {'object_type': 'text', 'text': '%s using flag: %s' % (op_name,
                                                                       flag)})

    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_dir = os.path.abspath(os.path.join(base_dir,
                                           current_dir.lstrip(os.sep)))
    if not valid_user_path(configuration, abs_dir, base_dir, True):
        output_objects.append({'object_type': 'error_text', 'text':
                               "You're not allowed to work in %s!"
                               % current_dir})
        logger.warning('%s tried to %s restricted path %s ! (%s)'
                       % (client_id, op_name, abs_dir, current_dir))
        return (output_objects, returnvalues.CLIENT_ERROR)

    if verbose(flags):
        output_objects.append({'object_type': 'text', 'text':
                               "working in %s" % current_dir})

    if dst:
        if not safe_handler(configuration, 'post', op_name, client_id,
                            get_csrf_limit(configuration), accepted):
            output_objects.append(
                {'object_type': 'error_text', 'text': '''Only accepting
                CSRF-filtered POST requests to prevent unintended updates'''
                 })
            return (output_objects, returnvalues.CLIENT_ERROR)

        # NOTE: dst already incorporates current_dir prefix here
        # IMPORTANT: path must be expanded to abs for proper chrooting
        abs_dest = os.path.abspath(os.path.join(base_dir, dst))
        logger.info('chksum in %s' % abs_dest)

        # Don't use abs_path in output as it may expose underlying
        # fs layout.

        relative_dest = abs_dest.replace(base_dir, '')
        if not valid_user_path(configuration, abs_dest, base_dir, True):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "Invalid path! (%s expands to an illegal path)" % dst})
            logger.warning('%s tried to %s restricted path %s !(%s)'
                           % (client_id, op_name, abs_dest, dst))
            return (output_objects, returnvalues.CLIENT_ERROR)
        if not check_write_access(abs_dest, parent_dir=True):
            logger.warning('%s called without write access: %s' %
                           (op_name, abs_dest))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'cannot checksum to "%s": inside a read-only location!' %
                 relative_dest})
            return (output_objects, returnvalues.CLIENT_ERROR)

    all_lines = []
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
            for hash_algo in algo_list:
                try:
                    chksum_helper = _algo_map.get(hash_algo, _algo_map["md5"])
                    checksum = chksum_helper(abs_path, max_chunks=max_chunks)
                    line = "%s %s\n" % (checksum, relative_path)
                    logger.info("%s %s of %s: %s" % (op_name, hash_algo,
                                                     abs_path, checksum))
                    output_lines.append(line)
                except Exception as exc:
                    output_objects.append(
                        {'object_type': 'error_text', 'text':
                         "%s failed on %r" % (op_name, relative_path)})
                    logger.error("%s: failed on '%s': %s" % (op_name,
                                                             relative_path, exc))
                    status = returnvalues.SYSTEM_ERROR
                    continue
            entry = {'object_type': 'file_output',
                     'lines': output_lines}
            output_objects.append(entry)
            all_lines += output_lines

    if dst and not write_file(''.join(all_lines), abs_dest, logger):
        output_objects.append({'object_type': 'error_text',
                               'text': "failed to write checksums to %s" %
                               relative_dest})
        logger.error("writing checksums to %s for %s failed" % (abs_dest,
                                                                client_id))
        status = returnvalues.SYSTEM_ERROR

    return (output_objects, status)
