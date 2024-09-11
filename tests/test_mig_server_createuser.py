# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_server-createuser - unit tests for the migrid createuser CLI
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

"""Unit tests for the migrid createuser CLI"""

from __future__ import print_function
import os
import sys

from tests.support import MIG_BASE, TEST_OUTPUT_DIR, MigTestCase, testmain

from mig.server.createuser import main as createuser

class TestBooleans(MigTestCase):
    def before_each(self):
        configuration = self.configuration
        test_user_db_home = os.path.join(configuration.state_path, 'user_db_home')
        try:
            os.rmdir(test_user_db_home)
        except:
            pass
        self.expected_user_db_home = test_user_db_home

    def _provide_configuration(self):
        return 'testconfig'

    def test_user_db_is_created_and_user_is_added(self):
        args = [
            "-r",
            "Test User",
            "Test Org",
            "NA",
            "DK",
            "dummy-user",
            "This is the create comment",
            "password"
        ]
        createuser(args, TEST_OUTPUT_DIR, configuration=self.configuration)

        # presence of user home
        path_kind = MigTestCase._absolute_path_kind(self.expected_user_db_home)
        self.assertEqual(path_kind, 'dir')

        # presence of user db
        expected_user_db_file = os.path.join(self.expected_user_db_home, 'MiG-users.db')
        path_kind = MigTestCase._absolute_path_kind(expected_user_db_file)
        self.assertEqual(path_kind, 'file')


if __name__ == '__main__':
    testmain()
