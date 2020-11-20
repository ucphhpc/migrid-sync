#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# du - Show disk use for one or more files
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
from mig.shared.base import client_id_dir, invisible_path
from mig.shared.fileio import walk, write_file, check_write_access
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables
from mig.shared.parseflags import verbose, summarize
from mig.shared.safeinput import valid_path_pattern
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'flags': [''], 'path': REJECT_UNSET, 'dst': [''],
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
            output_objects.append({'object_type': 'text', 'text':
                                   '%s using flag: %s' % (op_name, flag)})

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

        # NOTE: we produce output matching an invocation of:
        # du -aL --apparent-size --block-size=1 PATH [PATH ...]
        filedus = []
        summarize_output = summarize(flags)
        for abs_path in match:
            if invisible_path(abs_path):
                continue
            relative_path = abs_path.replace(base_dir, '')
            # cache accumulated sub dir sizes - du sums into parent dir size
            dir_sizes = {}
            try:
                # Assume a directory to walk
                for (root, dirs, files) in walk(abs_path, topdown=False,
                                                followlinks=True):
                    if invisible_path(root):
                        continue
                    dir_bytes = 0
                    for name in files:
                        real_file = os.path.join(root, name)
                        if invisible_path(real_file):
                            continue
                        relative_file = real_file.replace(base_dir, '')
                        size = os.path.getsize(real_file)
                        dir_bytes += size
                        if not summarize_output:
                            filedus.append({'object_type': 'filedu',
                                            'name': relative_file,
                                            'bytes': size})
                    for name in dirs:
                        real_dir = os.path.join(root, name)
                        if invisible_path(real_dir):
                            continue
                        dir_bytes += dir_sizes[real_dir]
                    relative_root = root.replace(base_dir, '')
                    dir_bytes += os.path.getsize(root)
                    dir_sizes[root] = dir_bytes
                    if root == abs_path or not summarize_output:
                        filedus.append({'object_type': 'filedu',
                                        'name': relative_root,
                                        'bytes': dir_bytes})
                if os.path.isfile(abs_path):
                    # Fall back to plain file where walk is empty
                    size = os.path.getsize(abs_path)
                    filedus.append({'object_type': 'filedu',
                                    'name': relative_path,
                                    'bytes': size})
            except Exception as exc:
                output_objects.append({'object_type': 'error_text',
                                       'text': "%s: '%s': %s" % (op_name,
                                                                 relative_path,
                                                                 exc)})
                logger.error("%s: failed on '%s': %s" % (op_name,
                                                         relative_path, exc))
                status = returnvalues.SYSTEM_ERROR
                continue
        if dst:
            all_lines += ['%(bytes)d\t\t%(name)s' for entry in filedus]
        else:
            output_objects.append(
                {'object_type': 'filedus', 'filedus': filedus})

    if dst and not write_file(''.join(all_lines), abs_dest, logger):
        output_objects.append({'object_type': 'error_text',
                               'text': "failed to write disk use to %s" %
                               relative_dest})
        logger.error("writing disk use to %s for %s failed" % (abs_dest,
                                                               client_id))
        status = returnvalues.SYSTEM_ERROR

    return (output_objects, status)
