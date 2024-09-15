#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_openid - openid server authenticating users against user database
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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


"""OpenID server to let users authenticate with username and password from
our local user DB.

Requires OpenID module (https://github.com/openid/python-openid).
"""

from __future__ import print_function
from __future__ import absolute_import

from http.cookies import SimpleCookie, CookieError
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import base64
import cgi
import cgitb
import codecs
from collections import defaultdict, namedtuple
from flask import Flask, request, Response
from functools import partial, update_wrapper
import os
import re
import socket
import sys
import threading
import time
import types
import werkzeug.exceptions as httpexceptions
from wsgiref.simple_server import WSGIRequestHandler

from mig.shared.accountstate import check_account_accessible
from mig.shared.base import canonical_user, client_dir_id, client_id_dir, cert_field_map
from mig.shared.conf import get_configuration_object
from mig.shared.compat import PY2
from mig.shared.griddaemons.openid import default_max_user_hits, \
    default_user_abuse_hits, default_proto_abuse_hits, \
    default_username_validator, refresh_user_creds, update_login_map, \
    login_map_lookup, hit_rate_limit, expire_rate_limit, \
    validate_auth_attempt
from mig.shared.htmlgen import openid_page_template
from mig.shared.logger import daemon_logger, register_hangup_handler
from mig.shared.pwcrypto import make_simple_hash
from mig.shared.safeinput import valid_distinguished_name, valid_password, \
    valid_path, valid_ascii, valid_job_id, valid_base_url, valid_url, \
    valid_complex_url, InputException
from mig.shared.tlsserver import hardened_ssl_context
from mig.shared.url import urlparse, urlencode, parse_qsl
from mig.shared.useradm import get_any_oid_user_dn, check_password_scramble, \
    check_hash
from mig.shared.userdb import default_db_path
from mig.shared.validstring import possible_user_id, is_valid_email_address
from mig.server.createuser import _main as createuser

# Update with extra fields
cert_field_map.update({'role': 'ROLE', 'timezone': 'TZ', 'nickname': 'NICK',
                       'fullname': 'CN', 'o': 'O', 'ou': 'OU'})
cert_field_names = list(cert_field_map)
cert_field_values = list(cert_field_map.values())
cert_field_aliases = {}

# NOTE: response may contain password on the form
# (<Symbol Bare namespace>, 'password'): 'S3cr3tP4ssw0rd'
pw_pattern = "\(<Symbol Bare namespace>, 'password'\): '(.+)'"
pw_regexp = re.compile(pw_pattern)


if PY2:
    from urllib2 import HTTPError
else:
    from urllib.error import HTTPError


if PY2:
    def _ensure_encoded_string(chunk):
        return chunk
else:
    def _ensure_encoded_string(chunk):
        return codecs.encode(chunk, 'utf8')


if PY2:
    from cgi import escape as escape_html
else:
    from html import escape as escape_html


httpexceptions_by_code = {
    exc.code: exc for exc in httpexceptions.__dict__.values() if hasattr(exc, 'code')}


def http_error_from_status_code(http_status_code, http_url, description=None):
    return httpexceptions_by_code[http_status_code](description)


def quoteattr(val):
    """Escape string for safe printing"""
    esc = escape_html(val, 1)
    return '"%s"' % (esc,)


def valid_mode_name(arg):
    """Make sure only valid mode names are allowed"""
    valid_job_id(arg)


def valid_cert_dir(arg):
    """Make sure only valid cert dir names are allowed"""
    valid_distinguished_name(arg, extra_chars='+_')


def valid_cert_fields(arg):
    """Make sure only valid cert field names are allowed"""
    valid_job_id(arg, extra_chars=',')
    if [i for i in arg.split(',') if not i in cert_field_names]:
        invalid_argument(arg)


def valid_identity_url(arg):
    """Make sure only valid url followed by cert dir names are allowed"""
    valid_distinguished_name(arg, extra_chars=':+_')


def valid_session_hash(arg):
    """Make sure only valid session hashes are allowed"""
    valid_password(arg, extra_chars='=', max_length=512)


def invalid_argument(arg):
    """Always raise exception to mark argument invalid"""
    raise ValueError("Unexpected query variable: %s" % quoteattr(arg))


# requests

