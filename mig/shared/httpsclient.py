#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# httpsclient - Shared functions for all HTTPS clients
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

from mig.shared.base import is_gdp_user, get_xgi_bin, auth_type_description
from mig.shared.defaults import AUTH_CERTIFICATE, AUTH_OPENID_V2, \
    AUTH_OPENID_CONNECT, AUTH_GENERIC, AUTH_NONE, AUTH_MIG_OID, AUTH_EXT_OID, \
    AUTH_MIG_OIDC, AUTH_EXT_OIDC, AUTH_MIG_CERT, AUTH_EXT_CERT, \
    AUTH_SID_GENERIC, AUTH_UNKNOWN, auth_openid_mig_db, auth_openid_ext_db, \
    keyword_all, csrf_field
from mig.shared.gdp.all import get_project_user_dn
from mig.shared.handlers import get_csrf_limit
from mig.shared.pwcrypto import make_csrf_token, make_csrf_trust_token
from mig.shared.settings import load_twofactor
from mig.shared.url import urlencode, parse_qsl, \
    base32urlencode
from mig.shared.useradm import get_oidc_user_dn, get_openid_user_dn

# Generic login clients will have their REMOTE_USER env set to some ID provided
# by the web server authenticator module. In that case look up mapping
# to native user.

generic_id_field = 'REMOTE_USER'

# All HTTPS clients coming through apache will have their unique
# certificate distinguished name available in this field

cert_id_field = 'SSL_CLIENT_S_DN'

# Requests using Session ID as auth should include this field
# NOTE: it is not really used at the moment except to discriminate between SID
#       and unexpected auth methods.

session_id_field = 'SESSION_ID'

