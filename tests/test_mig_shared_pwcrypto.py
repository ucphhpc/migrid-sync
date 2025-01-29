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

"""Unit test pwcrypto functions"""

import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MigTestCase, temppath, testmain

from mig.shared.pwcrypto import *

class MigSharedPwcrypto_make_hash(MigTestCase):
    def test_pickle_string(self):
        expected = "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$epib2rEg/HYTQZFnCp7hmIGZ6rzHnViy"

        actual = make_hash('foobar', _urandom=lambda vlen: b'0' * vlen)

        self.assertEqual(actual, expected, "mismatch pickling string")


if __name__ == '__main__':
    testmain()