class ValidationReport(RuntimeError):
    def __init__(self, errors_by_field):
        self.errors_by_field = errors_by_field

    def serialize(self, output_format='text'):
        if output_format == 'json':
            return dict(errors=self.errors_by_field)
        else:
            lines = ["- %s: required %s" % (k, v) for k, v in self.errors_by_field.items()]
            lines.insert(0, '')
            return 'payload failed to validate:%s' % ('\n'.join(lines),)


def _is_not_none(value):
    """value is not None"""
    return value is not None


def _is_string_and_non_empty(value):
    """value is a non-empty string"""
    return isinstance(value, str) and len(value) > 0


_REQUEST_ARGS_POST_USER = namedtuple('PostUserArgs', [
    'full_name',
    'organization',
    'state',
    'country',
    'email',
    'comment',
    'password',
])


_REQUEST_ARGS_POST_USER._validators = defaultdict(lambda: _is_not_none, dict(
    full_name=_is_string_and_non_empty,
    organization=_is_string_and_non_empty,
    state=_is_string_and_non_empty,
    country=_is_string_and_non_empty,
    email=_is_string_and_non_empty,
    comment=_is_string_and_non_empty,
    password=_is_string_and_non_empty,
))

def validate_payload(definition, payload):
    args = definition(*[payload.get(field, None) for field in definition._fields])

    errors_by_field = {}
    for field_name, field_value in args._asdict().items():
        validator_fn = definition._validators[field_name]
        if not validator_fn(field_value):
            errors_by_field[field_name] = validator_fn.__doc__
    if errors_by_field:
        raise ValidationReport(errors_by_field)
    else:
        return args

def _create_and_expose_server(server, configuration):
    app = Flask('coreapi')

    @app.get('/openid/user')
    def GET_user():
        raise http_error_from_status_code(400, None)

    @app.get('/openid/user/<username>')
    def GET_user_username(username):
        return 'FOOBAR'

    @app.post('/openid/user')
    def POST_user():
        payload = request.get_json()

        # unpack the payload to a series of arguments
        try:
            validated = validate_payload(_REQUEST_ARGS_POST_USER, payload)
        except ValidationReport as vr:
            return http_error_from_status_code(400, None, vr.serialize())

        args = list(validated)

        try:

        #     user_dict = canonical_user(configuration, raw_user, raw_user.keys())
        # except (AttributeError, IndexError, KeyError) as e:
        #     raise http_error_from_status_code(400, None)
        # except Exception as e:
        #     pass

        # try:
            createuser(configuration, args)
        except Exception as e:
            pass

        greeting = 'hello client!'
        return Response(greeting, 201)

    return app


class ApiHttpServer(HTTPServer):
    """
    http(s) server that contains a reference to an OpenID Server and
    knows its base URL.
    Extended to fork on requests to avoid one slow or broken login stalling
    the rest.
    """

    min_expire_delay = 120
    last_expire = time.time()
    # NOTE: We do not enable hash and scramble cache here since it is hardly
    #       any gain and it potentially introduces a race
    hash_cache, scramble_cache = None, None

    def __init__(self, configuration, **kwargs):
        self.configuration = configuration
        self.logger = configuration.logger
        self._on_start = kwargs.pop('on_start', lambda _: None)

        address = configuration.daemon_conf['address']
        port = configuration.daemon_conf['port']

        addr = (address, port)
        HTTPServer.__init__(self, addr, ApiHttpRequestHandler, **kwargs)

        fqdn = self.server_name
        port = self.server_port
        # Masquerading if needed
        if configuration.daemon_conf['show_address']:
            fqdn = configuration.daemon_conf['show_address']
        if configuration.daemon_conf['show_port']:
            port = configuration.daemon_conf['show_port']
        if configuration.daemon_conf['nossl']:
            proto = 'http'
            proto_port = 80
        else:
            proto = 'https'
            proto_port = 443
        if port != proto_port:
            self.base_url = '%s://%s:%s/' % (proto, fqdn, port)
        else:
            self.base_url = '%s://%s/' % (proto, fqdn)

        # We serve from sub dir to ease targeted proxying
        self.server_app = None
        self.server_base = 'openid'
        self.base_url += "%s/" % self.server_base
        self.openid = None
        self.approved = {}
        self.lastCheckIDRequest = {}

        # print "DEBUG: sreg fields: %s" % sreg.data_fields
        for name in cert_field_names:
            cert_field_aliases[name] = []
            for target in [i for i in cert_field_names if name != i]:
                if cert_field_map[name] == cert_field_map[target]:
                    cert_field_aliases[name].append(target)

    @property
    def base_environ(self):
        return {}

    def expire_volatile(self):
        """Expire old entries in the volatile helper dictionaries"""
        if self.last_expire + self.min_expire_delay < time.time():
            self.last_expire = time.time()
            expire_rate_limit(self.configuration, "openid",
                              expire_delay=self.min_expire_delay)
            if self.hash_cache:
                self.hash_cache.clear()
            if self.scramble_cache:
                self.scramble_cache.clear()
            self.logger.debug("Expired old rate limits and scramble cache")

    def get_app(self):
        return self.server_app

    def server_activate(self):
        HTTPServer.server_activate(self)
        self._on_start(self)


