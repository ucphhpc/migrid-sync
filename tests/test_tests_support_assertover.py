# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_tests_support_assertover - unit test of the corresponding tests module
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

from tests.support import AssertOver
from tests.support.assertover import NoBlockError, NoCasesError


def assert_a_thing(value):
    """A simple assert helper to test with"""
    assert value.endswith(' thing'), "must end with a thing"


class TestsSupportAssertOver(unittest.TestCase):
    """Coverage of AssertOver helper"""

    def test_none_failing(self):
        saw_raise = False
        try:
            with AssertOver(values=('some thing', 'other thing')) as value_block:
                value_block(lambda _: assert_a_thing(_))
        except Exception as exc:
            saw_raise = True
        self.assertFalse(saw_raise)

    def test_three_total_two_failing(self):
        with self.assertRaises(AssertionError) as raised:
            with AssertOver(values=('some thing', 'other stuff', 'foobar')) as value_block:
                value_block(lambda _: assert_a_thing(_))

        theexception = raised.exception
        self.assertEqual(str(theexception), """assertions raised for the following values:
- <'other stuff'> : must end with a thing
- <'foobar'> : must end with a thing""")

    def test_no_cases(self):
        with self.assertRaises(AssertionError) as raised:
            with AssertOver(values=()) as value_block:
                value_block(lambda _: assert_a_thing(_))

        theexception = raised.exception
        self.assertIsInstance(theexception, NoCasesError)


if __name__ == '__main__':
    unittest.main()
