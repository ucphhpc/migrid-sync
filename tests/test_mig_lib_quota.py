# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_quota - unit test of the corresponding mig lib module
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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

# Imports of the code under test
from mig.lib.quota import update_quota

# Imports required for the unit tests themselves
from tests.support import MigTestCase


class MigLibQouta(MigTestCase):
    """Unit tests for quota related helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        pass

    def test_invalid_quota_backend(self):
        """Test invalid quota_backend in configuration"""
        self.configuration.quota_backend = "NEVERNEVER"
        with self.assertLogs(level="ERROR") as log_capture:
            update_quota(self.configuration)
        self.assertTrue(
            "'NEVERNEVER' not in supported_quota_backends:" in msg
            for msg in log_capture.output
        )
