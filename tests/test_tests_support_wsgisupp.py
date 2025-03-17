# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_tests_support_wsgisupp - unit test of the corresponding tests module
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

"""Unit tests for the tests module pointed to in the filename"""

import unittest
from mig.shared.compat import SimpleNamespace

from tests.support import AssertOver
from tests.support.wsgisupp import prepare_wsgi


def assert_a_thing(value):
    """A simple assert helper to test with"""
    assert value.endswith(' thing'), "must end with a thing"


class TestsSupportWsgisupp_prepare_wsgi(unittest.TestCase):
    """Coverage of prepare_wsgi helper"""

    def test_prepare_GET(self):
        configuration = SimpleNamespace(
            config_file='/path/to/the/confs/MiGserver.conf'
        )

        environ, _ = prepare_wsgi(configuration, 'http://testhost/some/path')

        self.assertEqual(environ['MIG_CONF'],
                         '/path/to/the/confs/MiGserver.conf')
        self.assertEqual(environ['HTTP_HOST'], 'testhost')
        self.assertEqual(environ['PATH_INFO'], '/some/path')
        self.assertEqual(environ['REQUEST_METHOD'], 'GET')

    def test_prepare_GET_with_query(self):
        test_url = 'http://testhost/some/path'
        configuration = SimpleNamespace(
            config_file='/path/to/the/confs/MiGserver.conf'
        )

        environ, _ = prepare_wsgi(configuration, test_url, query={
            'foo': 'true',
            'bar': 1
        })

        self.assertEqual(environ['QUERY_STRING'], 'foo=true&bar=1')

    def test_prepare_POST(self):
        test_url = 'http://testhost/some/path'
        configuration = SimpleNamespace(
            config_file='/path/to/the/confs/MiGserver.conf'
        )

        environ, _ = prepare_wsgi(configuration, test_url, method='POST')

        self.assertEqual(environ['REQUEST_METHOD'], 'POST')

    def test_prepare_POST_with_headers(self):
        test_url = 'http://testhost/some/path'
        configuration = SimpleNamespace(
            config_file='/path/to/the/confs/MiGserver.conf'
        )

        headers = {
            'Authorization': 'Basic XXXX',
            'Content-Length': 0,
        }
        environ, _ = prepare_wsgi(
            configuration, test_url, method='POST', headers=headers)

        self.assertEqual(environ['CONTENT_LENGTH'], 0)
        self.assertEqual(environ['HTTP_AUTHORIZATION'], 'Basic XXXX')


if __name__ == '__main__':
    unittest.main()
