# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# wsgisupp - test support library for WSGI
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#

"""Test support library for WSGI."""

import codecs
import importlib
from collections import namedtuple
from io import BytesIO
import json as jsonlib
import os
import sys
from urllib.parse import urlencode, urlparse

from tests.support.suppconst import MIG_BASE

OBJECTS_TYPE = 'objects'


def _import_forcibly(module_name, relative_module_dir=None):
    """Custom import function to allow an import of a file for testing
    that resides within a non-module directory."""

    module_path = os.path.join(MIG_BASE, 'mig')
    if relative_module_dir is not None:
        module_path = os.path.join(module_path, relative_module_dir)
    sys.path.append(module_path)
    mod = importlib.import_module(module_name)
    sys.path.pop(-1)  # do not leave the forced module path
    return mod


migwsgi = _import_forcibly('migwsgi', relative_module_dir='wsgi-bin')


class FakeWsgiStartResponse:
    """Glue object that conforms to the same interface as the start_response()
    in the WSGI specs but records the calls to it such that they can be
    inspected and, for our purposes, asserted against."""

    def __init__(self):
        self.calls = []

    def __call__(self, status, headers, exc=None):
        self.calls.append((status, headers, exc))


def _urlencode_form(form_content):
    """
    Convert a data structure describing form contents to byte string
    that can be directly sent as the body of an HTTP request.
    """

    field_key_and_value_pairs = []
    if isinstance(form_content, dict):
        for key, value in form_content.items():
            if isinstance(value, list):
                for item in value:
                    field_key_and_value_pairs.append((key, item))
                continue
            field_key_and_value_pairs.append((key, value))
    elif isinstance(form_content, list):
        field_key_and_value_pairs = form_content
    else:
        raise AssertionError("invalid form content")
    return urlencode(field_key_and_value_pairs, doseq=True).encode('ascii')


def create_wsgi_environ(configuration, wsgi_url, method=None, query=None, headers=None, form=None, json=None,
        mig_user_dn=None):
    """Populate the necessary variables that will constitute a valid WSGI
    environment given a URL to which we will make a requests under test and
    various other options that set up the nature of that request."""

    parsed_url = urlparse(wsgi_url)

    if query:
        method = "GET"

        request_query = urlencode(query)
        wsgi_input = ()
    elif form:
        method = "POST"
        request_query = ""

        body = _urlencode_form(form)

        headers = headers or {}
        if not "Content-Type" in headers:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Content-Length"] = str(len(body))
        wsgi_input = BytesIO(body)
    elif json:
        headers = headers or {}

        # convert the supplied body into textual bytes for 'transmission'
        if isinstance(json, bytes):
            # use as-is
            pass
        elif isinstance(json, dict):
            body = jsonlib.dumps(json).encode('utf8')
        else:
            raise NotImplementedError()

        method = 'POST'
        request_query = ''

        headers['Content-Type'] = 'application/json'
        headers['Content-Length'] = str(len(body))
        wsgi_input = BytesIO(body)
    else:
        assert method is not None, "method required with no payload specified"
        request_query = parsed_url.query
        wsgi_input = ()

    class _errors:
        """Internal helper to ignore wsgi.errors close method calls"""

        def close(self, *ars, **kwargs):
            """ "Simply ignore"""
            pass

    environ = {}
    environ["wsgi.errors"] = _errors()
    environ["wsgi.input"] = wsgi_input
    environ["wsgi.url_scheme"] = parsed_url.scheme
    environ["wsgi.version"] = (1, 0)
    environ["MIG_CONF"] = configuration.config_file
    environ["HTTP_HOST"] = parsed_url.netloc
    environ["PATH_INFO"] = parsed_url.path
    environ["QUERY_STRING"] = request_query
    environ["REQUEST_METHOD"] = method
    environ["SCRIPT_URI"] = "".join(
        ("http://", environ["HTTP_HOST"], environ["PATH_INFO"])
    )

    if mig_user_dn:
        environ['REMOTE_USER'] = mig_user_dn

    path_parts = parsed_url.path.split('/')
    maybe_script_name = path_parts[-1]
    _, script_ext = os.path.splitext(path_parts[-1])
    if script_ext != '':
        # the script has an extension, so treat it as a functionality file
        environ['SCRIPT_NAME'] = maybe_script_name

    if headers:
        for k, v in headers.items():
            header_key = k.replace("-", "_").upper()
            if header_key.startswith("CONTENT"):
                # Content-* headers must not be prefixed in WSGI
                pass
            else:
                header_key = "HTTP_%s" % (header_key,)
            environ[header_key] = v

    return environ


