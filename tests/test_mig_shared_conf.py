# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_configuration - unit test of configuration
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

"""Unit tests for shared conf"""

import inspect
import os
import unittest

from tests.support import MigTestCase, TEST_DATA_DIR, PY2, testmain
from tests.support.fixturesupp import FixtureAssertMixin

from mig.shared.conf import Configuration, \
                            RuntimeConfiguration, \
                            get_configuration_object


class MigSharedConf(MigTestCase):
    """Coverage of module methods."""

    def test_get_configuration_object_returns_runtime_configuration(self):
        configuration = get_configuration_object(skip_log=True,
                                                 disable_auth_log=True)
        self.assertIsInstance(configuration, RuntimeConfiguration)
        static_configuration = configuration._configuration
        self.assertIsInstance(static_configuration, Configuration)


if __name__ == '__main__':
    testmain()
