# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_tests_support_configsupp - unit test of the corresponding tests module
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

from tests.support import MigTestCase, testmain
from tests.support.configsupp import FakeConfiguration

from mig.shared.configuration import Configuration, \
    _CONFIGURATION_ARGUMENTS, _CONFIGURATION_DEFAULTS, \
    _CONFIGURATION_NOFORWARD_KEYS, _without_noforward_keys


class MigSharedInstall_FakeConfiguration(MigTestCase):
    def test_consistent_parameters(self):
        default_configuration = Configuration(None)
        fake_configuration = FakeConfiguration()

        self.maxDiff = None
        self.assertEqual(
            Configuration.as_dict(default_configuration),
            FakeConfiguration.as_dict(fake_configuration)
        )

    def test_only_configuration_keys(self):
        with self.assertRaises(AssertionError):
            FakeConfiguration(bar='1')


if __name__ == '__main__':
    testmain()
