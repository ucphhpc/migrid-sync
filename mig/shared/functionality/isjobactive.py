#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# isjobactive - Check if sandbox job is still active
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

"""This is a job kill helper for sandboxes"""
from __future__ import absolute_import

import os

from .shared import returnvalues
from .shared.functional import validate_input
from .shared.init import initialize_main_variables
from .shared.resadm import get_sandbox_exe_stop_command


def signature():
    """Signature of the main function"""

    defaults = {'iosessionid': [None], 'sandboxkey': [None],
                'exe_name': [None]}
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

    iosessionid = accepted['iosessionid'][-1]
    sandboxkey = accepted['sandboxkey'][-1]
    exe_name = accepted['exe_name'][-1]

    status = returnvalues.OK

    # Web format for cert access and no header for SID access
    if client_id:
        output_objects.append({'object_type': 'title', 'text'
                               : 'SSS job activity checker'})
        output_objects.append({'object_type': 'header', 'text'
                               : 'SSS job activity checker'})
    else:
        output_objects.append({'object_type': 'start'})

    # check that the job exists, iosessionid is ok (does symlink exist?)

    if iosessionid and os.path.islink(configuration.webserver_home
                                      + iosessionid):
        msg = 'jobactive'
    else:
        if sandboxkey and exe_name:
            (result, msg) = \
                     get_sandbox_exe_stop_command(configuration.sandbox_home,
                                                  sandboxkey, exe_name, logger)
            if result:
                msg = 'stop_command: %s' % msg
        else:
            msg = 'jobinactive'
        status = returnvalues.ERROR

    # Status code line followed by raw output
    if not client_id:
        output_objects.append({'object_type': 'script_status', 'text': ''})
        output_objects.append({'object_type': 'binary', 'data': '%s' % status[0]})
    output_objects.append({'object_type': 'binary', 'data': msg})
    return (output_objects, status)


