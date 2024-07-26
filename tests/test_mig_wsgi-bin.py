# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Unit tests for the MiG WSGI glue."""

import codecs
from configparser import ConfigParser
import importlib
import os
import stat
import sys

from tests.support import PY2, MIG_BASE, MigTestCase, testmain, is_path_within
from tests.support.htmlsupp import HtmlAssertMixin
from tests.support.wsgisupp import prepare_wsgi, WsgiAssertMixin
from tests.support.wsgibinsupp import WsgibinInstrumentation, WsgibinAssertMixin

from mig.shared.base import client_id_dir, client_dir_id, get_short_id, \
    invisible_path, allow_script, brief_list
import mig.shared.returnvalues as returnvalues

# workaround for files within non-module directories


def _import_forcibly(module_name, relative_module_dir=None):
    module_path = os.path.join(MIG_BASE, 'mig')
    if relative_module_dir is not None:
        module_path = os.path.join(module_path, relative_module_dir)
    sys.path.append(module_path)
    mod = importlib.import_module(module_name)
    sys.path.pop(-1)  # do not leave the forced module path
    return mod


migwsgi = _import_forcibly('migwsgi', relative_module_dir='wsgi-bin')


def noop(*args):
    pass


class MigWsgibin(MigTestCase, HtmlAssertMixin,
                 WsgiAssertMixin, WsgibinAssertMixin):

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        self.fake_wsgi = prepare_wsgi(self.configuration, 'http://localhost/')
        self.wsgibin_instrumentation = WsgibinInstrumentation()

        self.application_args = (
            self.configuration,
            self.fake_wsgi.environ,
            self.fake_wsgi.start_response,
        )
        self.application_kwargs = dict(
            _wrap_wsgi_errors=noop,
            _format_output=self.wsgibin_instrumentation.format_output,
            _retrieve_handler=self.wsgibin_instrumentation.retrieve_handler,
            _set_environ=noop,
        )

    def test_return_value_ok_returns_status_200(self):
        self.wsgibin_instrumentation.set_response([], returnvalues.OK)

        wsgi_result = migwsgi._application(
            *self.application_args,
            **self.application_kwargs
        )

        self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)
        self.assertWsgibinInstrumentation()

    def test_return_value_ok_returns_valid_html_page(self):
        self.wsgibin_instrumentation.set_response([], returnvalues.OK)

        wsgi_result = migwsgi._application(
            *self.application_args,
            **self.application_kwargs
        )

        output, _ = self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)
        self.assertWsgibinInstrumentation()
        self.assertIsValidHtmlDocument(output)

    def test_return_value_ok_returns_expected_title(self):
        self.wsgibin_instrumentation.set_response([], returnvalues.OK)
        self.wsgibin_instrumentation.format_output.set_values(
            title_text='TEST')

        wsgi_result = migwsgi._application(
            *self.application_args,
            **self.application_kwargs
        )

        output, _ = self.assertWsgiResponse(wsgi_result, self.fake_wsgi, 200)
        self.assertWsgibinInstrumentation()
        self.assertHtmlElementTextContent(
            output, 'title', 'TEST', trim_newlines=True)


if __name__ == '__main__':
    testmain()
