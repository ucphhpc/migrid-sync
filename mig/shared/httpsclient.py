#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# httpsclient - Shared functions for all HTTPS clients
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

"""Common HTTPS client functions for e.g. access control"""

from __future__ import print_function
from __future__ import absolute_import

import os
import socket

from mig.shared.defaults import AUTH_CERTIFICATE, AUTH_OPENID_V2, \
    AUTH_OPENID_CONNECT, AUTH_GENERIC, AUTH_NONE, AUTH_MIG_OID, AUTH_EXT_OID, \
    AUTH_MIG_OIDC, AUTH_EXT_OIDC, AUTH_MIG_CERT, AUTH_EXT_CERT, \
    AUTH_SID_GENERIC, AUTH_UNKNOWN, auth_openid_mig_db, auth_openid_ext_db
from mig.shared.gdp.all import get_project_user_dn
from mig.shared.url import urlencode, parse_qsl
from mig.shared.useradm import get_oidc_user_dn, get_openid_user_dn

# Generic login clients will have their REMOTE_USER env set to some ID provided
# by the web server authenticator module. In that case look up mapping
# to native user.

generic_id_field = 'REMOTE_USER'

# All HTTPS clients coming through apache will have their unique
# certificate distinguished name available in this field

cert_id_field = 'SSL_CLIENT_S_DN'

# All OpenID Connect authenticated clients will have their unique ID set in
# this ID field. We do support apache mangling of env value to oidc.claim.X
# with the alternate value.

oidc_id_field = 'OIDC_CLAIM_upn'
oidc_id_field_alternate = oidc_id_field.replace('OIDC_CLAIM_', 'oidc.claim.')

# Requests using Session ID as auth should include this field
# NOTE: it is not really used at the moment except to discriminate between SID
#       and unexpected auth methods.

session_id_field = 'SESSION_ID'


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


def extract_base_url(configuration, environ):
    """Extract base URL of requested page from environ"""
    page_url = environ["SCRIPT_URI"]
    parts = page_url.split('/')
    if not parts or not parts[0] in ('http:', 'https:'):
        configuration.logger.error(
            "error in base url extraction from %s" % environ)
        raise ValueError("Invalid request page format: %s" % page_url)
    return '/'.join(parts[:3])


def extract_client_cert(configuration, environ):
    """Extract unique user cert ID from SSL cert value in environ.
    NOTE: We must provide the environment as os.environ may be from the time
    of load, which is not the right one for wsgi scripts.
    """

    # We accept utf8 chars (e.g. '\xc3') in cert_id_field but they get
    # auto backslash-escaped in environ so we need to unescape first

    return unescape(environ.get(cert_id_field, '')).strip()


def extract_client_oidc(configuration, environ, lookup_dn=True):
    """Extract unique user credentials from OIDC_CLAIM_X values in provided
    environment.
    NOTE: We must provide the environment as os.environ may be from the time
    of load, which is not the right one for wsgi scripts.
    If lookup_dn is set the resulting OpenID is translated to the corresponding
    local account if any.
    """
    _logger = configuration.logger
    oidc_db = ""

    # We accept utf8 chars (e.g. '\xc3') in login field but they get
    # auto backslash-escaped in environ so we need to unescape first
    _logger.debug('oidc id field: %s' % oidc_id_field)
    login = unescape(environ.get(oidc_id_field, '')).strip()
    if not login:
        login = unescape(environ.get(oidc_id_field_alternate, '')).strip()
    _logger.debug('raw login: %s' % login)
    # _logger.debug('configuration.user_mig_oidc_provider: %s'
    #              % len(configuration.user_mig_oidc_provider))
    if not login:
        return (oidc_db, "")
    # TODO: do we need session DB here?
    # if configuration.user_mig_oidc_provider and \
    #        login.startswith(configuration.user_mig_oidc_provider):
    #    oidc_db = auth_oidc_mig_db
    # elif configuration.user_ext_oidc_provider and \
    #        login.startswith(configuration.user_ext_oidc_provider):
    #    oidc_db = auth_oidc_ext_db
    # else:
    #    _logger.warning("could not detect openid provider db for %s: %s"
    #                    % (login, environ))
    #_logger.debug('oidc_db: %s' % oidc_db)
    if lookup_dn:
        # Let backend do user_check
        login = get_oidc_user_dn(configuration, login, user_check=False)

        if configuration.site_enable_gdp:
            # NOTE: some gdp backends require user to be logged in but not that
            #       a project is open. It's handled with skip_client_id_rewrite
            login = get_project_user_dn(
                configuration, environ["REQUEST_URI"], login, 'https')

    return (oidc_db, login)


