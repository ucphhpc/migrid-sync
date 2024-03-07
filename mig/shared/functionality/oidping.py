#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# oidping - OpenID 2.0 and Connect server availability checker backend
# Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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

"""Check availability of OpenID 2.0 and Connect server back end"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import force_native_str
from mig.shared.functional import validate_input
from mig.shared.init import initialize_main_variables
from mig.shared.url import urlopen


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
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    oid_url = accepted['url'][-1].strip()
    openid_status = {'object_type': 'openid_status', 'server': None,
                     'status': None, 'error': ""}

    # IMPORTANT: we only allow ping of configured openid servers to avoid abuse
    # otherwise the urlopen could be tricked to use e.g. file:/etc/passwd or
    # be used to attack remote sites
    if not oid_url:
        logger.debug("%s with target URL %r ignored" % (op_name, oid_url))
        openid_status['server'] = oid_url
        openid_status['status'] = "invalid query"
        openid_status['error'] = "please provide a oid ping target URL"
    elif oid_url in configuration.user_openid_providers:
        # TODO: build url from conf
        ping_url = oid_url.replace("/id/", "/ping")
        openid_status['server'] = ping_url
        logger.debug("%s openid server on %s" % (op_name, ping_url))
        try:
            # Never use proxies
            os.environ['no_proxy'] = '*'
            ping_status = urlopen(ping_url)
            http_status = ping_status.getcode()
            # NOTE: we may get utf8 bytes here
            data = force_native_str(ping_status.read())
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
        except Exception as exc:
            openid_status['status'] = "down"
            openid_status['error'] = "unexpected server response (%s)" % exc
        if openid_status['status'] == "online":
            logger.info("%s on %s succeeded" % (op_name, oid_url))
        else:
            logger.error("%s against %s returned error: " % (op_name, oid_url)
                         + " %(error)s (%(status)s)" % openid_status)
    elif oid_url in configuration.user_openidconnect_providers:
        # TODO: build url from conf
        # ping_url = oid_url.replace(
        #    "/oauth/nam/.well-known/openid-configuration", "")
        ping_url = oid_url
        openid_status['server'] = ping_url
        logger.debug("%s openid connect server on %s" % (op_name, ping_url))
        try:
            # Never use proxies
            os.environ['no_proxy'] = '*'
            ping_status = urlopen(ping_url)
            http_status = ping_status.getcode()
            # NOTE: we may get utf8 bytes here
            data = force_native_str(ping_status.read())
            ping_status.close()
            if http_status == 200:
                # TODO: better parsing
                if "authorization_endpoint" in data:
                    openid_status['status'] = "online"
                else:
                    openid_status['status'] = "down"
                    openid_status['error'] = data
            else:
                openid_status['status'] = "down"
                openid_status['error'] = "server returned error code %s" % \
                                         http_status
        except Exception as exc:
            openid_status['status'] = "down"
            openid_status['error'] = "unexpected server response (%s)" % exc
        if openid_status['status'] == "online":
            logger.info("%s on %s succeeded" % (op_name, oid_url))
        else:
            logger.error("%s against %r returned error: " % (op_name, oid_url)
                         + " %(error)s (%(status)s)" % openid_status)
    else:
        logger.error("%s against %r is not a valid openid provider" %
                     (op_name, oid_url))
        openid_status['server'] = "no such server configured"
        openid_status['status'] = "unavailable"
        openid_status['error'] = "OpenID login from %s not enabled" % oid_url
    output_objects.append(openid_status)
    return (output_objects, returnvalues.OK)