class ThreadedApiHttpServer(ThreadingMixIn, ApiHttpServer):
    """Multi-threaded version of the ApiHttpServer"""
    pass


class ApiHttpRequestHandler(WSGIRequestHandler):
    """Override BaseHTTPRequestHandler to handle OpenID protocol"""

    # Input validation helper which must hold validators for all valid query
    # string variables. Any other variables must trigger a client error.

    validators = {
        'username': valid_cert_dir,
        'login_as': valid_cert_dir,
        'identifier': valid_cert_dir,
        'user': valid_cert_dir,
        'password': valid_password,
        'yes': valid_ascii,
        'no': valid_ascii,
        'err': valid_ascii,
        'remember': valid_ascii,
        'cancel': valid_ascii,
        'submit': valid_distinguished_name,
        'logout': valid_ascii,
        'success_to': valid_url,
        'fail_to': valid_url,
        'return_to': valid_complex_url,
        'openid.assoc_handle': valid_password,
        'openid.assoc_type': valid_password,
        'openid.dh_consumer_public': valid_session_hash,
        'openid.dh_gen': valid_password,
        'openid.dh_modulus': valid_session_hash,
        'openid.session_type': valid_mode_name,
        'openid.claimed_id': valid_identity_url,
        'openid.identity': valid_identity_url,
        'openid.mode': valid_mode_name,
        'openid.ns': valid_base_url,
        'openid.realm': valid_base_url,
        'openid.success_to': valid_url,
        'openid.return_to': valid_complex_url,
        'openid.trust_root': valid_base_url,
        'openid.ns.sreg': valid_base_url,
        'openid.sreg.required': valid_cert_fields,
        'openid.sreg.optional': valid_ascii,
        'openid.sreg.policy_url': valid_base_url,
    }

    def __init__(self, socket, addr, server, **kwargs):
        self.server = server

        if self.daemon_conf['session_ttl'] > 0:
            self.session_ttl = self.daemon_conf['session_ttl']
        else:
            self.session_ttl = 48 * 3600

        # NOTE: drop idle clients after N seconds to clean stale connections.
        #       Does NOT include clients that connect and do nothing at all :-(
        self.timeout = 120

        self._http_url = None
        self.parsed_uri = None
        self.path_parts = None
        self.retry_url = ''

        WSGIRequestHandler.__init__(self, socket, addr, server, **kwargs)

    @property
    def configuration(self):
        return self.server.configuration

    @property
    def daemon_conf(self):
        return self.server.configuration.daemon_conf

    @property
    def logger(self):
        return self.server.configuration.daemon_conf['logger']


def limited_accept(logger, self, *args, **kwargs):
    """Accepts a new connection from a remote client, and returns a tuple
    containing that new connection wrapped with a server-side SSL channel, and
    the address of the remote client.

    This version extends the default SSLSocket accept handler to only allow the
    client a limited idle period before timing out the connection, to avoid
    blocking legitimate clients.

    It can be tested with something like
    for i in $(seq 1 5); do telnet FQDN PORT & ; done
    curl https://FQDN:PORT/
    which should eventually show the page content.
    """
    newsock, addr = socket.socket.accept(self)
    # NOTE: fetch timeout from kwargs but with fall back to 10s
    #       it must be short since server completely blocks here!
    timeout = kwargs.get('timeout', 10)
    logger.debug("Accept connection from %s with timeout %s" % (addr, timeout))
    newsock.settimeout(timeout)
    newsock = self.context.wrap_socket(newsock,
                                       do_handshake_on_connect=self.do_handshake_on_connect,
                                       suppress_ragged_eofs=self.suppress_ragged_eofs,
                                       server_side=True)
    logger.debug('Done accepting connection.')
    return newsock, addr