def extract_client_openid(configuration, environ, lookup_dn=True):
    """Extract unique user credentials from REMOTE_USER value in provided
    environment.
    NOTE: We must provide the environment as os.environ may be from the time
    of load, which is not the right one for wsgi scripts.
    If lookup_dn is set the resulting OpenID is translated to the corresponding
    local account if any.
    """
    _logger = configuration.logger
    oid_db = ""

    # We accept utf8 chars (e.g. '\xc3') in login field but they get
    # auto backslash-escaped in environ so we need to unescape first
    _logger.debug('openid login field: %s' % generic_id_field)
    login = unescape(environ.get(generic_id_field, '')).strip()
    _logger.debug('login: %s' % login)
    _logger.debug('configuration.user_mig_oid_provider: %s'
                  % len(configuration.user_mig_oid_provider))
    if not login:
        return (oid_db, "")
    if configuration.user_mig_oid_provider and \
            login.startswith(configuration.user_mig_oid_provider):
        oid_db = auth_openid_mig_db
    elif configuration.user_ext_oid_provider and \
            login.startswith(configuration.user_ext_oid_provider):
        oid_db = auth_openid_ext_db
    else:
        _logger.warning("could not detect openid provider db for %s: %s"
                        % (login, environ))
    _logger.debug('oid_db: %s' % oid_db)
    if lookup_dn:
        # Let backend do user_check
        login = get_openid_user_dn(configuration, login, user_check=False)

        if configuration.site_enable_gdp:
            # NOTE: some gdp backends require user to be logged in but not that
            #       a project is open. It's handled with skip_client_id_rewrite
            login = get_project_user_dn(
                configuration, environ["REQUEST_URI"], login, 'https')

    return (oid_db, login)


def detect_client_auth(configuration, environ):
    """Detect the active client authentication method based on environ"""
    _logger = configuration.logger
    url = extract_base_url(configuration, environ)
    flavor_map = {AUTH_MIG_CERT: configuration.migserver_https_mig_cert_url,
                  AUTH_EXT_CERT: configuration.migserver_https_ext_cert_url,
                  AUTH_MIG_OID: configuration.migserver_https_mig_oid_url,
                  AUTH_EXT_OID: configuration.migserver_https_ext_oid_url,
                  AUTH_MIG_OIDC: configuration.migserver_https_mig_oidc_url,
                  AUTH_EXT_OIDC: configuration.migserver_https_ext_oidc_url,
                  AUTH_SID_GENERIC: configuration.migserver_https_sid_url}
    flavor = AUTH_UNKNOWN
    for (auth_flavor, vhost_base) in flavor_map.items():
        if vhost_base and url.startswith(vhost_base):
            flavor = auth_flavor
            break
    if flavor == AUTH_UNKNOWN:
        _logger.warning("auth flavor is unknown for %s" % url)
    # IMPORTANT: order does matter here because oid is generic REMOTE_USER
    if environ.get(cert_id_field, None):
        return (AUTH_CERTIFICATE, flavor)
    elif environ.get(oidc_id_field, None) or \
            environ.get(oidc_id_field_alternate, None):
        return (AUTH_OPENID_CONNECT, flavor)
    elif environ.get(generic_id_field, None):
        # OpenID 2.0 lacks specific environment fields but use generic_id_field
        # and the actual ID starts with the authenicating server URL
        user_id = environ[generic_id_field]
        if user_id.startswith('https://') or user_id.startswith('http://'):
            return (AUTH_OPENID_V2, flavor)
        elif user_id is not None:
            return (AUTH_GENERIC, flavor)
        else:
            _logger.warning("Generic auth user ID is empty")
    elif flavor == AUTH_SID_GENERIC:
        session_id = environ.get(session_id_field, None)
        if session_id is not None:
            # TODO: verify active session_id here if ever used
            return (AUTH_GENERIC, flavor)
        else:
            # NOTE: SID is never actually used in this particular case
            _logger.debug("No actual Session ID auth found")
            return (AUTH_NONE, flavor)
    else:
        _logger.warning("Unknown or missing client auth method")
    return (AUTH_NONE, flavor)


