#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# oiddiscover - discover valid openid relying party endpoints for this realm
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
from shared.init import initialize_main_variables

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
    output_objects.append({'object_type': 'header', 'text'
                          : 'OpenID Discovery for %s' % \
                           configuration.short_title})
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    # Force to raw file output unless something else is explicitly requested
    raw_output = False
    if os.environ['QUERY_STRING'].find('output_format') == -1:
        raw_output = True
        user_arguments_dict['output_format'] = ['file']

    discovery_doc = '''<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS
    xmlns:xrds="xri://$xrds"
    xmlns:openid="http://openid.net/xmlns/1.0"
    xmlns="xri://$xrd*($v*2.0)">
    <XRD>
        <Service priority="1">
            <Type>http://specs.openid.net/auth/2.0/return_to</Type>
            %s
        </Service>
    </XRD>
</xrds:XRDS>
'''

    if configuration.site_enable_openid:
        # TMP! add own openid server realm as well
        sid_url = configuration.migserver_https_sid_url
        oid_url = configuration.migserver_https_oid_url
        helper_urls = {
            'migoid_entry_url': os.path.join(sid_url),
            'migoid_signup_url': os.path.join(sid_url, 'cgi-sid', 'signup.py'),
            'migoid_create_url': os.path.join(sid_url, 'wsgi-bin',
                                              'oiddiscover.py'),
            'migoid_dash_url': os.path.join(sid_url, 'wsgi-bin',
                                            'dashboard.py'),
            'migoid_files_url': os.path.join(sid_url, 'wsgi-bin',
                                             'fileman.py'),
            'kitoid_entry_url': os.path.join(oid_url),
            'kitoid_signup_url': os.path.join(oid_url, 'cgi-sid', 'signup.py'),
            'kitoid_create_url': os.path.join(oid_url, 'cgi-sid',
                                              'oiddiscover.py'),
            'kitoid_dash_url': os.path.join(oid_url, 'wsgi-bin',
                                            'dashboard.py'),
            'kitoid_files_url': os.path.join(oid_url, 'wsgi-bin',
                                             'fileman.py')}
        discovery_uris = '''<URI>%(kitoid_entry_url)s</URI>
            <URI>%(kitoid_signup_url)s</URI>
            <URI>%(kitoid_create_url)s</URI>
            <URI>%(kitoid_dash_url)s</URI>
            <URI>%(kitoid_files_url)s</URI>
            <URI>%(migoid_entry_url)s</URI>
            <URI>%(migoid_signup_url)s</URI>
            <URI>%(migoid_create_url)s</URI>
            <URI>%(migoid_dash_url)s</URI>
            <URI>%(migoid_files_url)s</URI>
''' % helper_urls
    else:
        discovery_uris = ''

    output_objects.append({'object_type': 'text', 'text':
                           'Advertising valid OpenID endpoints:'})

    discovery_doc = discovery_doc % discovery_uris
    if raw_output:
        headers = [('Content-Type', 'application/xrds+xml'),
                   ('Content-Disposition', 'attachment; filename=oid.xrds'),
                   ('Content-Length', '%s' % len(discovery_doc))]
        output_objects = [{'object_type': 'start', 'headers': headers}]
        output_objects.append({'object_type': 'binary', 'data': discovery_doc})
        return (output_objects, returnvalues.OK)
    else:
        # output discovery_doc as raw xrds doc in any case
        output_objects.append({'object_type': 'file_output', 'lines':
                               [discovery_doc]})
    return (output_objects, returnvalues.OK)
