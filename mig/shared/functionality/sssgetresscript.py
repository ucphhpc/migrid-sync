#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sssgetresscript - Load current resource scripts for SSS
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""This is a script download helper for SSS sandboxes"""

import shared.returnvalues as returnvalues
from shared.functional import validate_input, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.sandbox import get_resource_name
from shared.resadm import get_frontend_script, get_master_node_script


def signature():
    """Signature of the main function"""

    defaults = {'action': REJECT_UNSET, 'sandboxkey': REJECT_UNSET,
                'exe_name': ['localhost']}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_title=False,
                                  op_menu=client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    action = accepted['action'][-1]
    sandboxkey = accepted['sandboxkey'][-1]
    exe_name = accepted['exe_name'][-1]

    status = returnvalues.OK

    # Web format for cert access and no header for SID access
    if client_id:
        output_objects.append({'object_type': 'title', 'text'
                               : 'SSS script download'})
        output_objects.append({'object_type': 'header', 'text'
                               : 'SSS script download'})
    else:
        output_objects.append({'object_type': 'start'})

    if not configuration.site_enable_sandboxes:
        output_objects.append({'object_type': 'text', 'text':
                               '''Sandbox resources are disabled on this site.
Please contact the Grid admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    (result, unique_resource_name) = get_resource_name(sandboxkey, logger)
    if not result:
        msg = unique_resource_name
    elif action == 'get_frontend_script':
        (result, msg) = get_frontend_script(unique_resource_name, logger)
    elif action == 'get_master_node_script':
        (result, msg) = get_master_node_script(unique_resource_name,
                                               exe_name, logger)
    else:
        result = False
        msg = 'Unknown action: %s' % action

    if not result:
        status = returnvalues.ERROR

    # Status code line followed by raw output
    if not client_id:
        output_objects.append({'object_type': 'script_status', 'text': ''})
        output_objects.append({'object_type': 'binary', 'data': '%s' % status[0]})
    output_objects.append({'object_type': 'binary', 'data': msg})
    return (output_objects, status)
