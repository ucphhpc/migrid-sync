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
import socket
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

def unescape(esc_str):
    """Remove backslash escapes from a string"""
    try:
        return esc_str.decode('string_escape')
    except:
        return esc_str

def extract_client_cert(configuration, environ):
    """Extract unique user cert ID from SSL cert value in environ.
    NOTE: We must provide the environment as os.environ may be from the time
    of load, which is not the right one for wsgi scripts.
    """

    # We accept utf8 chars (e.g. '\xc3') in client_id_field but they get
    # auto backslash-escaped in environ so we need to unescape first
    
    return unescape(environ.get(client_id_field, '')).strip()

def extract_client_openid(configuration, environ, lookup_dn=True):
    """Extract unique user credentials from REMOTE_USER value in provided 
    environment.
    NOTE: We must provide the environment as os.environ may be from the time
    of load, which is not the right one for wsgi scripts.
    If lookup_dn is set the resulting OpenID is translated to the corresponding
    local account if any.
    """

    # We accept utf8 chars (e.g. '\xc3') in client_login_field but they get
    # auto backslash-escaped in environ so we need to unescape first
    
    login = unescape(environ.get(client_login_field, '')).strip()
    if not login:
        return ""
    if lookup_dn:
        # Let backend do user_check
        login = get_openid_user_dn(configuration, login, user_check=False)
    return login

def extract_client_id(configuration, environ):
    """Extract unique user cert ID from HTTPS or fall back to try REMOTE_USER
    login environment set by OpenID.
    NOTE: We must provide the environment as os.environ may be from the time
    of load, which is not the right one for wsgi scripts.
    """
    distinguished_name = extract_client_cert(configuration, environ)
    if configuration.user_openid_providers and not distinguished_name:
        if environ["REQUEST_URI"].find('oidaccountaction.py') == -1 and \
               environ["REQUEST_URI"].find('oiddiscover.py') == -1:
            # Throw away any extra ID fields from environment
            pop_openid_query_fields(environ)
        distinguished_name = extract_client_openid(configuration, environ)
    return distinguished_name

def check_source_ip(remote_ip, unique_resource_name):
    """Check if remote_ip matches any IP available for the FQDN from
    unique_resource_name"""
    resource_fqdn = '.'.join(unique_resource_name.split('.')[:-1])
    (_, _, resource_ip_list) = socket.gethostbyname_ex(resource_fqdn)
    if not remote_ip in resource_ip_list:
        raise ValueError("Source IP address %s not in resource alias IPs %s" \
                         % (remote_ip, ', '.join(resource_ip_list)))
