#
# --- BEGIN_HEADER ---
#
# test_mig_server_reset2fakey - unit tests for twofactor reset script
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

"""Unit tests for twofactor reset script."""

import base64
import os
import unittest

from mig.server.reset2fakey import main
from mig.shared.base import client_id_dir
from mig.shared.defaults import twofactor_filename
from mig.shared.fileio import unpickle
from tests.support import MigTestCase
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin

TEST_SEED = base64.b32encode(b"a" * 20)


class TestMain(MigTestCase, UserAssertMixin):
    """Unit tests for main function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self._provision_test_user(self, TEST_USER_DN)

    def test_enable(self) -> None:
        tmp: str = self.temppath(self.id(), ensure_dir=True)
        seed_path = os.path.join(tmp, "seed.txt")
        with open(seed_path, "wb") as seed_file:
            seed_file.write(TEST_SEED)

        exit_code = main(
            [
                "-i",
                TEST_USER_DN,
                seed_path,
                "100",
            ]
        )

        expected_twofactor_pickle_path = os.path.join(
            self.configuration.user_settings,
            client_id_dir(TEST_USER_DN),
            twofactor_filename,
        )
        data = unpickle(expected_twofactor_pickle_path, logger=None)

        self.assertEqual(exit_code, 0)
        self.assertNotEqual(data, False)
        self.assertEqual(data["CREATOR"], TEST_USER_DN)

    def test_remove(self) -> None:
        tmp: str = self.temppath(self.id(), ensure_dir=True)
        seed_path = os.path.join(tmp, "seed.txt")
        with open(seed_path, "wb") as seed_file:
            seed_file.write(TEST_SEED)

        enable_exit_code = main(
            [
                "-i",
                TEST_USER_DN,
                seed_path,
                "100",
            ]
        )
        self.assertEqual(enable_exit_code, 0)

        remove_exit_code = main(
            [
                "-i",
                TEST_USER_DN,
                "-r",
            ]
        )

        expected_twofactor_pickle_path = os.path.join(
            self.configuration.user_settings,
            client_id_dir(TEST_USER_DN),
            twofactor_filename,
        )
        self.assertEqual(remove_exit_code, 0)
        with self.assertRaises(FileNotFoundError):
            _ = os.stat(expected_twofactor_pickle_path)


if __name__ == "__main__":
    unittest.main()
