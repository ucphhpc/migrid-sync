#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mig/services/coreapi/server - coreapi service server internals
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


"""HTTP server parts of the coreapi service."""

from __future__ import print_function
from __future__ import absolute_import

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import base64
from collections import defaultdict, namedtuple
from flask import Flask, request, Response
import os
import sys
import threading
import time
import werkzeug.exceptions as httpexceptions
from wsgiref.simple_server import WSGIRequestHandler

from mig.lib.coresvc.payloads import PayloadException, \
    PAYLOAD_POST_USER as _REQUEST_ARGS_POST_USER
from mig.shared.base import canonical_user, keyword_auto, force_native_str_rec
from mig.shared.useradm import fill_user, \
    create_user as useradm_create_user, search_users as useradm_search_users
from mig.shared.userdb import default_db_path


httpexceptions_by_code = {
    exc.code: exc for exc in httpexceptions.__dict__.values() if hasattr(exc, 'code')}


def http_error_from_status_code(http_status_code, http_url, description=None):
    return httpexceptions_by_code[http_status_code](description)


def _create_user(user_dict, conf_path, **kwargs):
    try:
        useradm_create_user(user_dict, conf_path, keyword_auto, **kwargs)
    except Exception as exc:
        return 1
    return 0


def search_users(configuration, search_filter):
    _, hits = useradm_search_users(search_filter, configuration, keyword_auto)
    return list((obj for _, obj in hits))


def _create_and_expose_server(server, configuration):
    app = Flask('coreapi')

    @app.get('/user')
    def GET_user():
        raise http_error_from_status_code(400, None)

    @app.get('/user/<username>')
    def GET_user_username(username):
        return 'FOOBAR'

    @app.get('/user/find')
    def GET_user_find():
        query_params = request.args

        objects = search_users(configuration, {
            'email': query_params['email']
        })

        if len(objects) != 1:
            raise http_error_from_status_code(404, None)

        return dict(objects=objects)

    @app.post('/user')
    def POST_user():
        payload = request.get_json()

        try:
            validated = _REQUEST_ARGS_POST_USER.ensure(payload)
        except PayloadException as vr:
            return http_error_from_status_code(400, None, vr.serialize())

        user_dict = canonical_user(
            configuration, validated, _REQUEST_ARGS_POST_USER._fields)
        fill_user(user_dict)
        force_native_str_rec(user_dict)

        ret = _create_user(user_dict, configuration, default_renew=True)
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
    """TODO: docstring"""

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


def start_service(configuration, host=None, port=None):
    assert host is not None, "required kwarg: host"
    assert port is not None, "required kwarg: port"

    logger = configuration.logger

    def _on_start(server, *args, **kwargs):
        server.server_app = _create_and_expose_server(
            None, server.configuration)

    httpserver = ThreadedApiHttpServer(
        configuration, host=host, port=port, on_start=_on_start)

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
        from mig.shared.conf import get_configuration_object
        # Force no log init since we use separate logger
        configuration = get_configuration_object(skip_log=True)

    logger = configuration.logger

    # Allow e.g. logrotate to force log re-open after rotates
    #register_hangup_handler(configuration)

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