def start_service(configuration, host=None, port=None):
    assert host is not None, "required kwarg: host"
    assert port is not None, "required kwarg: port"

    """Service launcher"""
    daemon_conf = configuration.daemon_conf
    logger = configuration.logger

    nossl = daemon_conf['nossl']
    addr = (host, port)
    # TODO: is this threaded version robust enough (thread safety)?
    # OpenIDServer = ApiHttpServer
    httpserver = ThreadedApiHttpServer(configuration, addr)

    # Wrap in SSL if enabled
    if nossl:
        logger.warning('Not wrapping connections in SSL - only for testing!')
    else:
        # Use best possible SSL/TLS args for this python version
        key_path = cert_path = configuration.user_openid_key
        dhparams_path = configuration.user_shared_dhparams
        if not os.path.isfile(cert_path):
            logger.error('No such server key: %s' % cert_path)
            sys.exit(1)
        logger.info('Wrapping connections in SSL')
        ssl_ctx = hardened_ssl_context(configuration, key_path, cert_path,
                                       dhparams_path)
        httpserver.socket = ssl_ctx.wrap_socket(httpserver.socket,
                                                server_side=True)
        # Override default SSLSocket accept function to inject timeout support
        # https://stackoverflow.com/questions/394770/override-a-method-at-instance-level/42154067#42154067

        bound_limited_accept = partial(limited_accept, logger)

        httpserver.socket.accept = types.MethodType(
            bound_limited_accept, httpserver.socket)

    serve_msg = 'Server running at: %s' % httpserver.base_url
    logger.info(serve_msg)
    print(serve_msg)
    while True:
        logger.debug('handle next request')
        httpserver.handle_request()
        logger.debug('done handling request')
        httpserver.expire_volatile()


def _extend_configuration(configuration, address, port, **kwargs):
    configuration.daemon_conf = {
        'address': address,
        'port': port,
        'root_dir': os.path.abspath(configuration.user_home),
        'db_path': os.path.abspath(default_db_path(configuration)),
        'session_store': os.path.abspath(configuration.openid_store),
        'session_ttl': 24 * 3600,
        'allow_password': 'password' in configuration.user_openid_auth,
        'allow_digest': 'digest' in configuration.user_openid_auth,
        'allow_publickey': 'publickey' in configuration.user_openid_auth,
        'user_alias': configuration.user_openid_alias,
        'host_rsa_key': kwargs['host_rsa_key'],
        'users': [],
        'login_map': {},
        'time_stamp': 0,
        'logger': kwargs['logger'],
        'nossl': kwargs['nossl'],
        'expandusername': kwargs['expandusername'],
        'show_address': kwargs['show_address'],
        'show_port': kwargs['show_port'],
        'support_email': configuration.support_email,
        # TODO: Add the following to configuration:
        # max_openid_user_hits
        # max_openid_user_abuse_hits
        # max_openid_proto_abuse_hits
        # max_openid_secret_hits
        'auth_limits':
            {'max_user_hits': default_max_user_hits,
             'user_abuse_hits': default_user_abuse_hits,
             'proto_abuse_hits': default_proto_abuse_hits,
             'max_secret_hits': 1,
             },
    }