class _PreparedWsgi:
    """
    Object representing a simulated WSGI request to be exercised by a test case.
    """

    def __init__(self, configuration, url, **kwargs):
        self.configuration = configuration
        self.environ = create_wsgi_environ(configuration, url, **kwargs)
        self.start_response = FakeWsgiStartResponse()

    def __iter__(self):
        return iter((self.environ, self.start_response))

    def _bind_invocation(self):
        self.application_args = (
            self.environ,
            self.start_response,
        )

        self.application_kwargs = dict(
            configuration=self.configuration,
            _set_os_environ=False,
        )

        return migwsgi.application(
            *self.application_args,
            **self.application_kwargs
        )

    @staticmethod
    def trigger_and_unpack_result(wsgi_result):
        chunks = list(wsgi_result)
        assert len(chunks) > 0, "invocation returned no output"
        complete_value = b''.join(chunks)
        decoded_value = codecs.decode(complete_value, 'utf8')
        return decoded_value


def prepare_wsgi(configuration, url, **kwargs):
    if 'method' not in kwargs:
        kwargs['method'] = 'GET'
    return _PreparedWsgi(configuration, url, **kwargs)


class WsgiAssertMixin:
    """Custom assertions for verifying server code executed under test."""

    def prepareWsgiAssert(self, configuration, url, **kwargs):
        return _PreparedWsgi(configuration, url, **kwargs)

    def assertWsgiResponse(self, wsgi_result, prepared_wsgi,
                                        expected_status_code=None,
                                        expected_content_type=None,
                                        content_format=None):
        assert isinstance(prepared_wsgi, _PreparedWsgi)

        if wsgi_result:
            # legacy codepath
            pass
        else:
            wsgi_result = prepared_wsgi._bind_invocation()
        content = _PreparedWsgi.trigger_and_unpack_result(wsgi_result)

        def called_once(fake):
            assert hasattr(fake, "calls")
            return len(fake.calls) == 1

        fake_start_response = prepared_wsgi.start_response

        try:
            self.assertTrue(called_once(fake_start_response))
        except AssertionError:
            if len(fake_start_response.calls) == 0:
                raise AssertionError("WSGI handler did not respond")
            else:
                raise AssertionError("WSGI handler responded more than once")

        wsgi_call = fake_start_response.calls[0]

        if expected_status_code:
            # check for expected HTTP status code
            wsgi_status = wsgi_call[0]
            actual_status_code = int(wsgi_status[0:3])
            self.assertEqual(actual_status_code, expected_status_code)

        headers = dict(wsgi_call[1])

        expecting_json = content_format == 'json'
        if expecting_json and not expected_content_type:
            expected_content_type = 'application/json'

        if expected_content_type:
            actual_content_type = headers.get('Content-Type', 'none/none')
            self.assertEqual(actual_content_type, expected_content_type, "mismatched Content-Type")

        if expecting_json:
            try:
                content = jsonlib.loads(content)
            except jsonlib.decoder.JSONDecodeError:
                raise AssertionError("response did not contain valid JSON")

        return content, headers

    def assertWsgiJsonResponse(self, prepared_wsgi):
        content, _ = self.assertWsgiResponse(None, prepared_wsgi, None, content_format='json')

        assert isinstance(content, list)

        found_objects = [obj for obj in content if obj['object_type'] == OBJECTS_TYPE]
        assert len(found_objects) == 1, "object with type '%s' was not found" % (OBJECTS_TYPE,)
        return found_objects[0][OBJECTS_TYPE]
