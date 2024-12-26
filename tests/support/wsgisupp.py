# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# htmlsupp - test support library for WSGI
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

import codecs

from tests.support._env import PY2

if PY2:
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

"""Test support library for WSGI."""


def create_wsgi_environ(configuration, wsgi_url, wsgi_headers=None):
    parsed_url = urlparse(wsgi_url)

    environ = {}
    environ['wsgi.input'] = ()
    environ['wsgi.url_scheme'] = parsed_url.scheme
    environ['MIG_CONF'] = configuration.config_file
    environ['HTTP_HOST'] = parsed_url.netloc
    environ['PATH_INFO'] = parsed_url.path
    environ['QUERY_STRING'] = parsed_url.query
    environ['REQUEST_METHOD'] = 'GET'
    environ['SCRIPT_URI'] = ''.join(('http://', environ['HTTP_HOST'], environ['PATH_INFO']))

    if wsgi_headers:
        for k, v in wsgi_headers.items():
            header_key = "HTTP_%s" % (k.upper(),)
            environ[header_key] = v

    return environ


class FakeStartResponse:
    def __init__(self):
        self.calls = []

    def __call__(self, status, headers, exc=None):
        self.calls.append((status, headers, exc))


def create_wsgi_start_response():
    return FakeStartResponse()


def _trigger_and_unpack_result(wsgi_result):
    chunks = list(wsgi_result)
    assert len(chunks) > 0, "invocation returned no output"
    complete_value = b''.join(chunks)
    decoded_value = codecs.decode(complete_value, 'utf8')
    return decoded_value


class WsgiAssertMixin:
    """Custom assertions for verifying server code executed under test."""

    def assertWsgiResponse(self, wsgi_result, fake_start_response, expected_status_code):
        assert isinstance(fake_start_response, FakeStartResponse)

        content = _trigger_and_unpack_result(wsgi_result)

        def called_once(fake):
            assert hasattr(fake, 'calls')
            return len(fake.calls) == 1

        self.assertTrue(called_once(fake_start_response))
        thecall = fake_start_response.calls[0]
        wsgi_status = thecall[0]
        actual_status_code = int(wsgi_status[0:3])
        self.assertEqual(actual_status_code, expected_status_code)

        return content
