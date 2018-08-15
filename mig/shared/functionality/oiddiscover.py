#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# oiddiscover - discover valid openid relying party endpoints for this realm
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Discovery of valid OpenID relying party endpoints for this realm.
The OpenID protocol specifies an optional verification mechanism for the
OpenID provider to verify that an allow request came from a valid relying party
endpoint.
http://openid.net/specs/openid-authentication-2_0.html#rp_discovery

We extract the OpenID setting and reply with a suitable YADIS XRDS document
here if OpenID is enabled.
"""

import os
import tempfile

import shared.returnvalues as returnvalues
from shared.functional import validate_input
from shared.init import initialize_main_variables, find_entry
from shared.httpsclient import generate_openid_discovery_doc


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['file', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    logger = configuration.logger
    logger.info('oiddiscover: %s' % user_arguments_dict)
    output_objects.append({'object_type': 'header', 'text':
                           'OpenID Discovery for %s' %
                           configuration.short_title})
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    # Force to raw file output unless something else is explicitly requested.
    # Relies on delay_format option in run_cgi_script_possibly_with_cert
    if not user_arguments_dict.get('output_format', []):
        user_arguments_dict['output_format'] = ['file']

    discovery_doc = generate_openid_discovery_doc(configuration)
    output_objects.append({'object_type': 'text', 'text':
                           'Advertising valid OpenID endpoints:'})
    # make sure we always have at least one output_format entry
    output_format = user_arguments_dict.get('output_format', []) + ['file']
    if output_format[0] == 'file':
        headers = [('Content-Type', 'application/xrds+xml'),
                   ('Content-Disposition', 'attachment; filename=oid.xrds'),
                   ('Content-Length', '%s' % len(discovery_doc))]
        start_entry = find_entry(output_objects, 'start')
        start_entry['headers'] = headers
        # output discovery_doc as raw xrds doc in any case
        output_objects.append({'object_type': 'file_output', 'lines':
                               [discovery_doc]})
    else:
        output_objects.append({'object_type': 'binary', 'data': discovery_doc})
    return (output_objects, returnvalues.OK)
