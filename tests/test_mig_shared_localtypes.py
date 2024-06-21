# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addheader - add license header to all code modules.
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

"""Unit tests for the shared package of local types."""

from past.builtins import basestring
import codecs
import sys

from tests.support import MigTestCase, testmain

from mig.shared.localtypes import AsciiEnum


PY2 = sys.version_info[0] == 2


def as_string_of_unicode(value):
    assert isinstance(value, basestring)
    if not is_string_of_unicode(value):
        assert PY2, "unreachable unless Python 2"
        return unicode(codecs.decode(value, 'utf8'))
    return value


def is_string_of_unicode(value):
    return type(value) == type(u'')


DUMMY_UNICODE = u'UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®'


class MigSharedLocaltypes__AsciiEnum(MigTestCase):
    def test_defines_the_number_of_cases_specified(self):
        class TheEnum(AsciiEnum):
            SomeCase = 'some case'
            OtherCase = 'other case'
            ZzzCase = 'all the zzz'

        self.assertEqual(len(TheEnum), 3)

    def test_defines_cases_that_behave_as_strings(self):
        class TheEnum(AsciiEnum):
            SomeCase = 'some case'
            OtherCase = 'other case'

        self.assertEqual(TheEnum.SomeCase, 'some case')
        self.assertEqual(TheEnum.OtherCase, 'other case')

    def test_disallows_unicode_keys(self):
        with self.assertRaises(Exception) as cm:
            class TheEnum(AsciiEnum):
                SomeCase = DUMMY_UNICODE

        theexception = cm.exception

        expected_message = "'UniCode123\\\\xc2\\\\xbd\\\\xc2\\\\xbe\\\\xc2\\\\xb5\\\\xc3\\\\x9f\\\\xc3\\\\xb0\\\\xc3\\\\xbe\\\\xc4\\\\x91\\\\xc5\\\\x8b\\\\xc4\\\\xa7\\\\xc4\\\\xb8\\\\xc3\\\\xbe\\\\xc5\\\\x82@\\\\xc2\\\\xaa\\\\xe2\\\\x82\\\\xac\\\\xc2\\\\xa3$\\\\xc2\\\\xa5\\\\xc2\\\\xa9\\\\xc2\\\\xae' is not pure ascii"
        if PY2:
            # repr of unicode strings includes a leading "u" to signify the type
            expected_message = "u" + expected_message
        self.assertEqual(theexception.__str__(), expected_message)


if __name__ == '__main__':
    testmain()
