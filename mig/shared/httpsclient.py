#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# httpsclient - Shared functions for all HTTPS clients
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

"""Common HTTPS client functions for e.g. access control"""

import os
from urllib import urlencode
from urlparse import parse_qsl

from shared.useradm import get_openid_user_dn

# All HTTPS clients coming through apache will have their unique
# certificate distinguished name available in this field

client_id_field = 'SSL_CLIENT_S_DN'

# Login based clients like OpenID ones will instead have their REMOTE_USER env
# set to some ID provided by the authenticator. In that case look up mapping
# to native user

client_login_field = 'REMOTE_USER'

def pop_openid_query_fields(environ):
    """Extract and remove any additional ID fields from the HTTP query string
    in order to extract OpenID SReg fields and making sure they don't interfere
    with the backend functionality handlers.
    Returns a dictionary with any openid.* fields from the QUERY_STRING
    environment dictionary and removes them from the QUERY_STRING and REQUEST_URI
    input environ dictionary.
    """
    openid_vars = []
    mangled_vars = []
    original_query = environ['QUERY_STRING']
    original_request = environ['REQUEST_URI']
    query_params = parse_qsl(original_query)
    for (key, val) in query_params:
        if key.startswith('openid.'):
            openid_vars.append((key, val))
        else:
            mangled_vars.append((key, val))
    mangled_query = urlencode(mangled_vars)
    mangled_request = original_request.replace(original_query, mangled_query) 
    environ['REQUEST_URI'] = mangled_request
    environ['QUERY_STRING'] = mangled_query
    return openid_vars

def extract_client_id(configuration, environ=os.environ):
    """Extract unique user cert ID from HTTPS or fall back to try REMOTE_USER
    login environment set by OpenID.
    Optionally takes current environment instead of using os.environ from time
    of load.
    """

    distinguished_name = environ.get(client_id_field, '').strip()
    if configuration.user_openid_provider and not distinguished_name:
        login = environ.get(client_login_field, '').strip()
        if not login:
            return ""
        if environ["REQUEST_URI"].find('oidaccountaction.py') == -1 and \
               environ["REQUEST_URI"].find('autocreate.py') == -1:
            # Throw away any extra ID fields from environment
            pop_openid_query_fields(environ)
        distinguished_name = get_openid_user_dn(configuration, login)
    return distinguished_name
