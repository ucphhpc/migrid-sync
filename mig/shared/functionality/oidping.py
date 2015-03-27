#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# oidping - OpenID server availability checker backend
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Check availability of OpenID server back end"""

import os
import urllib

import shared.returnvalues as returnvalues
from shared.functional import validate_input
from shared.init import initialize_main_variables, find_entry

def signature(configuration):
    """Signature of the main function"""

    defaults = {}
    return ['openid_status', defaults]

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature(configuration)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    openid_status = {'object_type': 'openid_status', 'server': None, 'status': None,
                     'error': ""} 
    if configuration.user_openid_providers:
        # TODO: build url from conf
        ping_url = "https://openid.ku.dk/ping"
        openid_status['server'] = ping_url
        ping_status = urllib.urlopen(ping_url)
        http_status = ping_status.getcode()
        if http_status == 200:
            data = ping_status.read()
            ping_status.close()
            # TODO: better parsing
            if "<h1>True</h1>" in data:
                openid_status['status'] = "online"
            else:
                openid_status['status'] = "down"
                openid_status['error'] = data
        else:
                openid_status['status'] = "down"
                openid_status['error'] = "server returned error code %s" % \
                                         http_status
    else:
        openid_status['server'] = 'no server configured'
        openid_status['status'] = "unavailable"
        openid_status['error'] = "OpenID login not enabled"
    output_objects.append(openid_status)
    return (output_objects, returnvalues.OK)