def extract_client_id(configuration, environ, lookup_dn=True):
    """Extract unique user ID from environment. Supports certificate,
    OpenID Connect or fall back REMOTE_USER login environment set e.g. by
    OpenID 2.0.
    If lookup_dn is set any resulting OpenID is translated to the corresponding
    local account if any.
    NOTE: We must provide the environment as os.environ may be from the time
    of load, which is not the right one for wsgi scripts.
    """
    (auth_type, auth_flavor) = detect_client_auth(configuration, environ)
    if auth_type == AUTH_CERTIFICATE:
        distinguished_name = extract_client_cert(configuration, environ)
    elif auth_type == AUTH_OPENID_CONNECT:
        # if environ["REQUEST_URI"].find('oidcaccountaction.py') == -1 and \
        #        environ["REQUEST_URI"].find('autocreate.py') == -1:
        #    # Throw away any extra ID fields from environment
        #    pop_oidc_query_fields(environ)
        (_, distinguished_name) = extract_client_oidc(configuration, environ,
                                                      lookup_dn)
    elif auth_type == AUTH_OPENID_V2:
        if environ["REQUEST_URI"].find('oidaccountaction.py') == -1 and \
                environ["REQUEST_URI"].find('autocreate.py') == -1:
            # Throw away any extra ID fields from environment
            pop_openid_query_fields(environ)
        (_, distinguished_name) = extract_client_openid(configuration, environ,
                                                        lookup_dn)
    elif auth_type == AUTH_GENERIC:
        distinguished_name = environ.get(generic_id_field, None)
    else:
        # Fall back to use certificate value in any case
        distinguished_name = extract_client_cert(configuration, environ)
    return distinguished_name


def check_source_ip(remote_ip, unique_resource_name, proxy_fqdn=None):
    """Check if remote_ip matches any IP available for the FQDN from
    unique_resource_name or from optional NATed visible address, proxy_fqdn.
    """
    resource_fqdn = '.'.join(unique_resource_name.split('.')[:-1])
    res_ip_list = []
    try:
        (_, _, res_ip_list) = socket.gethostbyname_ex(resource_fqdn)
    except socket.gaierror:
        pass

    proxy_ip_list = []
    if proxy_fqdn:
        try:
            (_, _, proxy_ip_list) = socket.gethostbyname_ex(proxy_fqdn)
        except socket.gaierror:
            pass

    if not remote_ip in res_ip_list + proxy_ip_list:
        raise ValueError("Source IP address %s not in resource alias IPs %s"
                         % (remote_ip, ', '.join(res_ip_list + proxy_ip_list)))


def generate_openid_discovery_doc(configuration):
    """Prepare XML with OpenID discovery information for the OpenID 2.0 relying
    party verification mechanism.
    Returns empty string if no OpenID is enabled and otherwise points to valid
    entry points with OpenID. The set of URLs depend on the availability of
    migoid and extoid provider as well as whether site runs gdp.
    """
    discovery_doc = ''
    if not configuration.user_openid_providers:
        return discovery_doc

    sid_url = configuration.migserver_https_sid_url
    migoid_url = configuration.migserver_https_mig_oid_url
    extoid_url = configuration.migserver_https_ext_oid_url
    cgibin, wsgibin, cgisid = 'cgi-bin', 'wsgi-bin', 'cgi-sid'
    urls = []
    if migoid_url:
        urls.append(migoid_url)
        # NOTE: copy entries to avoid changing menu
        entry_pages = [i for i in configuration.site_default_menu]
        # NOTE: GDP has separate landing page
        if configuration.site_enable_gdp:
            entry_pages.append('gdpman')
        for page in entry_pages:
            urls.append(os.path.join(migoid_url, cgibin, '%s.py' % page))
            if configuration.site_enable_wsgi:
                urls.append(os.path.join(migoid_url, wsgibin, '%s.py' % page))
    if extoid_url:
        urls.append(extoid_url)
        # NOTE: copy entries to avoid changing menu
        entry_pages = [i for i in configuration.site_default_menu]
        # NOTE: autocreate with credentials from external OpenID provider
        if configuration.auto_add_oid_user:
            entry_pages.append('autocreate')
        # NOTE: we let ext users request migoid with authentication and fill
        if migoid_url:
            entry_pages.append('reqoid')
        # NOTE: GDP has separate landing page
        if configuration.site_enable_gdp:
            entry_pages.append('gdpman')
        for page in entry_pages:
            urls.append(os.path.join(extoid_url, cgibin, '%s.py' % page))
            if configuration.site_enable_wsgi:
                urls.append(os.path.join(extoid_url, wsgibin, '%s.py' % page))
    if sid_url:
        entry_pages = ['signup', 'login']
        # NOTE: we reuse cert req to create migoid account for now
        entry_pages.append('reqcert')
        for page in entry_pages:
            urls.append(os.path.join(sid_url, cgisid, '%s.py' % page))

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
''' % '\n'.join(['            <URI>%s</URI>' % i for i in urls])
    return discovery_doc


if __name__ == "__main__":
    from mig.shared.conf import get_configuration_object
    conf = get_configuration_object()
    print("""OpenID discovery infomation XML which may be pasted into
state/wwwpublic/oiddiscover.xml if site uses OpenId but doesn't enable the
SID vhost:
""")
    print(generate_openid_discovery_doc(conf))
