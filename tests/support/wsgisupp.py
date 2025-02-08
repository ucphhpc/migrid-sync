# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# wsgisupp - test support library for WSGI
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

"""Test support library for WSGI."""

from collections import namedtuple
import codecs
from io import BytesIO
from werkzeug.datastructures import MultiDict

from tests.support._env import PY2

if PY2:
    from urllib import urlencode
    from urlparse import urlparse
else:
    from urllib.parse import urlencode, urlparse


# named type representing the tuple that is passed to WSGI handlers
_PreparedWsgi = namedtuple('_PreparedWsgi', ['environ', 'start_response'])


class FakeWsgiStartResponse:
    """Glue object that conforms to the same interface as the start_response()
       in the WSGI specs but records the calls to it such that they can be
       inspected and, for our purposes, asserted against."""

    def __init__(self):
        self.calls = []

    def __call__(self, status, headers, exc=None):
        self.calls.append((status, headers, exc))


def create_wsgi_environ(configuration, wsgi_url, method='GET', query=None, headers=None, form=None):
    """Populate the necessary variables that will constitute a valid WSGI
    environment given a URL to which we will make a requests under test and
    various other options that set up the nature of that request."""

    parsed_url = urlparse(wsgi_url)

    if query:
        method = 'GET'

        request_query = urlencode(query)
        wsgi_input = ()
    elif form:
        method = 'POST'
        request_query = ''

        body = urlencode(MultiDict(form)).encode('ascii')

        headers = headers or {}
        if not 'Content-Type' in headers:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        headers['Content-Length'] = str(len(body))
        wsgi_input = BytesIO(body)
    else:
        request_query = parsed_url.query
        wsgi_input = ()

    class _errors:
        def close():
            pass

    environ = {}
    environ['wsgi.errors'] = _errors()
    environ['wsgi.input'] = wsgi_input
    environ['wsgi.url_scheme'] = parsed_url.scheme
    environ['wsgi.version'] = (1, 0)
    environ['MIG_CONF'] = configuration.config_file
    environ['HTTP_HOST'] = parsed_url.netloc
    environ['PATH_INFO'] = parsed_url.path
    environ['QUERY_STRING'] = request_query
    environ['REQUEST_METHOD'] = method
    environ['SCRIPT_URI'] = ''.join(
        ('http://', environ['HTTP_HOST'], environ['PATH_INFO']))

    if headers:
        for k, v in headers.items():
            header_key = k.replace('-', '_').upper()
            if header_key.startswith('CONTENT'):
                # Content-* headers must not be prefixed in WSGI
                pass
            else:
                header_key = "HTTP_%s" % (header_key),
            environ[header_key] = v

    return environ


def create_wsgi_start_response():
    return FakeWsgiStartResponse()


def prepare_wsgi(configuration, url, **kwargs):
    return _PreparedWsgi(
        create_wsgi_environ(configuration, url, **kwargs),
        create_wsgi_start_response()
    )


def _trigger_and_unpack_result(wsgi_result):
    chunks = list(wsgi_result)
    assert len(chunks) > 0, "invocation returned no output"
    complete_value = b''.join(chunks)
    decoded_value = codecs.decode(complete_value, 'utf8')
    return decoded_value


class WsgiAssertMixin:
    """Custom assertions for verifying server code executed under test."""

    def assertWsgiResponse(self, wsgi_result, fake_wsgi, expected_status_code):
        assert isinstance(fake_wsgi, _PreparedWsgi)

        content = _trigger_and_unpack_result(wsgi_result)

        def called_once(fake):
            assert hasattr(fake, 'calls')
            return len(fake.calls) == 1

        fake_start_response = fake_wsgi.start_response

        try:
            self.assertTrue(called_once(fake_start_response))
        except AssertionError:
            if len(fake_start_response.calls) == 0:
                raise AssertionError("WSGI handler did not respond")
            else:
                raise AssertionError("WSGI handler responded more than once")

        wsgi_call = fake_start_response.calls[0]

        # check for expected HTTP status code
        wsgi_status = wsgi_call[0]
        actual_status_code = int(wsgi_status[0:3])
        self.assertEqual(actual_status_code, expected_status_code)

        headers = dict(wsgi_call[1])

        return content, headers
