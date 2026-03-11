# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_wsgibin - unit tests of the WSGI glue
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
# --- END_HEADER ---
#

"""Unit tests for the MiG WSGI glue"""

import codecs
import importlib
import os
import stat
import sys
import unittest
from configparser import ConfigParser
from html.parser import HTMLParser

# Imports required for the unit test wrapping
import mig.shared.returnvalues as returnvalues
from mig.shared.base import allow_script, brief_list, client_dir_id, \
    client_id_dir, get_short_id, invisible_path
from mig.shared.compat import SimpleNamespace
# Imports required for the unit tests themselves
from tests.support import MIG_BASE, MigTestCase, ensure_dirs_exist, \
    is_path_within, testmain
from tests.support.snapshotsupp import SnapshotAssertMixin
from tests.support.wsgisupp import WsgiAssertMixin, prepare_wsgi


class DocumentBasicsHtmlParser(HTMLParser):
    """An HTML parser using builtin machinery to check basic html structure."""

    def __init__(self):
        HTMLParser.__init__(self)
        self._doctype = "none"
        self._saw_doctype = False
        self._saw_tags = False
        self._tag_html = "none"

    def handle_decl(self, decl):
        try:
            decltag, decltype = decl.split(" ")
        except Exception:
            decltag = ""
            decltype = ""

        if decltag.upper() == "DOCTYPE":
            self._saw_doctype = True
        else:
            decltype = "unknown"

        self._doctype = decltype

    def handle_starttag(self, tag, attrs):
        if tag == "html":
            if self._saw_tags:
                tag_html = "not_first"
            else:
                tag_html = "was_first"
            self._tag_html = tag_html
        self._saw_tags = True

    def assert_basics(self):
        if not self._saw_doctype:
            raise AssertionError("missing DOCTYPE")

        if self._doctype != "html":
            raise AssertionError("non-html DOCTYPE")

        if self._tag_html == "none":
            raise AssertionError("missing <html>")

        if self._tag_html != "was_first":
            raise AssertionError("first tag seen was not <html>")


class TitleExtractingHtmlParser(DocumentBasicsHtmlParser):
    """An HTML parser using builtin machinery which will extract the title."""

    def __init__(self):
        DocumentBasicsHtmlParser.__init__(self)
        self._title = None
        self._within_title = None

    def handle_data(self, *args, **kwargs):
        if self._within_title:
            self._title = args[0]

    def handle_starttag(self, tag, attrs):
        DocumentBasicsHtmlParser.handle_starttag(self, tag, attrs)

        if tag == "title":
            self._within_title = True

    def handle_endtag(self, tag):
        DocumentBasicsHtmlParser.handle_endtag(self, tag)

        if tag == "title":
            self._within_title = False

    def title(self, trim_newlines=False):
        self.assert_basics()

        if self._title and not self._within_title:
            if trim_newlines:
                return self._title.strip()
            else:
                return self._title
        elif self._within_title:
            raise AssertionError(None, "title end tag missing")
        else:
            raise AssertionError(None, "title was not encountered")


def _import_forcibly(module_name, relative_module_dir=None):
    """Custom import function to allow an import of a file for testing
    that resides within a non-module directory.
    """

    module_path = os.path.join(MIG_BASE, "mig")
    if relative_module_dir is not None:
        module_path = os.path.join(module_path, relative_module_dir)
    sys.path.append(module_path)
    mod = importlib.import_module(module_name)
    sys.path.pop(-1)  # do not leave the forced module path
    return mod


# Imports of the code under test (indirect import needed here)
migwsgi = _import_forcibly("migwsgi", relative_module_dir="wsgi-bin")


class FakeBackend:
    """Object with programmable behaviour that behave like a backend and
    captures details about the calls made to it. It allows the tests to
    assert against known outcomes as well as selectively trigger a wider
    range of codepaths.
    """

    def __init__(self):
        self.output_objects = [
            {"object_type": "start"},
            {"object_type": "title", "text": "ERROR"},
        ]
        self.return_value = returnvalues.ERROR

    def main(self, client_id, user_arguments_dict):
        return self.output_objects, self.return_value

    def set_response(self, output_objects, returnvalue):
        self.output_objects = output_objects
        self.return_value = returnvalue

    def to_import_module(self):
        def _import_module(module_path):
            return self

        return _import_module


class MigWsgibin(MigTestCase, SnapshotAssertMixin, WsgiAssertMixin):
    """WSGI glue test cases"""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self.fake_backend = FakeBackend()
        self.fake_wsgi = prepare_wsgi(self.configuration, "http://localhost/")

        self.application_args = (
            self.fake_wsgi.environ,
            self.fake_wsgi.start_response,
        )
        self.application_kwargs = dict(
            configuration=self.configuration,
            _import_module=self.fake_backend.to_import_module(),
            _set_os_environ=False,
        )

    def assertHtmlTitle(self, value, title_text=None, trim_newlines=False):
        assert title_text is not None

        parser = TitleExtractingHtmlParser()
        parser.feed(value)
        actual_title = parser.title(trim_newlines=trim_newlines)
        self.assertEqual(actual_title, title_text)

    def test_top_level_request_returns_status_ok(self):
        wsgi_result = migwsgi.application(
            *self.application_args, **self.application_kwargs
        )

        self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)

    def test_objects_containing_only_title_has_expected_title(self):
        output_objects = [{"object_type": "title", "text": "TEST"}]
        self.fake_backend.set_response(output_objects, returnvalues.OK)

        wsgi_result = migwsgi.application(
            *self.application_args, **self.application_kwargs
        )

        output, _ = self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)
        self.assertHtmlTitle(output, title_text="TEST", trim_newlines=True)

    def test_objects_containing_only_title_matches_snapshot(self):
        output_objects = [{"object_type": "title", "text": "TEST"}]
        self.fake_backend.set_response(output_objects, returnvalues.OK)

        wsgi_result = migwsgi.application(
            *self.application_args, **self.application_kwargs
        )

        output, _ = self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)
        self.assertSnapshot(output, extension="html")


