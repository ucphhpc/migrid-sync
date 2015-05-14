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

import urllib

import shared.returnvalues as returnvalues
from shared.functional import validate_input
from shared.init import initialize_main_variables

def signature():
    """Signature of the main function"""

    defaults = {'url': ['']}
    return ['openid_status', defaults]

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    oid_url = accepted['url'][-1]
    openid_status = {'object_type': 'openid_status', 'server': None,
                     'status': None, 'error': ""}
    # IMPORTANT: we only allow ping of configured openid servers to avoid abuse
    # otherwise the urlopen could be tricked to use e.g. file:/etc/passwd or
    # be used to attack remote sites
    if oid_url in configuration.user_openid_providers:
        # TODO: build url from conf
        ping_url = oid_url.replace("/id/", "/ping")
        openid_status['server'] = ping_url
        try:
            ping_status = urllib.urlopen(ping_url)
            http_status = ping_status.getcode()
            data = ping_status.read()
            ping_status.close()
            if http_status == 200:
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
        except Exception, exc:
            openid_status['status'] = "down"
            openid_status['error'] = "unexpected server response (%s)" % exc
        if openid_status['status'] == "online":
            logger.info("%s on %s succeeded" % (op_name, oid_url))
        else:
            logger.error("%s against %s returned error: " % (op_name, oid_url) \
                         + " %(error)s (%(status)s)" % openid_status)
    else:
        logger.error("%s against %s is not a valid openid provider" % \
                     (op_name, oid_url))
        openid_status['server'] = "no such server configured"
        openid_status['status'] = "unavailable"
        openid_status['error'] = "OpenID login from %s not enabled" % oid_url
    output_objects.append(openid_status)
    return (output_objects, returnvalues.OK)
