# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_filemarks - unit tests for shared filemarks helpers
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
# -- END_HEADER ---
#

"""Unit tests for mig.shared.filemarks module"""

import os
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

    def before_each(self):
        """Setup fake configuration and temp dir before each test."""
        self.marks_base = os.path.join(self.configuration.mig_system_run,
                                       TEST_MARKS_DIR)
        ensure_dirs_exist(os.path.dirname(self.marks_base))
        self.marks_path = os.path.join(self.marks_base, TEST_MARKS_FILE)

    def test_update_filemark_create(self):
        """Test update_filemark creates mark files"""
        timestamp = time.time()
        update_result = update_filemark(self.configuration, self.marks_base,
                                        TEST_MARKS_FILE, timestamp)
        self.assertTrue(update_result)
        self.assertTrue(os.path.isfile(self.marks_path))

    def test_update_filemark_timestamp(self):
        """Test update_filemark creates files with correct timestamp"""
        timestamp = time.time()
        update_filemark(self.configuration, self.marks_base,
                        TEST_MARKS_FILE, timestamp)
        self.assertTrue(os.path.isfile(self.marks_path))
        self.assertEqual(os.path.getmtime(self.marks_path), timestamp)

    def test_update_filemark_delete(self):
        """Test update_filemark deletes mark files with negative timestamp"""
        update_filemark(self.configuration, self.marks_base,
                        TEST_MARKS_FILE, time.time())
        delete_result = update_filemark(self.configuration, self.marks_base,
                                        TEST_MARKS_FILE, -1)
        self.assertTrue(delete_result)
        self.assertFalse(os.path.exists(self.marks_path))

    def test_get_filemark_existing(self):
        """Test get_filemark retrieves timestamp for existing mark"""
        timestamp = time.time()
        update_filemark(self.configuration, self.marks_base,
                        TEST_MARKS_FILE, timestamp)
        retrieved = get_filemark(self.configuration, self.marks_base,
                                 TEST_MARKS_FILE)
        self.assertEqual(retrieved, timestamp)

    def test_get_filemark_missing(self):
        """Test get_filemark returns None for missing mark files"""
        retrieved = get_filemark(self.configuration, self.marks_base,
                                 'missing.mark')
        self.assertIsNone(retrieved)

    def test_reset_filemark_single(self):
        """Test reset_filemark updates single mark timestamp to 0"""
        update_filemark(self.configuration, self.marks_base,
                        TEST_MARKS_FILE, time.time())
        reset_result = reset_filemark(self.configuration, self.marks_base,
                                      [TEST_MARKS_FILE])
        self.assertTrue(reset_result)
        retrieved = get_filemark(self.configuration, self.marks_base,
                                 TEST_MARKS_FILE)
        self.assertEqual(retrieved, 0)

    def test_reset_filemark_delete(self):
        """Test reset_filemark deletes marks with delete=True"""
        update_filemark(self.configuration, self.marks_base,
                        TEST_MARKS_FILE, time.time())
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
            update_filemark(self.configuration, self.marks_base, mark,
                            time.time())

        reset_result = reset_filemark(self.configuration, self.marks_base)
        self.assertTrue(reset_result)

        for mark in marks:
            result = get_filemark(self.configuration, self.marks_base, mark)
            self.assertEqual(result, 0)


if __name__ == '__main__':
    testmain()
