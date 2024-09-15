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

    @app.get('/user')
    def GET_user():
        raise http_error_from_status_code(400, None)

    @app.get('/user/<username>')
    def GET_user_username(username):
        return 'FOOBAR'

    @app.post('/user')
    def POST_user():
        payload = request.get_json()

        try:
            validated = validate_payload(_REQUEST_ARGS_POST_USER, payload)
        except ValidationReport as vr:
            return http_error_from_status_code(400, None, vr.serialize())

        args = list(validated)

        ret = createuser(configuration, args)
        if ret != 0:
            raise http_error_from_status_code(400, None)

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

    def __init__(self, configuration, logger=None, host=None, port=None, **kwargs):
        self.configuration = configuration
        self.logger = logger if logger else configuration.logger
        self.server_app = None
        self._on_start = kwargs.pop('on_start', lambda _: None)

        addr = (host, port)
        HTTPServer.__init__(self, addr, ApiHttpRequestHandler, **kwargs)

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

    @property
    def base_url(self):
        proto = 'http'
        return '%s://%s:%d/' % (proto, self.server_name, self.server_port)


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
        return self.server.logger


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

    logger = configuration.logger

    # TODO: is this threaded version robust enough (thread safety)?
    # OpenIDServer = ApiHttpServer
    def _on_start(server, *args, **kwargs):
        server.server_app = _create_and_expose_server(None, server.configuration)
    httpserver = ThreadedApiHttpServer(configuration, host=host, port=port, on_start=_on_start)

    # Wrap in SSL if enabled
    if True:
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


def main(configuration=None):
    if not configuration:
        # Force no log init since we use separate logger
        configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("coreapi", configuration.user_openid_log, log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # FIXME:
    host = 'localhost'  # configuration.user_openid_address
    port = 5555            # configuration.user_openid_port
    server_address = (host, port)

    info_msg = "Starting coreapi..."
    logger.info(info_msg)
    print(info_msg)

    try:
        start_service(configuration, host=host, port=port)
    except KeyboardInterrupt:
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print(info_msg)
    info_msg = "Leaving with no more workers active"
    logger.info(info_msg)
    print(info_msg)
