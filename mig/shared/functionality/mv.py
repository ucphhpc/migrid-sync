#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mv - [insert a few words of module description on this line]
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

"""Emulate the un*x function with the same name"""

import os
import glob
import shutil

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.parseflags import verbose
from shared.useradm import client_id_dir
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'dst': REJECT_UNSET, 'src': REJECT_UNSET, 'flags': ['']}
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()
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

    flags = ''.join(accepted['flags'])
    src_list = accepted['src']
    dst = accepted['dst'][-1]

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    status = returnvalues.OK

    real_dest = base_dir + dst
    dst_list = glob.glob(real_dest)
    if not dst_list:

        # New destination?

        if not glob.glob(os.path.dirname(real_dest)):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Illegal dst path provided!'})
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
                              : "Warning: You're only allowed to write to your own home directory! dest (%s) expands to an illegal path (%s)"
                               % (dst, relative_dest)})
        logger.error('Warning: %s tried to copy file(s) to destination %s outside own home! (using pattern %s)'
                      % (client_id, real_dest, dst))
        return (output_objects, returnvalues.CLIENT_ERROR)

    for pattern in src_list:
        unfiltered_match = glob.glob(base_dir + pattern)
        match = []
        for server_path in unfiltered_match:
            real_path = os.path.abspath(server_path)
            if not valid_user_path(real_path, base_dir):

                # out of bounds - save user warning for later to allow partial match:
                # ../*/* is technically allowed to match own files.

                logger.error('Warning: %s tried to %s %s outside own home! (%s)'
                              % (client_id, op_name, real_path,
                             pattern))
                continue
            match.append(real_path)

        # Now actually treat list of allowed matchings and notify if no (allowed) match

        if not match:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '%s: no such file or directory! %s'
                                   % (op_name, pattern)})
            status = returnvalues.CLIENT_ERROR

        for real_path in match:
            relative_path = real_path.replace(base_dir, '')
            if verbose(flags):
                if verbose(flags):
                    output_objects.append({'object_type': 'file', 'name'
                            : relative_path})

            # Until recursive is supported src must be a file

            if os.path.isdir(real_path):
                output_objects.append({'object_type': 'warning', 'text'
                        : 'skipping directory src %s!' % relative_path})

            # If destination is a directory the src should be copied there

            if os.path.isdir(real_dest):
                real_dest = real_dest + os.sep\
                     + os.path.basename(real_path)
            try:
                shutil.move(real_path, real_dest)
            except Exception, exc:
                output_objects.append({'object_type': 'error_text',
                        'text': "%s: '%s': %s" % (op_name,
                        relative_path, exc)})
                logger.error("%s: failed on '%s': %s" % (op_name,
                             relative_path, exc))

                status = returnvalues.SYSTEM_ERROR
                continue

    return (output_objects, status)