def main():
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("openid", configuration.user_openid_log, log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # For masquerading
    show_address = configuration.user_openid_show_address
    show_port = configuration.user_openid_show_port

    # Allow configuration overrides on command line
    nossl = False
    expandusername = False
    if sys.argv[2:]:
        configuration.user_openid_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_openid_port = int(sys.argv[3])
    if sys.argv[4:]:
        nossl = (sys.argv[4].lower() in ('1', 'true', 'yes', 'on'))
    if sys.argv[5:]:
        expandusername = (sys.argv[5].lower() in ('1', 'true', 'yes', 'on'))

    if not configuration.site_enable_openid:
        err_msg = "OpenID service is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)
    print("""
Running grid openid server for user authentication against MiG user DB.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
""")
    print(__doc__)

    default_host_key = """
-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEA404IBMReHOdvhhJ5YtgquY3DNi0v0QwfPUk+EcH/CxFW8UCC
SUJe85up6lEQmOE9yKvrh+3yJgIjdV/ASOw9bd/u0NgNoPwl6A6P8GzHp94vz7UP
nTp+PEUbA8gwqXnzzdeuF3dLDSXuGHdcv8qQEVRBwj/haecO0fgZcfd4fmLDAG53
e/Vwc4lVIp4xx+OQowm9RW3nsAZge1DUoxlStD1/rEzBq1DvVx1Wu8pWS48f2ABH
fHt2Z4ozypMB+a4B56jervcZCNkV/fN2bdGZ8z07hNbn/EkaH2tPw/d62zdHddum
u7Pi0tYwMZz9GN3t18r9qi5ldUJuJNeNvNc7swIBIwKCAQBuZ7rAfKK9lPunhVDm
3gYfnKClSSXakNv5MjQXQPg4k2S+UohsudZZERgEGL7rK5MJspb44Um6sJThPSLh
l1EJe2VeH8wa/iEKUDdI5GD5w7DSmcXBZY3FgKa4sbE8X84wx9g3SJIq9SqA6YTS
LzAIasDasVA6wK9tTJ6lEczPq2VkxkzpKauDMgI6SpaBV+7Un3OM7VJEbWeaJVoZ
9I/2AHfp1hDpIfmaYBCnn2Ky70PBGA8DqAnHUKiid2dfZr8jKLu287LaUHxzIZXz
qSzS6Vg1K0kc5FrgTgrjaXAGNtMenXZdw2/7PMuBDaNuNUApFUlAP5LGvPQ9IRCt
YggDAoGBAP7z3lm74yxrzSa7HRASO2v3vp7jsbaYl4jPCc+6UruBFJlmUUdIQ2fh
8i2S1M5mAvZiJ/PKLQ3r6RXxWZOeh4Vw479HFCVHr5GstSfLolJ5svY8iWEoEGdN
D8aQTQrVAJwAPbLbF4eH5lgSokjOZcWMKsekk4vX2WmCMKWCMms/AoGBAOQ9Fffg
B8TMc1b+jTcj1Py5TiFsxIe3usYjn8Pgg8kpoGfdBoS/TxwoR0MbJdrPgXDKLlLn
A4GG6/7lFmxagCAfUyR2wAsOwAugcaFwS3K4QHGPiv9cgKxt9xhuhhDqXGI2lgAu
oJLcRYBvomPQ+3cGGgifclETTWgkzD5dNVaNAoGBAMStf6RPHPZhyiUxQk4581NK
FrUWDMAPUFOYZqePvCo/AUMjC4AhzZlH5rVxRRRAEOnz8u9EMWKCycB4Wwt6S0mu
25OOmoMorAKpzZO6WKYGHFeNyRBvXRx9Rq8e3FjQM6uLKEglW0tLlG/T3EbLG09A
PkI9IV1AHL8bShlHLjV5AoGBAJyBqKn4tN64FJNsuJrWve8f+w+bCmuxL53PSPtY
H9plr9IxKQqRz9jLKY0Z7hJiZ2NIz07KS4wEvxUvX9VFXyv4OQMPmaEur5LxrQD8
i4HdbgS6M21GvqIfhN2NncJ00aJukr5L29JrKFgSCPP9BDRb9Jgy0gu1duhTv0C0
8V/rAoGAEUheXHIqv9n+3oXLvHadC3aApiz1TcyttDM0AjZoSHpXoBB3AIpPdU8O
0drRG9zJTyU/BC02FvsGAMo0ZpGQRVMuN1Jj7sHsPaUdV38P4G0EaSQJDNxwFKVN
3stfzMDGtKM9lntAsfFQ8n4yvvEbn/quEWad6srf1yxt9B4t5JA=
-----END RSA PRIVATE KEY-----
"""

    try:
        host_key_fd = open(configuration.user_openid_key, 'r')
        host_rsa_key = host_key_fd.read()
        host_key_fd.close()
    except IOError:
        logger.info("No valid host key provided - using default")
        host_rsa_key = default_host_key

    address = configuration.user_openid_address
    port = configuration.user_openid_port
    _extend_configuration(
        configuration,
        address,
        port,
        logger=logger,
        expandusername=False,
        host_rsa_key=host_rsa_key,
        nossl=True,
        show_address=False,
        show_port=False,
    )

    logger.info("Starting OpenID server")
    info_msg = "Listening on address '%s' and port %d" % (address, port)
    logger.info(info_msg)
    print(info_msg)
    try:
        start_service(configuration, host=address, port=port)
    except KeyboardInterrupt:
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print(info_msg)
    info_msg = "Leaving with no more workers active"
    logger.info(info_msg)
    print(info_msg)


if __name__ == '__main__':
    main()
