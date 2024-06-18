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

"""Unit tests for the migrid module pointed to in the filename"""

import codecs
import importlib
import os
import sys
from past.builtins import basestring

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MigTestCase, testmain
from mig.shared.safeinput import \
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


class MigSharedSafeinput(MigTestCase):

    def test_basic_import(self):
        safeimport = importlib.import_module("mig.shared.safeinput")

    def test_existing_main(self):
        safeimport = importlib.import_module("mig.shared.safeinput")
        safeimport.main(_print=lambda _: None)

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
        for test_cn in self.COMMONNAME_PERMITTED:
            saw_raise = False
            try:
                valid_commonname(test_cn)
            except Exception:
                saw_raise = True
            self.assertFalse(saw_raise)

        for test_cn in self.COMMONNAME_PROHIBITED:
            saw_raise = False
            try:
                valid_commonname(test_cn)
            except Exception:
                saw_raise = True
            self.assertTrue(saw_raise)

    def test_commonname_filter(self):
        for test_cn in self.COMMONNAME_PERMITTED:
            test_cn_unicode = as_string_of_unicode(test_cn)
            filtered_cn = filter_commonname(test_cn)
            self.assertEqual(filtered_cn, test_cn_unicode)

        for test_cn in self.COMMONNAME_PROHIBITED:
            test_cn_unicode = as_string_of_unicode(test_cn)
            filtered_cn = filter_commonname(test_cn)
            self.assertNotEqual(filtered_cn, test_cn_unicode)


if __name__ == '__main__':
    testmain()
