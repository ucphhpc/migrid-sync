# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_serial - unit test of the corresponding mig shared module
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

"""Unit test serial functions"""

import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MigTestCase, temppath, testmain
from mig.shared.serial import *

class BasicSerial(MigTestCase):
    BASIC_OBJECT = {'abc': 123, 'def': 'def', 'ghi': 42.0, 'accented': 'TéstÆøå'}

    def test_pickle_string(self):
        orig = BasicSerial.BASIC_OBJECT
        data = loads(dumps(orig))
        self.assertEqual(data, orig, "mismatch pickling string")

    def test_pickle_file(self):
        tmp_path = temppath("dummyserial.tmp", self)
        orig = BasicSerial.BASIC_OBJECT
        dump(orig, tmp_path)
        data = load(tmp_path)
        self.assertEqual(data, orig, "mismatch pickling string")

if __name__ == '__main__':
    testmain()
