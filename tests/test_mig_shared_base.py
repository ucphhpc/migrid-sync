# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_base - unit test of the corresponding mig shared module
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

"""Unit test base functions"""

import binascii
import codecs
import os
import sys

from tests.support import PY2, MigTestCase, testmain

from mig.shared.base import force_utf8

DUMMY_STRING = "foo bÆr baz"
DUMMY_UNICODE = u'UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®'


class MigSharedBase(MigTestCase):
    """Unit tests of fucntions within the mig.shared.base module."""

    def test_force_utf8_on_string(self):
        actual = force_utf8(DUMMY_STRING)

        self.assertIsInstance(actual, bytes)
        self.assertEqual(binascii.hexlify(actual), b'666f6f2062c386722062617a')

    def test_force_utf8_on_unicode(self):
        actual = force_utf8(DUMMY_UNICODE)

        self.assertIsInstance(actual, bytes)
        self.assertEqual(actual, codecs.encode(DUMMY_UNICODE, 'utf8'))


if __name__ == '__main__':
    testmain()
