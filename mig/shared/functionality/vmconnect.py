#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# vmconnect - connect to virtual machine
# Copyright (C) 2003-2012  The MiG Project lead by Brian Vinter
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

"""Virtual machine connection back end functionality"""

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert
from shared import vms


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_title=False)

    status = returnvalues.OK
    defaults = {'job_id': ['']}

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

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Virtual Desktop'})

    password = vms.vnc_jobid(accepted['job_id'][0])

    # Do an "intoN" then map to acsii

    # TODO: Read proxy parameters from configuration

    output_objects.append({'object_type': 'text', 'text'
                          : vms.popup_snippet() + vms.vnc_applet(
        'amigos18.diku.dk',
        8111,
        8114,
        1024,
        768,
        password,
        )})

    return (output_objects, status)


