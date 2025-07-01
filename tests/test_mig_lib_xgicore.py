# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_xgicore - unit test of the corresponding mig lib module
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Unit test xgicore functions"""

import os
import sys

from tests.support import MigTestCase, FakeConfiguration, testmain

from mig.lib.xgicore import *


class MigLibXgicore__get_output_format(MigTestCase):
    """Unit test get_output_format"""

    def test_default_when_missing(self):
        """Test that default output_format is returned when not set."""
        expected = "html"
        user_args = {}
        actual = get_output_format(FakeConfiguration(), user_args,
                                   default_format=expected)
        self.assertEqual(actual, expected,
                         "mismatch in default output_format")

    def test_get_single_requested_format(self):
        """Test that the requested output_format is returned."""
        expected = "file"
        user_args = {'output_format': [expected]}
        actual = get_output_format(FakeConfiguration(), user_args,
                                   default_format='BOGUS')
        self.assertEqual(actual, expected,
                         "mismatch in extracted output_format")

    def test_get_first_requested_format(self):
        """Test that first requested output_format is returned."""
        expected = "file"
        user_args = {'output_format': [expected, 'BOGUS']}
        actual = get_output_format(FakeConfiguration(), user_args,
                                   default_format='BOGUS')
        self.assertEqual(actual, expected,
                         "mismatch in extracted output_format")


class MigLibXgicore__override_output_format(MigTestCase):
    """Unit test override_output_format"""

    def test_unchanged_without_override(self):
        """Test that existing output_format is returned when not overriden."""
        expected = "html"
        user_args = {}
        out_objs = []
        actual = override_output_format(FakeConfiguration(), user_args,
                                        out_objs, expected)
        self.assertEqual(actual, expected,
                         "mismatch in unchanged output_format")

    def test_get_single_requested_format(self):
        """Test that the requested output_format is returned if overriden."""
        expected = "file"
        user_args = {'output_format': [expected]}
        out_objs = [{'object_type': 'start', 'override_format': True}]
        actual = override_output_format(FakeConfiguration(), user_args,
                                        out_objs, 'OVERRIDE')
        self.assertEqual(actual, expected,
                         "mismatch in overriden output_format")

    def test_get_first_requested_format(self):
        """Test that first requested output_format is returned if overriden."""
        expected = "file"
        user_args = {'output_format': [expected, 'BOGUS']}
        actual = get_output_format(FakeConfiguration(), user_args,
                                   default_format='BOGUS')
        self.assertEqual(actual, expected,
                         "mismatch in extracted output_format")


class MigLibXgicore__fill_start_headers(MigTestCase):
    """Unit test fill_start_headers"""

    def test_unchanged_when_set(self):
        """Test that existing valid start entry is returned as-is."""
        out_format = "file"
        headers = [('Content-Type', 'application/octet-stream'),
                   ('Content-Size', 42)]
        expected = {'object_type': 'start', 'headers': headers}
        out_objs = [expected, {'object_type': 'binary', 'data': 42*b'0'}]
        actual = fill_start_headers(FakeConfiguration(), out_objs, out_format)
        self.assertEqual(actual, expected,
                         "mismatch in unchanged start entry")

    def test_headers_added_when_missing(self):
        """Test that start entry headers are added if missing."""
        out_format = "file"
        headers = [('Content-Type', 'application/octet-stream')]
        minimal_start = {'object_type': 'start'}
        expected = {'object_type': 'start', 'headers': headers}
        out_objs = [minimal_start, {'object_type': 'binary', 'data': 42*b'0'}]
        actual = fill_start_headers(FakeConfiguration(), out_objs, out_format)
        self.assertEqual(actual, expected,
                         "mismatch in auto initialized start entry")

    def test_start_added_when_missing(self):
        """Test that start entry is added if missing."""
        out_format = "file"
        headers = [('Content-Type', 'application/octet-stream')]
        expected = {'object_type': 'start', 'headers': headers}
        out_objs = [{'object_type': 'binary', 'data': 42*b'0'}]
        actual = fill_start_headers(FakeConfiguration(), out_objs, out_format)
        self.assertEqual(actual, expected,
                         "mismatch in auto initialized start entry")


if __name__ == '__main__':
    testmain()
