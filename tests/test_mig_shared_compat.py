# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_fileio - unit test of the corresponding mig shared module
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Unit test compat functions"""

import binascii
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))
from support import MigTestCase, testmain

from mig.shared.compat import \
    ensure_native_string

DUMMY_BYTECHARS = b'DEADBEEF'
DUMMY_BYTESRAW = binascii.unhexlify('DEADBEEF') # 4 bytes

class MigSharedCompat__ensure_native_string(MigTestCase):
    def test_char_bytes_conversion(self):
        actual = ensure_native_string(DUMMY_BYTECHARS)
        self.assertEqual(actual, 'DEADBEEF')

    def test_raw_bytes_conversion(self):
        with self.assertRaises(UnicodeDecodeError):
            ensure_native_string(DUMMY_BYTESRAW)


if __name__ == '__main__':
    testmain()