class MigWsgibin_output_objects(
    MigTestCase, WsgiAssertMixin, SnapshotAssertMixin
):
    """Unit tests for output_object related part of wsgi functions."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self.fake_backend = FakeBackend()
        self.fake_wsgi = prepare_wsgi(self.configuration, "http://localhost/")

        self.application_args = (
            self.fake_wsgi.environ,
            self.fake_wsgi.start_response,
        )
        self.application_kwargs = dict(
            configuration=self.configuration,
            _import_module=self.fake_backend.to_import_module(),
            _set_os_environ=False,
        )

    def assertIsValidHtmlDocument(self, value):
        parser = DocumentBasicsHtmlParser()
        parser.feed(value)
        parser.assert_basics()

    def test_unknown_object_type_generates_valid_error_page(self):
        self.logger.forgive_errors()
        output_objects = [
            {
                "object_type": "nonexistent",  # trigger error handling path
            }
        ]
        self.fake_backend.set_response(output_objects, returnvalues.OK)

        wsgi_result = migwsgi.application(
            *self.application_args, **self.application_kwargs
        )

        output, _ = self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)
        self.assertIsValidHtmlDocument(output)

    def test_objects_with_type_text(self):
        output_objects = [
            # workaround invalid HTML being generated with no title object
            {"object_type": "title", "text": "TEST"},
            {
                "object_type": "text",
                "text": "some text",
            },
        ]
        self.fake_backend.set_response(output_objects, returnvalues.OK)

        wsgi_result = migwsgi.application(
            *self.application_args, **self.application_kwargs
        )

        output, _ = self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)
        self.assertSnapshotOfHtmlContent(output)


class MigWsgibin_input_object(
    MigTestCase, WsgiAssertMixin, SnapshotAssertMixin
):
    """Unit tests for input_object related part of wsgi functions."""

    DUMMY_BYTES = "dummyæøå-ßßß-value".encode("utf-8")

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self.fake_backend = FakeBackend()
        self.fake_wsgi = None

    # TODO: integrate all of this in the default prepare_wsgi?
    def _prepare_test(self, form_overrides=None, custom_env=None):
        """Override common setup with form and environ values as needed"""

        # Set up a wsgi input with non-ascii bytes and open it in binary mode
        # If form_overrides is passed a list of tuples like [('key' 'val')] it
        # produces a fake_wsgi input on the form: b'key=val'
        self.fake_wsgi = prepare_wsgi(
            self.configuration, "http://localhost/", form=form_overrides
        )
        # override the default environ fields from wsgisupp
        if custom_env:
            self.fake_wsgi.environ.update(custom_env)

        self.application_args = (
            self.fake_wsgi.environ,
            self.fake_wsgi.start_response,
        )
        self.application_kwargs = dict(
            configuration=self.configuration,
            _import_module=self.fake_backend.to_import_module(),
            _set_os_environ=False,
        )

    # NOTE: enabled with underlying wsgi use of Fieldstorage fixed
    def test_put_text_plain_with_binary_input_succeeds(self):
        test_form = [("_csrf", self.DUMMY_BYTES)]
        test_env = {
            "REQUEST_METHOD": "PUT",
            "CONTENT_TYPE": "text/plain",
            "CONTENT_LENGTH": "100",
        }
        self._prepare_test(test_form, test_env)

        output_objects = [
            # workaround invalid HTML being generated with no title object
            {"object_type": "title", "text": "TEST"},
            {
                "object_type": "text",
                "text": "some text",
            },
        ]
        self.fake_backend.set_response(output_objects, returnvalues.OK)

        wsgi_result = migwsgi.application(
            *self.application_args, **self.application_kwargs
        )

        # Must succeed with HTTP 200 when it parses input
        output, _ = self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)

    @unittest.skip("disabled with underlying wsgi use of Fieldstorage fixed")
    def test_put_text_plain_with_binary_input_fails(self):
        test_form = [("_csrf", self.DUMMY_BYTES)]
        test_env = {
            "REQUEST_METHOD": "PUT",
            "CONTENT_TYPE": "text/plain",
            "CONTENT_LENGTH": "100",
        }
        self._prepare_test(test_form, test_env)

        output_objects = [
            # workaround invalid HTML being generated with no title object
            {"object_type": "title", "text": "TEST"},
            {
                "object_type": "text",
                "text": "some text",
            },
        ]
        self.fake_backend.set_response(output_objects, returnvalues.OK)

        # TODO: can we add assertLogs to check error log explicitly?
        wsgi_result = migwsgi.application(
            *self.application_args, **self.application_kwargs
        )

        # Must fail with HTTP 500 from failing to parse input
        output, _ = self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 500)

    def test_post_url_encoded_with_binary_input_succeeds(self):
        test_form = [("_csrf", self.DUMMY_BYTES)]
        test_env = None
        self._prepare_test(test_form, test_env)

        output_objects = [
            # workaround invalid HTML being generated with no title object
            {"object_type": "title", "text": "TEST"},
            {
                "object_type": "text",
                "text": "some text",
            },
        ]
        self.fake_backend.set_response(output_objects, returnvalues.OK)

        wsgi_result = migwsgi.application(
            *self.application_args, **self.application_kwargs
        )

        # Must succeed with HTTP 200 when it parses input
        output, _ = self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)


if __name__ == "__main__":
    testmain()
