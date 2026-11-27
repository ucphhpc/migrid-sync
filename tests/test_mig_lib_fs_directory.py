#
# --- BEGIN_HEADER ---
#
# test_mig_lib_fs_directory - unit tests of fs directory module
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
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# --- END_HEADER ---
#

"""Unit tests for the migrid module pointed to in the filename"""

import os

from mig.lib import fs
from tests.support import MigTestCase


class TestMkdir(MigTestCase):
    """Unit tests for mkdir."""

    def test_creates_directory_with_default_mode(self) -> None:
        path = os.path.join(self.temppath("mkdir"), "created")

        fs.mkdir(path)
        actual = os.stat(path)

        self.assertEqual(actual.st_mode & 0o777, 0o700)

    def test_creates_directory_with_given_mode(self) -> None:
        path = os.path.join(self.temppath("mkdir"), "created")

        fs.mkdir(path, mode=0o651)
        actual = os.stat(path)

        self.assertEqual(actual.st_mode & 0o777, 0o651)

    def test_raises_file_exists_error_if_directory_exists(self) -> None:
        tmp = self.temppath("mkdir")
        path = os.path.join(tmp, "directory")
        os.mkdir(path)

        with self.assertRaises(FileExistsError):
            fs.mkdir(path)

    def test_raises_file_exists_error_if_file_exists(self) -> None:
        tmp = self.temppath("mkdir")
        path = os.path.join(tmp, "file")
        with open(path, "w") as tmpfile:
            tmpfile.write("content")

        with self.assertRaises(FileExistsError):
            fs.mkdir(path)

    def test_raises_file_not_found_error_parent_directory_does_not_exist(
        self,
    ) -> None:
        tmp = self.temppath("mkdir")
        path = os.path.join(tmp, "nonexisting", "created")

        with self.assertRaises(FileNotFoundError):
            fs.mkdir(path)


class TestMakedirs(MigTestCase):
    """Unit tests for makedirs."""

    def test_creates_directories_with_default_mode(self) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2", "level3")

        fs.makedirs(path)
        stat1 = os.stat(os.path.join(tmp, "level1"))
        stat2 = os.stat(os.path.join(tmp, "level1", "level2"))
        stat3 = os.stat(os.path.join(tmp, "level1", "level2", "level3"))

        self.assertEqual(stat1.st_mode & 0o777, 0o700)
        self.assertEqual(stat2.st_mode & 0o777, 0o700)
        self.assertEqual(stat3.st_mode & 0o777, 0o700)

    def test_creates_directories_with_given_mode(self) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2", "level3")

        fs.makedirs(path, mode=0o751)
        stat1 = os.stat(os.path.join(tmp, "level1"))
        stat2 = os.stat(os.path.join(tmp, "level1", "level2"))
        stat3 = os.stat(os.path.join(tmp, "level1", "level2", "level3"))

        self.assertEqual(stat1.st_mode & 0o777, 0o751)
        self.assertEqual(stat2.st_mode & 0o777, 0o751)
        self.assertEqual(stat3.st_mode & 0o777, 0o751)

    def test_raises_file_exists_error_if_file_exists(self) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "file")
        with open(path, "w") as tmpfile:
            tmpfile.write("content")

        with self.assertRaises(FileExistsError):
            fs.makedirs(path)

    def test_does_not_raise_file_exists_error_if_nonleaf_dir_exists(
        self,
    ) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2")
        os.mkdir(os.path.join(tmp, "level1"))

        fs.makedirs(path)

        self.assertIsNotNone(os.stat(path))

    def test_raises_file_exists_error_if_leaf_dir_exists(self) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2")
        os.makedirs(path)

        with self.assertRaises(FileExistsError):
            fs.makedirs(path)

    def test_does_not_raise_file_exists_error_when_leaf_dir_exists_if_exist_ok(
        self,
    ) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2")
        os.makedirs(path)

        fs.makedirs(path, exist_ok=True)

        self.assertIsNotNone(os.stat(path))
