#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sfping - Seafile server availability checker backend
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Check availability of Seafile server back end"""

from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.functional import validate_input
from mig.shared.init import initialize_main_variables
from mig.shared.url import urlopen


def signature():
    """Signature of the main function"""

    defaults = {'url': ['']}
    return ['seafile_status', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    sf_url = accepted['url'][-1]
    seafile_status = {'object_type': 'seafile_status', 'server': None,
                      'status': None, 'error': "", 'data': ""}
    # IMPORTANT: we only allow ping of configured seafile servers to avoid abuse
    # otherwise the urlopen could be tricked to use e.g. file:/etc/passwd or
    # be used to attack remote sites
    if sf_url in [configuration.user_seahub_url, configuration.user_seareg_url]:
        ping_url = configuration.user_seareg_url
        seafile_status['server'] = ping_url
        try:
            # Never use proxies
            ping_status = urlopen(ping_url, proxies={})
            http_status = ping_status.getcode()
            data = ping_status.read()
            seafile_status['data'] = data
            ping_status.close()
            if http_status == 200:
                # TODO: better parsing
                if "Seafile" in data:
                    seafile_status['status'] = "online"
                else:
                    seafile_status['status'] = "down"
                    seafile_status['error'] = data
            else:
                seafile_status['status'] = "down"
                seafile_status['error'] = "server returned error code %s" % \
                    http_status
        except Exception as exc:
            seafile_status['status'] = "down"
            seafile_status['error'] = "unexpected server response (%s)" % exc
        if seafile_status['status'] == "online":
            logger.info("%s on %s succeeded" % (op_name, sf_url))
        else:
            logger.error("%s against %s returned error: " % (op_name, sf_url)
                         + " %(error)s (%(status)s)" % seafile_status)
    else:
        logger.error("%s against %s is not a valid seafile instance" %
                     (op_name, sf_url))
        seafile_status['server'] = "no such server configured"
        seafile_status['status'] = "unavailable"
        seafile_status['error'] = "Seafile service from %s not enabled" % sf_url
    output_objects.append(seafile_status)
    return (output_objects, returnvalues.OK)
