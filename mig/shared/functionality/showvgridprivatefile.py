#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showvgridprivatefile - Access to VGrid private files for owners and members
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

"""Show the requested file located in a given vgrids private_base dir"""

import os

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.parseflags import binary
from shared.validstring import valid_user_path
from shared.vgrid import vgrid_is_owner_or_member


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'file': REJECT_UNSET,
                'flags': ['']}
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
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    vgrid_name = accepted['vgrid_name'][-1]
    filename = accepted['file'][-1]
    flags = ''.join(accepted['flags'])
        
    if not vgrid_is_owner_or_member(vgrid_name, client_id,
                                    configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''You must be an owner or member of %s vgrid to
access the private files.''' % vgrid_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.vgrid_home,
                                            vgrid_name)) + os.sep

    # Strip leading slashes to avoid join() throwing away prefix 

    rel_path = filename.lstrip(os.sep)
    real_path = os.path.abspath(os.path.join(base_dir, rel_path))

    if not valid_user_path(real_path, base_dir, True):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''You are not allowed to use paths outside vgrid
private files dir.'''})
        return (output_objects, returnvalues.CLIENT_ERROR)
    
    try:
        private_fd = open(real_path, 'rb')
        entry = {'object_type': 'file_output',
                 'lines': private_fd.readlines(),
                 'wrap_binary': binary(flags),
                 'wrap_targets': ['lines']}
        output_objects.append(entry)
        private_fd.close()
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error reading VGrid private file (%s)'
                               % exc})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    return (output_objects, returnvalues.OK)
