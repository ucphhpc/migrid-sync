#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showvgridprivatefile - View VGrid private files for owners and members
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Show the requested file located in a given vgrids private_base dir if the
client is an owner or a member of the vgrid. Members are allowed to read private
files but not write them, therefore they don't have a private_base link where
they can access them like owners do.
"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.fileio import read_file, read_file_lines
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.init import initialize_main_variables, find_entry, \
    start_download
from mig.shared.validstring import valid_user_path
from mig.shared.vgrid import vgrid_is_owner_or_member


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'path': REJECT_UNSET}
    return ['file_output', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_title=False, op_header=False,
                                  op_menu=False)
    defaults = signature()[1]
    label = configuration.site_vgrid_label
    # NOTE: no title or header here since output is usually raw
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

    vgrid_name = accepted['vgrid_name'][-1]
    path = accepted['path'][-1]

    if not vgrid_is_owner_or_member(vgrid_name, client_id,
                                    configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''You must be an owner or member of %s %s to
access the private files.''' % (vgrid_name, label)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.vgrid_private_base,
                                            vgrid_name)) + os.sep

    start_entry = find_entry(output_objects, 'start')

    # Strip leading slashes to avoid join() throwing away prefix

    rel_path = path.lstrip(os.sep)
    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
    if not valid_user_path(configuration, abs_path, base_dir, True):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''You are not allowed to use paths outside %s
private files dir.''' % label})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # NOTE: we use a simplified version of the cat.py handling here and simply
    #       return anything but html and txt as downloads.
    if abs_path.endswith('.html') or abs_path.endswith('.txt'):
        force_file = False
        src_mode = "r"
    else:
        force_file = True
        src_mode = "rb"

    output_lines = []
    try:
        if force_file:
            content = read_file(abs_path, logger, mode=src_mode)
            lines = [content]
        else:
            content = lines = read_file_lines(abs_path, logger,
                                              mode=src_mode)
        if content is None:
            raise Exception("could not read file")
        output_lines += lines
    except Exception as exc:
        logger.error("reading private file %s failed: %s" % (abs_path, exc))
        output_objects.append({'object_type': 'error_text', 'text':
                               'Error reading %s private file %s' % (label,
                                                                     path)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    entry = {'object_type': 'file_output',
             'lines': output_lines,
             'wrap_binary': force_file,
             'verbatim': not force_file,
             'wrap_targets': ['lines']}
    # Inject download marker when force_file is set
    if force_file:
        download_marker = start_download(configuration, abs_path,
                                         output_lines)
        start_entry.update(download_marker)
    output_objects.append(entry)
    # Don't append status or timing info
    output_objects.append({'object_type': 'script_status'})
    return (output_objects, returnvalues.OK)
