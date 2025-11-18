# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_base - unit tests for shared base helpers
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

"""Unit tests for the migrid module pointed to in the filename"""

import base64
import codecs
import sys
from past.builtins import basestring, unicode

from tests.support import MigTestCase, testmain

from mig.shared.safeinput import main as safeinput_main, InputException, \
    filter_commonname, valid_commonname

PY2 = sys.version_info[0] == 2


def as_string_of_unicode(value):
    assert isinstance(value, basestring)
    if not is_string_of_unicode(value):
        assert PY2, "unreachable unless Python 2"
        return unicode(codecs.decode(value, 'utf8'))
    return value


def is_string_of_unicode(value):
    return type(value) == type(u'')


def _hex_wrap(val):
    """Insert a clearly marked hex representation of val"""
    # Please keep aligned with helper in mig/shared/functionality/autocreate.py
    return ".X%s" % base64.b16encode(val.encode('utf8')).decode('utf8')


class TestMigSharedSafeInput(MigTestCase):
    """Test mig.shared.safeinput functions"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return 'testconfig'

    def before_each(self):
        """Setup fake configuration before each test."""
        return

    APOSTROPHE_FULL_NAME = "John O'Connor"
    APOSTROPHE_FULL_NAME_SKIP = "John OConnor"
    APOSTROPHE_FULL_NAME_HEX = "John O.X27Connor"

    COMMONNAME_PERMITTED = (
        'Firstname Lastname',
        'Test Æøå',
        'Test Überh4x0r',
        'Harry S. Truman',
        u'Unicode æøå')

    COMMONNAME_PROHIBITED = (
        "Invalid D'Angelo",
        'Test Maybe Invalid Źacãŕ',
        'Test Invalid ?',
        'Test HTML Invalid <code/>')

    def test_commonname_valid(self):
        """Test commonname_valid with on set of test users"""
        for test_cn in self.COMMONNAME_PERMITTED:
            saw_raise = False
            try:
                valid_commonname(test_cn)
            except InputException:
                saw_raise = True
            self.assertFalse(saw_raise)

        for test_cn in self.COMMONNAME_PROHIBITED:
            saw_raise = False
            try:
                valid_commonname(test_cn)
            except InputException:
                saw_raise = True
            self.assertTrue(saw_raise)

    def test_commonname_filter(self):
        """Test filter_commonname on the set of test users"""
        for test_cn in self.COMMONNAME_PERMITTED:
            test_cn_unicode = as_string_of_unicode(test_cn)
            filtered_cn = filter_commonname(test_cn)
            self.assertEqual(filtered_cn, test_cn_unicode)

        for test_cn in self.COMMONNAME_PROHIBITED:
            test_cn_unicode = as_string_of_unicode(test_cn)
            filtered_cn = filter_commonname(test_cn)
            self.assertNotEqual(filtered_cn, test_cn_unicode)
            self.assertTrue(len(filtered_cn) < len(test_cn_unicode))
            # With default skip all chars in filtered_cn must be in original
            overlap = [i for i in filtered_cn if i in test_cn_unicode]
            self.assertEqual(''.join(overlap), filtered_cn)

    def test_commonname_filter_hexlify_illegal(self):
        """Test filter_commonname on the set of test users with hexlify"""
        for test_cn in self.COMMONNAME_PERMITTED:
            test_cn_unicode = as_string_of_unicode(test_cn)
            filtered_cn = filter_commonname(test_cn, illegal_handler=_hex_wrap)
            # Valid should remain unchanged with hexlify illegal_handler
            self.assertEqual(filtered_cn, test_cn_unicode)

        for test_cn in self.COMMONNAME_PROHIBITED:
            test_cn_unicode = as_string_of_unicode(test_cn)
            filtered_cn = filter_commonname(test_cn, illegal_handler=_hex_wrap)
            # Invalid should be replaced with hexlify illegal_handler
            self.assertNotEqual(filtered_cn, test_cn_unicode)
            self.assertIn('.X', filtered_cn)
            self.assertTrue(len(filtered_cn) > len(test_cn_unicode))

    def test_filter_commonname_apostrophe_name_skip_illegal(self):
        """Test filter_commonname with skip and apostrophe in name"""
        result = filter_commonname(self.APOSTROPHE_FULL_NAME,
                                   illegal_handler=None)
        self.assertNotEqual(result, self.APOSTROPHE_FULL_NAME)
        self.assertNotIn("'", result)
        self.assertEqual(result, self.APOSTROPHE_FULL_NAME_SKIP)

    def test_filter_commonname_apostrophe_name_hexlify_illegal(self):
        """Test filter_commonname with hexlify and apostrophe in name"""
        result = filter_commonname(self.APOSTROPHE_FULL_NAME,
                                   illegal_handler=_hex_wrap)
        self.assertNotEqual(result, self.APOSTROPHE_FULL_NAME)
        self.assertNotIn("'", result)
        self.assertEqual(result, self.APOSTROPHE_FULL_NAME_HEX)


class TestMigSharedBase__legacy(MigTestCase):
    """Run mig.shared.safeinput legacy self-test"""

    # TODO: migrate all legacy self-check functionality into the above?
    def test_existing_main(self):
        """Run built-in self-tests and check output"""
        def raise_on_error_exit(exit_code):
            if exit_code != 0:
                if raise_on_error_exit.last_print is not None:
                    identifying_message = raise_on_error_exit.last_print
                else:
                    identifying_message = 'unknown'
                raise AssertionError(
                    'failure in unittest/testcore: %s' % (identifying_message,))
        raise_on_error_exit.last_print = None

        def record_last_print(value):
            """Keep track of printed output"""
            raise_on_error_exit.last_print = value

        safeinput_main(_exit=raise_on_error_exit, _print=record_last_print)


if __name__ == '__main__':
    testmain()