# Helper to lookup mandatory twofactor settings matching conf values
twofactor_setting_flavors = {'extoid': 'EXT_OID_TWOFACTOR',
                             'extoidc': 'EXT_OID_TWOFACTOR',
                             'migoid': 'MIG_OID_TWOFACTOR',
                             'migoidc': 'MIG_OID_TWOFACTOR',
                             'sftp': 'SFTP_PASSWORD_TWOFACTOR',
                             'webdavs': 'WEBDAVS_TWOFACTOR',
                             'ftps': 'FTPS_TWOFACTOR'}


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
    """Extract unique user credentials from REMOTE_USER value in provided
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
    _logger.debug('oidc id field: %s' % generic_id_field)
    login = unescape(environ.get(generic_id_field, '')).strip()
    _logger.debug('raw login: %s' % login)
    _logger.debug('configuration.user_mig_oidc_provider: %s'
                  % len(configuration.user_mig_oidc_provider))
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
    # _logger.debug('oidc_db: %s' % oidc_db)
    if lookup_dn:
        # Let backend do user_check
        login = get_oidc_user_dn(configuration, login, user_check=False)

        if configuration.site_enable_gdp:
            # NOTE: some gdp backends require user to be logged in but not that
            #       a project is open. It's handled with skip_client_id_rewrite
            login = get_project_user_dn(
                configuration, environ["REQUEST_URI"], login, 'https')

    return (oidc_db, login)


def extract_plain_login(configuration, environ, id_field=generic_id_field):
    """Extract just the plain login from id_field value in environ"""
    _logger = configuration.logger
    # We accept utf8 chars (e.g. '\xc3') in login field but they get
    # auto backslash-escaped in environ so we need to unescape first
    _logger.debug('extract login field: %s' % id_field)
    login = unescape(environ.get(id_field, '')).strip()
    return login


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

    login = extract_plain_login(configuration, environ)
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


def build_logout_url(configuration, environ):
    """Find associated auth provider logout url and build url to completely
    logout using whatever chaining required.
    """
    _logger = configuration.logger
    (auth_type, auth_flavor) = detect_client_auth(configuration, environ)
    local_logout = '%(SCRIPT_URI)s?logout=true' % environ
    if auth_type == AUTH_OPENID_V2:
        _logger.debug("logout chaining needed for %s auth" % auth_type)
        # NOTE: OpenID 2.0 logout requires local session database scrubbing.
        #       Logout at provider and return to local logout page for that.
        login = extract_plain_login(configuration, environ)
        logout_base = os.path.dirname(os.path.dirname(login))
        logout_query = urlencode({'return_to': local_logout})
        logout_url = logout_base + '/logout?%s' % logout_query
    elif auth_type == AUTH_OPENID_CONNECT:
        _logger.debug("no logout chaining needed for %s auth" % auth_type)
        logout_url = local_logout
    elif auth_type == AUTH_CERTIFICATE:
        _logger.debug("no logout chaining needed for %s auth" % auth_type)
        logout_url = local_logout
    else:
        _logger.warning("unknown logout chaining for %s" % auth_type)
        logout_url = local_logout
    _logger.debug("chain logout url: %s" % logout_url)
    return logout_url


def build_autologout_url(configuration,
                         environ,
                         client_id,
                         return_url,
                         return_query_dict=None,
                         ):
    """Find associated auth provider autologout url and build url to completely
    logout using whatever chaining required.

    OpenID 2.0 logout requires local session database scrubbing.
    That is achieved by first logging out of provider and then
    returning to local logout page.

    OpenID Connect module handles chained logout through vanity url and do not
    have a local session database.
    We still need to cleanup eg. 2FA sessions therefore OpenID Connect
    redirects to local cleanup before logging out of provider
    """
    _logger = configuration.logger
    login = extract_plain_login(configuration, environ)
    logout_base = os.path.dirname(os.path.dirname(login))
    autologout_base = "%s/autologout.py" \
        % os.path.dirname(environ.get('SCRIPT_URI', ''))
    csrf_limit = get_csrf_limit(configuration)
    (auth_type, auth_flavor) = detect_client_auth(configuration, environ)
    if auth_type == AUTH_OPENID_V2:
        # NOTE: OpenID 2.0 goes through provider logout before local cleanup
        # through autologout.
        # Add CSRF trust token to query_dict, needed at autologout.py for URL and
        # query args validation
        if return_query_dict is None:
            csrf_query_dict = {}
        else:
            csrf_query_dict = return_query_dict.copy()
        trust_token = make_csrf_trust_token(configuration, 'get', return_url,
                                            csrf_query_dict, client_id,
                                            csrf_limit)
        csrf_query_dict[csrf_field] = ['%s' % trust_token]
        encoded_redirect_to = base32urlencode(configuration, return_url,
                                              csrf_query_dict)
        local_autologout = '%s?redirect_to=%s' \
            % (autologout_base, encoded_redirect_to)
        autologout_url = os.path.join(logout_base, 'logout?return_to=%s' %
                                      local_autologout)
    elif auth_type == AUTH_OPENID_CONNECT:
        # NOTE: OpenID Connect goes through autologout before provider logout
        logout_url = "%s/dynamic/redirect_uri" % logout_base
        logout_return_url = return_url
        if return_query_dict:
            logout_return_url += "?%s" % urlencode(return_query_dict)
        csrf_query_dict = {}
        csrf_query_dict['logout'] = [logout_return_url]
        trust_token = make_csrf_trust_token(configuration, 'get', logout_url,
                                            csrf_query_dict, client_id,
                                            csrf_limit)
        csrf_query_dict[csrf_field] = [trust_token]
        encoded_redirect_to = base32urlencode(configuration, logout_url,
                                              csrf_query_dict)
        autologout_url = "%s/%s/autologout.py?redirect_to=%s" \
            % (logout_base,
               get_xgi_bin(configuration),
               encoded_redirect_to)
    else:
        _logger.warning("unknown autologout chaining for %s" % auth_type)
        autologout_url = "%s?logout=true" % logout_base
    _logger.debug("chain autologout url: %s" % autologout_url)
    return autologout_url


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
    elif environ.get(generic_id_field, None):
        user_id = environ[generic_id_field]
        # NOTE: OpenID Connect always have ID token claims in env
        # NOTE: OpenID 2.0 lacks specific environment fields but use
        # generic_id_field and the actual ID starts with the authenicating
        # server URL
        if [i for i in environ if i.startswith('OIDC_CLAIM_')]:
            return (AUTH_OPENID_CONNECT, flavor)
        elif user_id.startswith('https://') or user_id.startswith('http://'):
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


def find_auth_type_and_label(configuration, auth_type_name, auth_flavor):
    """Use contents of auth_type_description and auth_flavor to lookup actual
    simple auth_type (migoid, extcert, ...) and corresponding descritpive label
    for that auth_type.
    """
    rev_auth_flavor_map = {AUTH_EXT_OID: 'extoid', AUTH_EXT_OIDC: 'extoidc',
                           AUTH_MIG_OID: 'migoid', AUTH_MIG_OIDC: 'migoidc',
                           AUTH_EXT_CERT: 'extcert', AUTH_MIG_CERT: 'migcert',
                           AUTH_UNKNOWN: 'unknown'}
    auth_type = rev_auth_flavor_map[auth_flavor]
    auth_map = auth_type_description(configuration)
    auth_label = auth_map[auth_type]
    return (auth_type, auth_label)


def require_twofactor_setup(configuration, script_name, client_id, environ):
    """Check if site requires twofactor for this web access and if so return
    the corresponding functionality backend main function.
    """
    _logger = configuration.logger
    if not client_id:
        _logger.debug("not forcing twofactor setup for anonymous user")
        return False
    if configuration.site_enable_gdp \
            and is_gdp_user(configuration, client_id):
        _logger.debug("not forcing twofactor setup for GDP user: %s" %
                      client_id)
        return False
    # Helper to detect twofactor required and protected settings
    twofactor_short_flavors = {AUTH_EXT_OID: 'extoid', AUTH_EXT_OIDC: 'extoidc',
                               AUTH_MIG_OID: 'migoid', AUTH_MIG_OIDC: 'migoidc',
                               AUTH_EXT_CERT: 'extcert', AUTH_MIG_CERT: 'migcert',
                               AUTH_UNKNOWN: 'unknown'}
    twofactor_protos = configuration.site_twofactor_mandatory_protos
    (auth_type, auth_flavor) = detect_client_auth(configuration, environ)
    if keyword_all in twofactor_protos or 'https' in twofactor_protos or \
            twofactor_short_flavors[auth_flavor] in twofactor_protos:
        #_logger.debug("checking %s forced twofactor setup" % client_id)
        saved = load_twofactor(client_id, configuration)
        if not saved:
            _logger.debug(
                "no saved twofactor setup for %s - force" % client_id)
            return True
        if auth_flavor in (AUTH_EXT_OID, AUTH_EXT_OIDC) and \
                not saved.get('EXT_OID_TWOFACTOR', False):
            _logger.debug(
                "missing %s twofactor setup for %s - force" % (auth_flavor,
                                                               client_id))
            return True
        elif auth_flavor in (AUTH_MIG_OIDC, AUTH_MIG_OIDC) and \
                not saved.get('MIG_OID_TWOFACTOR', False):
            _logger.debug(
                "missing %s twofactor setup for %s - force" % (auth_flavor,
                                                               client_id))
            return True
        else:
            _logger.debug(
                "found flavor %s for %s and saved: %s" % (auth_flavor,
                                                          client_id, saved))

        #_logger.debug("required twofactor setup complete for %s" % client_id)

    _logger.debug("not forcing %s to twofactor setup" % client_id)
    return False


def protected_twofactor_settings(configuration, client_id, settings_dict):
    """Return a dictionary of twofactor settings from settings_dict that must
    be preserved because they are already enabled and marked mandatory in the
    configuration.
    """
    _logger = configuration.logger
    twofactor_protos = configuration.site_twofactor_mandatory_protos
    protected = {}
    if not twofactor_protos:
        return protected
    else:
        if keyword_all in twofactor_protos:
            mandatory_protos = list(twofactor_setting_flavors)
        else:
            mandatory_protos = list(twofactor_protos)
        for key in mandatory_protos:
            mandatory_key = twofactor_setting_flavors.get(key, None)
            if not mandatory_key:
                _logger.warning("ignore unknown mandatory twofactor value: %s"
                                % key)
                continue
            val = settings_dict.get(mandatory_key, None)
            if val:
                _logger.debug("protect twofactor %r setting" % key)
                protected[mandatory_key] = val
    _logger.debug("found protected 2FA settings for %s: %s" % (client_id,
                                                               protected))
    return protected


def missing_twofactor_settings(configuration, client_id, settings_dict):
    """Return a dictionary of twofactor settings from settings_dict that must
    be set because they are not yet enabled but marked mandatory in the
    configuration.
    """
    _logger = configuration.logger
    twofactor_protos = configuration.site_twofactor_mandatory_protos
    missing = {}
    if not twofactor_protos \
            or (configuration.site_enable_gdp
                and is_gdp_user(configuration, client_id)):
        return missing
    else:
        if keyword_all in twofactor_protos:
            mandatory_protos = list(twofactor_setting_flavors)
        else:
            mandatory_protos = list(twofactor_protos)
        for key in mandatory_protos:
            mandatory_key = twofactor_setting_flavors.get(key, None)
            if not mandatory_key:
                _logger.warning("ignore unknown mandatory twofactor value: %s"
                                % key)
                continue
            val = settings_dict.get(mandatory_key, None)
            if not val:
                _logger.debug("force missing twofactor %r setting" % key)
                missing[mandatory_key] = True
    _logger.debug("found missing 2FA settings for %s: %s" % (client_id,
                                                             missing))
    return missing


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
    import time
    from mig.shared.conf import get_configuration_object
    conf = get_configuration_object()
    print()
    print("*** DEPRECATION WARNING ***")
    print("Please use dedicated mig/server/genoiddiscovery.py instead of %s!"
          % __file__)
    print()
    time.sleep(30)
    print("""OpenID discovery infomation XML which may be pasted into
state/wwwpublic/oiddiscover.xml if site uses OpenId but doesn't enable the
SID vhost:
""")
    print(generate_openid_discovery_doc(conf))
