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

from collections import namedtuple
from flask import Flask, current_app
import json
import os
import sys
import threading
import time
from wsgiref.simple_server import WSGIRequestHandler


MigCtx = namedtuple('MigCtx', ['configuration'])


def _create_and_expose_server(server, configuration):
    app = Flask('coreapi')

    with app.app_context():
        current_app.migctx = MigCtx(configuration=configuration)

    from .routes import user
    app.register_blueprint(user.bp)

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
