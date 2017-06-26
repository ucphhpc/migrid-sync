#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# du - Show disk use for one or more files
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
# NOTE: Use faster scandir if available
try:
    from scandir import walk, __version__ as scandir_version
    if float(scandir_version) < 1.3:
        # Important os.walk compatibility utf8 fixes were not added until 1.3
        raise ImportError("scandir version is too old: fall back to os.walk")
except ImportError:
    from os import walk

import shared.returnvalues as returnvalues
from shared.base import client_id_dir, invisible_path
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.parseflags import verbose, summarize
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'flags': [''], 'path': REJECT_UNSET}
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
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    pattern_list = accepted['path']

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    status = returnvalues.OK

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

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
            except Exception, exc:
                output_objects.append({'object_type': 'error_text',
                        'text': "%s: '%s': %s" % (op_name,
                        relative_path, exc)})
                logger.error("%s: failed on '%s': %s" % (op_name,
                             relative_path, exc))
                status = returnvalues.SYSTEM_ERROR
                continue
        output_objects.append({'object_type': 'filedus', 'filedus': filedus})
    return (output_objects, status)


