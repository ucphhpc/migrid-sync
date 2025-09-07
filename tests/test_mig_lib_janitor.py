# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_janitor - unit test of the corresponding mig lib module
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

import time

from tests.support import MigTestCase, FakeConfiguration

from mig.lib.janitor import task_triggers, _lookup_last_run, _update_last_run


class MigLibJanitor(MigTestCase):
    """Unit tests for janitor related helper functions"""

    def test_last_run_bookkeeping(self):
        """Register a last run timestamp and check it"""
        expect = -1
        stamp = _lookup_last_run(self.configuration, 'janitor_task')
        self.assertEqual(stamp, expect)
        expect = 42
        stamp = _update_last_run(self.configuration, 'janitor_task', expect)
        self.assertEqual(stamp, expect)
        expect = time.time()
        stamp = _update_last_run(self.configuration, 'janitor_task', expect)
        self.assertEqual(stamp, expect)
