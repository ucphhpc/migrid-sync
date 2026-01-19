# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_filemarks - unit tests for shared filemarks helpers
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
# -- END_HEADER ---
#

"""Unit tests for mig.shared.filemarks module"""

import os
import shutil
import stat
import tempfile
import time
import unittest

from mig.shared.filemarks import update_filemark, get_filemark, reset_filemark
from tests.support import ensure_dirs_exist, MigTestCase, testmain

TEST_MARKS_DIR = 'TestMarks'
TEST_MARKS_FILE = 'file.mark'


class TestMigSharedFilemarks(MigTestCase):
    """Test mig.shared.filemarks functions"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return 'testconfig'

    def _prepare_mark_for_test(self, mark_name=None, timestamp=None):
        """Prepare test for mark_name with timestamp in default location"""
        if mark_name is None:
            mark_name = TEST_MARKS_FILE
        if timestamp is None:
            timestamp = time.time()
        self.marks_path = os.path.join(self.marks_base, mark_name)
        open(self.marks_path, 'w').close()
        os.utime(self.marks_path, (timestamp, timestamp))
        return timestamp

    def _verify_mark_after_test(self, mark_name, timestamp):
        """Verify that test has mark_name with timestamp in default location"""
        self.marks_path = os.path.join(self.marks_base, mark_name)
        self.assertTrue(os.path.exists(self.marks_path))
        self.assertEqual(os.path.getmtime(self.marks_path), timestamp)

    def before_each(self):
        """Setup fake configuration and temp dir before each test."""
        self.marks_base = os.path.join(self.configuration.mig_system_run,
                                       TEST_MARKS_DIR)
        ensure_dirs_exist(self.marks_base)
        self.marks_path = os.path.join(self.marks_base, TEST_MARKS_FILE)

    def test_update_filemark_create(self):
        """Test update_filemark creates mark file with timestamp"""
        timestamp = 4242
        self.assertFalse(os.path.isfile(self.marks_path))
        update_result = update_filemark(self.configuration, self.marks_base,
                                        TEST_MARKS_FILE, timestamp)
        self.assertTrue(update_result)
        self.assertTrue(os.path.isfile(self.marks_path))
        self.assertEqual(os.path.getmtime(self.marks_path), timestamp)

    def test_update_filemark_timestamp(self):
        """Test update_filemark updates existing file to given timestamp"""
        timestamp = 424242
        self._prepare_mark_for_test(TEST_MARKS_FILE, 4242)

        update_filemark(self.configuration, self.marks_base,
                        TEST_MARKS_FILE, timestamp)
        self.assertTrue(os.path.isfile(self.marks_path))
        self.assertEqual(os.path.getmtime(self.marks_path), timestamp)

    def test_update_filemark_delete(self):
        """Test update_filemark deletes mark files with negative timestamp"""
        self._prepare_mark_for_test(TEST_MARKS_FILE)

        delete_result = update_filemark(self.configuration, self.marks_base,
                                        TEST_MARKS_FILE, -1)
        self.assertTrue(delete_result)
        self.assertFalse(os.path.exists(self.marks_path))

    def test_get_filemark_existing(self):
        """Test get_filemark retrieves timestamp for existing mark"""
        timestamp = 4242
        self._prepare_mark_for_test(TEST_MARKS_FILE, timestamp)

        retrieved = get_filemark(self.configuration, self.marks_base,
                                 TEST_MARKS_FILE)
        self.assertEqual(retrieved, timestamp)

    def test_get_filemark_missing(self):
        """Test get_filemark returns None for missing mark files"""
        self.assertFalse(os.path.isfile(self.marks_path))
        retrieved = get_filemark(self.configuration, self.marks_base,
                                 'missing.mark')
        self.assertIsNone(retrieved)

    def test_reset_filemark_single(self):
        """Test reset_filemark updates single mark timestamp to 0"""
        self._prepare_mark_for_test(TEST_MARKS_FILE)

        reset_result = reset_filemark(self.configuration, self.marks_base,
                                      [TEST_MARKS_FILE])
        self.assertTrue(reset_result)

        self._verify_mark_after_test(TEST_MARKS_FILE, 0)

    def test_reset_filemark_delete(self):
        """Test reset_filemark deletes marks with delete=True"""
        self._prepare_mark_for_test(TEST_MARKS_FILE)

        reset_result = reset_filemark(self.configuration, self.marks_base,
                                      [TEST_MARKS_FILE], delete=True)
        self.assertTrue(reset_result)

        retrieved = get_filemark(self.configuration, self.marks_base,
                                 TEST_MARKS_FILE)
        self.assertIsNone(retrieved)
        self.assertFalse(os.path.exists(self.marks_path))

    def test_reset_filemark_all(self):
        """Test reset_filemark resets all marks when mark_list=None"""
        marks = ['mark1', 'mark2', 'mark3']
        for mark in marks:
            self._prepare_mark_for_test(mark)

        reset_result = reset_filemark(self.configuration, self.marks_base)
        self.assertTrue(reset_result)

        for mark in marks:
            self._verify_mark_after_test(mark, 0)

    def test_update_filemark_fails_when_file_prevents_directory(self):
        """Test update_filemark fails when file prevents create directory"""
        # Create a file in the way to prevent subdir creation
        self._prepare_mark_for_test('obstruct')

        result = update_filemark(self.configuration, self.marks_base,
                                 os.path.join('obstruct', 'test.mark'),
                                 time.time())
        self.assertFalse(result)

    @unittest.skipIf(os.getuid() == 0, "access check is ignored as priv user")
    def test_update_filemark_directory_perms_failure(self):
        """Test update_filemark fails on directory creation failure"""
        # Create a read-only parent directory to prevent subdir creation
        os.chmod(self.marks_base, stat.S_IRUSR)  # Remove write permissions

        result = update_filemark(self.configuration, self.marks_base,
                                 os.path.join('noaccess', 'test.mark'),
                                 time.time())
        self.assertFalse(result)

    @unittest.skipIf(os.getuid() == 0, "access check is ignored as priv user")
    def test_get_filemark_permission_denied(self):
        """Test get_filemark returns None when permission denied"""
        self._prepare_mark_for_test(TEST_MARKS_FILE)
        # Remove read permissions through parent dir
        os.chmod(self.marks_base, 0)

        result = get_filemark(self.configuration, self.marks_base,
                              TEST_MARKS_FILE)
        self.assertIsNone(result)
        # Restore permissions so cleanup works
        os.chmod(self.marks_base, stat.S_IRWXU)

    def test_reset_filemark_string_mark_list(self):
        """Test reset_filemark handles single string mark_list"""
        self._prepare_mark_for_test(TEST_MARKS_FILE)

        reset_result = reset_filemark(self.configuration, self.marks_base,
                                      TEST_MARKS_FILE)
        self.assertTrue(reset_result)

        self._verify_mark_after_test(TEST_MARKS_FILE, 0)

    def test_reset_filemark_invalid_mark_list(self):
        """Test reset_filemark fails with invalid mark_list type"""
        reset_result = reset_filemark(self.configuration, self.marks_base,
                                      {'invalid': 'type'})
        self.assertFalse(reset_result)

    def test_reset_filemark_all_missing_dir(self):
        """Test reset_filemark handles missing directory when mark_list=None"""
        shutil.rmtree(self.marks_base)  # Ensure directory doesn't exist
        reset_result = reset_filemark(self.configuration, self.marks_base)
        self.assertFalse(reset_result)

    @unittest.skipIf(os.getuid() == 0, "access check is ignored as priv user")
    def test_reset_filemark_partial_perms_failure(self):
        """Test reset_filemark with partial failure due to permissions"""
        valid_mark = 'valid.mark'
        invalid_mark = 'invalid.mark'
        invalid_path = os.path.join(self.marks_base, invalid_mark)
        # Create both marks but remove access to the latter
        self._prepare_mark_for_test(valid_mark)
        self._prepare_mark_for_test(invalid_mark)
        os.chmod(invalid_path, stat.S_IRUSR)  # Remove write permissions

        reset_result = reset_filemark(self.configuration, self.marks_base,
                                      [valid_mark, invalid_mark])
        self.assertFalse(reset_result)  # Should fail due to partial failure

        self._verify_mark_after_test(valid_mark, 0)

    def test_reset_filemark_partial_file_prevents_directory_failure(self):
        """Test reset_filemark with partial failure due to a file in the way"""
        valid_mark = 'valid.mark'
        invalid_mark = os.path.join('obstruct', 'invalid.mark')
        # Create valid mark and a file to prevent the invalid mark
        self._prepare_mark_for_test(valid_mark)
        # Create a file in the way to prevent subdir creation
        self._prepare_mark_for_test('obstruct')

        reset_result = reset_filemark(self.configuration, self.marks_base,
                                      [valid_mark, invalid_mark])
        self.assertFalse(reset_result)  # Should fail due to partial failure

        self._verify_mark_after_test(valid_mark, 0)

    def test_update_filemark_fails_when_file_prevents_directory(self):
        """Test update_filemark fails when file prevents create directory"""


if __name__ == '__main__':
    testmain()
