# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_fileio - unit test of the corresponding mig shared module
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

"""Unit test fileio functions"""

import binascii
import os
import sys
import time
import unittest

# Imports of the code under test
import mig.shared.fileio as fileio

# Imports required for the unit tests themselves
from tests.support import MigTestCase, ensure_dirs_exist, testmain

DUMMY_BYTES = binascii.unhexlify("DEADBEEF")  # 4 bytes
DUMMY_BYTES_LENGTH = 4
DUMMY_UNICODE = "UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®"
DUMMY_UNICODE_LENGTH = len(DUMMY_UNICODE)
DUMMY_TEXT = "dummy"
DUMMY_TWICE = "dummy - dummy"
DUMMY_TESTDIR = "fileio"
DUMMY_SUBDIR = "subdir"
DUMMY_FILE_ONE = "file1.txt"
DUMMY_FILE_TWO = "file2.txt"
DUMMY_FILE_MISSING = "missing.txt"
DUMMY_FILE_RO = "readonly.txt"
DUMMY_FILE_WO = "writeonly.txt"
DUMMY_FILE_RW = "readwrite.txt"
DUMMY_DIRECTORY_NESTED = "nested/dir/structure"
DUMMY_DIRECTORY_EMPTY = "empty_dir"
DUMMY_DIRECTORY_MOVE_SRC = "move_dir_src"
DUMMY_DIRECTORY_MOVE_DST = "move_dir_dst"
DUMMY_DIRECTORY_REMOVE = "remove_dir"
DUMMY_DIRECTORY_CHECKACCESS = "check_access"
DUMMY_DIRECTORY_MAKEDIRSREC = "makedirs_rec"
DUMMY_DIRECTORY_COPYRECSRC = "copy_dir_src"
DUMMY_DIRECTORY_COPYRECDST = "copy_dir_dst"
DUMMY_DIRECTORY_REMOVEREC = "remove_rec"
# File/dir paths for move/copy operations
DUMMY_FILE_MOVE_SRC = "move_src"
DUMMY_FILE_MOVE_DST = "move_dst"
DUMMY_FILE_COPY_SRC = "copy_src"
DUMMY_FILE_COPY_DST = "copy_dst"
DUMMY_FILE_WRITECHUNK = "write_chunk"
DUMMY_FILE_WRITEFILE = "write_file"
DUMMY_FILE_WRITEFILELINES = "write_file_lines"
DUMMY_FILE_READFILE = "read_file"
DUMMY_FILE_READFILELINES = "read_file_lines"
DUMMY_FILE_READHEADLINES = "read_head_lines"
DUMMY_FILE_READTAILLINES = "read_tail_lines"
DUMMY_FILE_DELETEFILE = "delete_file"
DUMMY_FILE_GETFILESIZE = "get_file_size"
DUMMY_FILE_MAKESYMLINKSRC = "link_src"
DUMMY_FILE_MAKESYMLINKDST = "link_target"
DUMMY_FILE_DELETESYMLINKSRC = "link_src"
DUMMY_FILE_DELETESYMLINKDST = "link_target"
DUMMY_FILE_TOUCH = "touch_file"

assert isinstance(DUMMY_BYTES, bytes)


class MigSharedFileio__temporary_umask(MigTestCase):
    """Test the temporary_umask function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_file_one = os.path.join(self.tmp_base, DUMMY_FILE_ONE)
        try:
            os.chmod(self.tmp_file_one, 0o600)
            os.remove(self.tmp_file_one)
        except:
            pass
        self.tmp_file_two = os.path.join(self.tmp_base, DUMMY_FILE_TWO)
        try:
            os.chmod(self.tmp_file_two, 0o600)
            os.remove(self.tmp_file_two)
        except:
            pass
        self.assertFalse(os.path.exists(self.tmp_file_two))
        self.tmp_dir = os.path.join(self.tmp_base, DUMMY_DIRECTORY_EMPTY)
        try:
            os.chmod(self.tmp_dir, 0o700)
            os.rmdir(self.tmp_dir)
        except:
            pass
        self.assertFalse(os.path.exists(self.tmp_dir))

    def test_creates_new_file_with_temporary_umask_777(self):
        """Test create file with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o777):
            open(self.tmp_file_one, "w").close()
        self.assertTrue(os.path.isfile(self.tmp_file_one))
        self.assertEqual(os.stat(self.tmp_file_one).st_mode & 0o777, 0o000)

    def test_creates_new_file_with_temporary_umask_277(self):
        """Test create file with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o277):
            open(self.tmp_file_one, "w").close()
        self.assertTrue(os.path.isfile(self.tmp_file_one))
        self.assertEqual(os.stat(self.tmp_file_one).st_mode & 0o777, 0o400)

    def test_creates_new_file_with_temporary_umask_227(self):
        """Test create file with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o227):
            open(self.tmp_file_one, "w").close()
        self.assertTrue(os.path.isfile(self.tmp_file_one))
        self.assertEqual(os.stat(self.tmp_file_one).st_mode & 0o777, 0o440)

    def test_creates_new_file_with_temporary_umask_077(self):
        """Test create file with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o077):
            open(self.tmp_file_one, "w").close()
        self.assertTrue(os.path.isfile(self.tmp_file_one))
        self.assertEqual(os.stat(self.tmp_file_one).st_mode & 0o777, 0o600)

    def test_creates_new_file_with_temporary_umask_027(self):
        """Test create file with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o027):
            open(self.tmp_file_one, "w").close()
        self.assertTrue(os.path.isfile(self.tmp_file_one))
        self.assertEqual(os.stat(self.tmp_file_one).st_mode & 0o777, 0o640)

    def test_creates_new_file_with_temporary_umask_007(self):
        """Test create file with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o007):
            open(self.tmp_file_one, "w").close()
        self.assertTrue(os.path.isfile(self.tmp_file_one))
        self.assertEqual(os.stat(self.tmp_file_one).st_mode & 0o777, 0o660)

    def test_creates_new_file_with_temporary_umask_022(self):
        """Test create file with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o022):
            open(self.tmp_file_one, "w").close()
        self.assertTrue(os.path.isfile(self.tmp_file_one))
        self.assertEqual(os.stat(self.tmp_file_one).st_mode & 0o777, 0o644)

    def test_creates_new_file_with_temporary_umask_002(self):
        """Test create file with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o002):
            open(self.tmp_file_one, "w").close()
        self.assertTrue(os.path.isfile(self.tmp_file_one))
        self.assertEqual(os.stat(self.tmp_file_one).st_mode & 0o777, 0o664)

    def test_creates_new_file_with_temporary_umask_000(self):
        """Test create file with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o000):
            open(self.tmp_file_one, "w").close()
        self.assertTrue(os.path.isfile(self.tmp_file_one))
        self.assertEqual(os.stat(self.tmp_file_one).st_mode & 0o777, 0o666)

    def test_creates_new_directory_with_temporary_umask_777(self):
        """Test create dir with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o777):
            os.mkdir(self.tmp_dir)
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertEqual(os.stat(self.tmp_dir).st_mode & 0o777, 0o000)
        # NOTE: we need to make dir accessible to prevent failure in setup
        os.chmod(self.tmp_dir, 0o700)

    def test_creates_new_directory_with_temporary_umask_277(self):
        """Test create dir with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o277):
            os.mkdir(self.tmp_dir)
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertEqual(os.stat(self.tmp_dir).st_mode & 0o777, 0o500)

    def test_creates_new_directory_with_temporary_umask_227(self):
        """Test create dir with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o227):
            os.mkdir(self.tmp_dir)
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertEqual(os.stat(self.tmp_dir).st_mode & 0o777, 0o550)

    def test_creates_new_directory_with_temporary_umask_077(self):
        """Test create dir with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o077):
            os.mkdir(self.tmp_dir)
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertEqual(os.stat(self.tmp_dir).st_mode & 0o777, 0o700)

    def test_creates_new_directory_with_temporary_umask_027(self):
        """Test create dir with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o027):
            os.mkdir(self.tmp_dir)
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertEqual(os.stat(self.tmp_dir).st_mode & 0o777, 0o750)

    def test_creates_new_directory_with_temporary_umask_007(self):
        """Test create dir with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o007):
            os.mkdir(self.tmp_dir)
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertEqual(os.stat(self.tmp_dir).st_mode & 0o777, 0o770)

    def test_creates_new_directory_with_temporary_umask_022(self):
        """Test create dir with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o022):
            os.mkdir(self.tmp_dir)
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertEqual(os.stat(self.tmp_dir).st_mode & 0o777, 0o755)

    def test_creates_new_directory_with_temporary_umask_002(self):
        """Test create dir with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o002):
            os.mkdir(self.tmp_dir)
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertEqual(os.stat(self.tmp_dir).st_mode & 0o777, 0o775)

    def test_creates_new_directory_with_temporary_umask_000(self):
        """Test create dir with permissions restricted by given temp umask"""
        with fileio.temporary_umask(0o000):
            os.mkdir(self.tmp_dir)
        self.assertTrue(os.path.isdir(self.tmp_dir))
        self.assertEqual(os.stat(self.tmp_dir).st_mode & 0o777, 0o777)

    def test_restores_original_umask_after_exit(self):
        """Test temporary_umask restores original umask after context"""
        original_umask = os.umask(0o022)  # Set known umask
        try:
            # Enter temporary_umask context
            with fileio.temporary_umask(0o077):
                pass  # Just exit immediately
            # Check umask restored to original (0o022)
            current_umask = os.umask(original_umask)  # Retrieve and reset
            # Cleanup: Restore environment
            os.umask(current_umask)
            self.assertEqual(
                current_umask, 0o022, "Failed to restore original umask"
            )
        finally:
            os.umask(original_umask)  # Ensure cleanup

    def test_nested_temporary_umask(self):
        """Test nested temporary_umask contexts restore correctly"""
        original_umask = os.umask(0o022)
        try:
            with fileio.temporary_umask(0o027):  # Outer context
                open(self.tmp_file_one, "w").close()
                mode1 = os.stat(self.tmp_file_one).st_mode & 0o777
                self.assertEqual(mode1, 0o640)  # 666 & ~027 = 640
                with fileio.temporary_umask(0o077):  # Inner context
                    open(self.tmp_file_two, "w").close()
                    mode2 = os.stat(self.tmp_file_two).st_mode & 0o777
                    self.assertEqual(mode2, 0o600)  # 666 & ~077
                # Back to outer context umask
                os.remove(self.tmp_file_one)
                open(self.tmp_file_one, "w").close()
                mode1_after = os.stat(self.tmp_file_one).st_mode & 0o777
                self.assertEqual(mode1_after, 0o640)  # 666 & ~027
            # Back to original umask
            open(self.tmp_file_one, "w").close()
            mode_original = os.stat(self.tmp_file_one).st_mode & 0o777
            self.assertEqual(mode_original, 0o640)  # 666 & ~002
        finally:
            os.umask(original_umask)
            for path in [self.tmp_file_one, self.tmp_file_two]:
                if os.path.exists(path):
                    os.remove(path)

    def test_restores_umask_after_exception(self):
        """Test temporary_umask restores umask after exception"""
        original_umask = os.umask(0o022)
        try:
            try:
                with fileio.temporary_umask(0o077):
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected exception
            # Umask should be restored to original
            current_umask = os.umask(original_umask)
            os.umask(current_umask)  # Reset for next check
            self.assertEqual(current_umask, 0o022)
        finally:
            os.umask(original_umask)
            if os.path.exists(self.tmp_file_one):
                os.remove(self.tmp_file_one)

    def test_umask_does_not_affect_existing_files(self):
        """Test temporary_umask doesn't modify existing file permissions"""
        open(self.tmp_file_one, "w").close()
        os.chmod(self.tmp_file_one, 0o644)  # Explicit permissions
        with fileio.temporary_umask(0o077):  # Shouldn't affect existing file
            # Change permissions inside context
            os.chmod(self.tmp_file_one, 0o755)
        mode_after = os.stat(self.tmp_file_one).st_mode & 0o777
        # Directly set, not influenced by umask
        self.assertEqual(mode_after, 0o755)


class MigSharedFileio__write_chunk(MigTestCase):
    """Test the write_chunk function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_FILE_WRITECHUNK)

    def test_return_false_on_invalid_data(self):
        """Test write_chunk returns False with invalid data input"""
        self.logger.forgive_errors()

        # NOTE: we make sure to disable any forced stringification here
        did_succeed = fileio.write_chunk(
            self.tmp_path, 1234, 0, self.logger, force_string=False
        )
        self.assertFalse(did_succeed)

    def test_return_false_on_invalid_offset(self):
        """Test write_chunk returns False with negative offset value"""
        self.logger.forgive_errors()

        did_succeed = fileio.write_chunk(
            self.tmp_path, DUMMY_BYTES, -42, self.logger
        )
        self.assertFalse(did_succeed)

    def test_return_false_on_invalid_dir(self):
        """Test write_chunk returns False when path is a directory"""
        self.logger.forgive_errors()
        ensure_dirs_exist(self.tmp_path)
        did_succeed = fileio.write_chunk(self.tmp_path, 1234, 0, self.logger)
        self.assertFalse(did_succeed)

    def test_creates_directory(self):
        """Test write_chunk creates parent directory when needed"""
        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, 0, self.logger)

        path_kind = self.assertPathExists(self.tmp_path)
        self.assertEqual(path_kind, "file")

    def test_store_bytes(self):
        """Test write_chunk stores byte data correctly at offset 0"""
        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, 0, self.logger)

        with open(self.tmp_path, "rb") as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    def test_store_bytes_at_offset(self):
        """Test write_chunk stores byte data at specified offset"""
        offset = 3

        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, offset, self.logger)

        with open(self.tmp_path, "rb") as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH + offset)
            self.assertEqual(
                content[0:3], bytearray([0, 0, 0]), "expected a hole was left"
            )
            self.assertEqual(content[3:], DUMMY_BYTES)

    @unittest.skip(
        "TODO: enable again - requires the temporarily disabled auto mode select"
    )
    def test_store_bytes_in_text_mode(self):
        """Test write_chunk stores byte data in text mode"""
        fileio.write_chunk(
            self.tmp_path, DUMMY_BYTES, 0, self.logger, mode="r+"
        )

        with open(self.tmp_path, "rb") as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    @unittest.skip(
        "TODO: enable again - requires the temporarily disabled auto mode select"
    )
    def test_store_unicode(self):
        """Test write_chunk stores unicode data in text mode"""
        fileio.write_chunk(
            self.tmp_path, DUMMY_UNICODE, 0, self.logger, mode="r+"
        )

        with open(self.tmp_path, "r") as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_UNICODE_LENGTH)
            self.assertEqual(content[:], DUMMY_UNICODE)

    @unittest.skip(
        "TODO: enable again - requires the temporarily disabled auto mode select"
    )
    def test_store_unicode_in_binary_mode(self):
        """Test write_chunk stores unicode data in binary mode"""
        fileio.write_chunk(
            self.tmp_path, DUMMY_UNICODE, 0, self.logger, mode="r+b"
        )

        with open(self.tmp_path, "r") as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_UNICODE_LENGTH)
            self.assertEqual(content[:], DUMMY_UNICODE)


class MigSharedFileio__write_file(MigTestCase):
    """Test the write_file function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        # NOTE: we inject sub-directory to test with missing and existing
        self.tmp_dir = os.path.join(self.tmp_base, DUMMY_SUBDIR)
        self.tmp_path = os.path.join(self.tmp_dir, DUMMY_FILE_WRITEFILE)

    def test_return_false_on_invalid_data(self):
        """Test write_file returns False with non-string data input"""
        self.logger.forgive_errors()

        # NOTE: we make sure to disable any forced stringification here
        did_succeed = fileio.write_file(
            1234, self.tmp_path, self.logger, force_string=False
        )
        self.assertFalse(did_succeed)

    def test_return_false_on_invalid_dir(self):
        """Test write_file returns False when path is a directory"""
        self.logger.forgive_errors()
        ensure_dirs_exist(self.tmp_path)
        did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path, self.logger)
        self.assertFalse(did_succeed)

    def test_return_false_on_missing_dir(self):
        """Test write_file returns False on missing parent dir"""
        self.logger.forgive_errors()

        did_succeed = fileio.write_file(
            DUMMY_BYTES, self.tmp_path, self.logger, make_parent=False
        )
        self.assertFalse(did_succeed)

    def test_creates_directory(self):
        """Test write_file creates parent directory when needed"""
        # TODO: temporarily use empty string to avoid any byte/unicode issues
        # did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path,
        #     self.logger)
        did_succeed = fileio.write_file("", self.tmp_path, self.logger)
        self.assertTrue(did_succeed)

        path_kind = self.assertPathExists(self.tmp_path)
        self.assertEqual(path_kind, "file")

    # TODO: replace next test once we have auto adjust mode in write helper
    def test_store_bytes_with_manual_adjust_mode(self):
        """Test write_file stores byte data in with manual adjust mode call"""
        mode = "w"
        mode = fileio._auto_adjust_mode(DUMMY_BYTES, mode)
        did_succeed = fileio.write_file(
            DUMMY_BYTES, self.tmp_path, self.logger, mode=mode
        )
        self.assertTrue(did_succeed)

        with open(self.tmp_path, "rb") as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    @unittest.skip(
        "TODO: enable again - requires the temporarily disabled auto mode select"
    )
    def test_store_bytes_in_text_mode(self):
        """Test write_file stores byte data when opening in text mode"""
        did_succeed = fileio.write_file(
            DUMMY_BYTES, self.tmp_path, self.logger, mode="w"
        )
        self.assertTrue(did_succeed)

        with open(self.tmp_path, "rb") as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    @unittest.skip(
        "TODO: enable again - requires the temporarily disabled auto mode select"
    )
    def test_store_unicode(self):
        """Test write_file stores unicode string when opening in text mode"""
        did_succeed = fileio.write_file(
            DUMMY_UNICODE, self.tmp_path, self.logger, mode="w"
        )
        self.assertTrue(did_succeed)

        with open(self.tmp_path, "r") as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_UNICODE_LENGTH)
            self.assertEqual(content[:], DUMMY_UNICODE)

    @unittest.skip(
        "TODO: enable again - requires the temporarily disabled auto mode select"
    )
    def test_store_unicode_in_binary_mode(self):
        """Test write_file handles unicode strings when opening in binary mode"""
        did_succeed = fileio.write_file(
            DUMMY_UNICODE, self.tmp_path, self.logger, mode="wb"
        )
        self.assertTrue(did_succeed)

        with open(self.tmp_path, "r") as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_UNICODE_LENGTH)
            self.assertEqual(content[:], DUMMY_UNICODE)


class MigSharedFileio__write_file_lines(MigTestCase):
    """Test the write_file_lines function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        # NOTE: we inject sub-directory to test with missing and existing
        self.tmp_dir = os.path.join(self.tmp_base, DUMMY_SUBDIR)
        self.tmp_path = os.path.join(self.tmp_dir, DUMMY_FILE_WRITEFILELINES)

    def test_write_lines(self):
        """Test write_file_lines writes lines to a file"""
        test_lines = ["line1\n", "line2\n", "line3"]
        result = fileio.write_file_lines(test_lines, self.tmp_path, self.logger)
        self.assertTrue(result)

        # Verify with read_file_lines
        lines = fileio.read_file_lines(self.tmp_path, self.logger)
        self.assertEqual(lines, test_lines)

    def test_invalid_data(self):
        """Test write_file_lines raises TypeError for non-list input"""
        self.logger.forgive_errors()
        with self.assertRaises(TypeError):
            fileio.write_file_lines(4242, self.tmp_path, self.logger)

    def test_creates_directory(self):
        """Test write_file_lines creates parent directory when needed"""
        test_lines = ["test line"]
        result = fileio.write_file_lines(test_lines, self.tmp_path, self.logger)
        self.assertTrue(result)

        path_kind = self.assertPathExists(self.tmp_path)
        self.assertEqual(path_kind, "file")

    def test_return_false_on_invalid_dir(self):
        """Test write_file_lines returns False when path is directory"""
        self.logger.forgive_errors()
        ensure_dirs_exist(self.tmp_path)
        result = fileio.write_file_lines(
            [DUMMY_TEXT], self.tmp_path, self.logger
        )
        self.assertFalse(result)

    def test_return_false_on_missing_dir(self):
        """Test write_file_lines fails when parent directory missing"""
        self.logger.forgive_errors()
        result = fileio.write_file_lines(
            [DUMMY_TEXT], self.tmp_path, self.logger, make_parent=False
        )
        self.assertFalse(result)


class MigSharedFileio__read_file(MigTestCase):
    """Test the read_file function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_FILE_READFILE)

    def test_reads_bytes(self):
        """Test read_file returns byte content with binary mode"""
        with open(self.tmp_path, "wb") as fh:
            fh.write(DUMMY_BYTES)
        content = fileio.read_file(self.tmp_path, self.logger, mode="rb")
        self.assertEqual(content, DUMMY_BYTES)

    def test_reads_text(self):
        """Test read_file returns text with text mode"""
        with open(self.tmp_path, "w") as fh:
            fh.write(DUMMY_UNICODE)
        content = fileio.read_file(self.tmp_path, self.logger, mode="r")
        self.assertEqual(content, DUMMY_UNICODE)

    def test_allows_missing_file(self):
        """Test read_file returns None with allow_missing=True"""
        content = fileio.read_file(
            "missing.txt", self.logger, allow_missing=True
        )
        self.assertIsNone(content)

    def test_reports_missing_file(self):
        """Test read_file returns None with allow_missing=False"""
        self.logger.forgive_errors()
        content = fileio.read_file(
            "missing.txt", self.logger, allow_missing=False
        )
        self.assertIsNone(content)

    def test_handles_directory_path(self):
        """Test read_file returns None when path is directory"""
        self.logger.forgive_errors()
        ensure_dirs_exist(self.tmp_path)
        content = fileio.read_file(self.tmp_path, self.logger)
        self.assertIsNone(content)


class MigSharedFileio__read_file_lines(MigTestCase):
    """Test the read_file_lines function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_FILE_READFILELINES)

    def test_returns_empty_list_for_empty_file(self):
        """Test read_file_lines returns empty list for empty file"""
        open(self.tmp_path, "w").close()
        lines = fileio.read_file_lines(self.tmp_path, self.logger)
        self.assertEqual(lines, [])

    def test_reads_lines_from_file(self):
        """Test read_file_lines returns lines from text file"""
        with open(self.tmp_path, "w") as fh:
            fh.write("line1\nline2\nline3")
        lines = fileio.read_file_lines(self.tmp_path, self.logger)
        self.assertEqual(lines, ["line1\n", "line2\n", "line3"])

    def test_none_for_missing_file(self):
        self.logger.forgive_errors()
        lines = fileio.read_file_lines("missing.txt", self.logger)
        self.assertIsNone(lines)


class MigSharedFileio__get_file_size(MigTestCase):
    """Test the get_file_size function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_FILE_GETFILESIZE)

    def test_returns_file_size(self):
        """Test get_file_size returns correct file size"""
        with open(self.tmp_path, "wb") as fh:
            fh.write(DUMMY_BYTES)
        size = fileio.get_file_size(self.tmp_path, self.logger)
        self.assertEqual(size, DUMMY_BYTES_LENGTH)

    def test_handles_missing_file(self):
        """Test get_file_size returns -1 for missing file"""
        self.logger.forgive_errors()
        size = fileio.get_file_size("missing.txt", self.logger)
        self.assertEqual(size, -1)

    def test_handles_directory(self):
        """Test get_file_size returns -1 when path is directory"""
        self.logger.forgive_errors()
        ensure_dirs_exist(self.tmp_path)
        size = fileio.get_file_size(self.tmp_path, self.logger)
        # explicitly check absence of the failure case
        self.assertFalse(size == -1)
        # additional check as directories do have a size
        self.assertTrue(size > 0)


class MigSharedFileio__delete_file(MigTestCase):
    """Test the delete_file function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_FILE_DELETEFILE)

    def test_deletes_existing_file(self):
        """Test delete_file removes existing file"""
        open(self.tmp_path, "w").close()
        result = fileio.delete_file(self.tmp_path, self.logger)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.tmp_path))

    def test_handles_missing_file_with_allow_missing(self):
        """Test delete_file succeeds with allow_missing=True"""
        result = fileio.delete_file(
            "missing.txt", self.logger, allow_missing=True
        )
        self.assertTrue(result)

    def test_false_for_missing_file_without_allow_missing(self):
        """Test delete_file returns False with allow_missing=False"""
        self.logger.forgive_errors()
        result = fileio.delete_file(
            "missing.txt", self.logger, allow_missing=False
        )
        self.assertFalse(result)


class MigSharedFileio__read_head_lines(MigTestCase):
    """Test the read_head_lines function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_FILE_READHEADLINES)

    def test_reads_requested_lines(self):
        """Test read_head_lines returns requested number of lines"""
        with open(self.tmp_path, "w") as fh:
            fh.write("line1\nline2\nline3\nline4")
        lines = fileio.read_head_lines(self.tmp_path, 2, self.logger)
        self.assertEqual(lines, ["line1\n", "line2\n"])

    def test_returns_all_lines_when_requested_more(self):
        """Test read_head_lines returns all lines when file has fewer"""
        with open(self.tmp_path, "w") as fh:
            fh.write("line1\nline2")
        lines = fileio.read_head_lines(self.tmp_path, 5, self.logger)
        self.assertEqual(lines, ["line1\n", "line2"])

    def test_returns_empty_list_for_empty_file(self):
        """Test read_head_lines returns empty for empty file"""
        open(self.tmp_path, "w").close()
        lines = fileio.read_head_lines(self.tmp_path, 3, self.logger)
        self.assertEqual(lines, [])

    def test_empty_for_missing_file(self):
        """Test read_head_lines returns [] for missing file"""
        self.logger.forgive_errors()
        lines = fileio.read_head_lines("missing.txt", 3, self.logger)
        self.assertEqual(lines, [])


class MigSharedFileio__read_tail_lines(MigTestCase):
    """Test the read_tail_lines function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_FILE_READTAILLINES)

    def test_reads_requested_lines(self):
        """Test read_tail_lines returns requested number of lines"""
        with open(self.tmp_path, "w") as fh:
            fh.write("line1\nline2\nline3\nline4")
        lines = fileio.read_tail_lines(self.tmp_path, 2, self.logger)
        self.assertEqual(lines, ["line3\n", "line4"])

    def test_returns_all_lines_when_requested_more(self):
        """Test read_tail_lines returns all lines when file has fewer"""
        with open(self.tmp_path, "w") as fh:
            fh.write("line1\nline2")
        lines = fileio.read_tail_lines(self.tmp_path, 5, self.logger)
        self.assertEqual(lines, ["line1\n", "line2"])

    def test_returns_empty_list_for_empty_file(self):
        """Test read_tail_lines returns empty for empty file"""
        open(self.tmp_path, "w").close()
        lines = fileio.read_tail_lines(self.tmp_path, 3, self.logger)
        self.assertEqual(lines, [])

    def test_empty_for_missing_file(self):
        """Test read_tail_lines returns [] for missing file"""
        self.logger.forgive_errors()
        lines = fileio.read_tail_lines("missing.txt", 3, self.logger)
        self.assertEqual(lines, [])


class MigSharedFileio__make_symlink(MigTestCase):
    """Test the make_symlink function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_dir = os.path.join(self.tmp_base, DUMMY_SUBDIR)
        ensure_dirs_exist(self.tmp_dir)
        self.tmp_link = os.path.join(self.tmp_dir, DUMMY_FILE_MAKESYMLINKSRC)
        self.tmp_target = os.path.join(self.tmp_dir, DUMMY_FILE_MAKESYMLINKDST)
        with open(self.tmp_target, "w") as fh:
            fh.write(DUMMY_TEXT)

    def test_creates_symlink(self):
        """Test make_symlink creates working symlink"""
        result = fileio.make_symlink(
            self.tmp_target, self.tmp_link, self.logger
        )
        self.assertTrue(result)
        self.assertTrue(os.path.islink(self.tmp_link))
        self.assertEqual(os.readlink(self.tmp_link), self.tmp_target)

    def test_force_overwrites_existing_link(self):
        """Test make_symlink force replaces existing link"""
        os.symlink("/dummy", self.tmp_link)
        result = fileio.make_symlink(
            self.tmp_target, self.tmp_link, self.logger, force=True
        )
        self.assertTrue(result)
        self.assertEqual(os.readlink(self.tmp_link), self.tmp_target)

    def test_fails_on_existing_link_without_force(self):
        """Test make_symlink fails on existing link without force"""
        self.logger.forgive_errors()
        os.symlink("/dummy", self.tmp_link)
        result = fileio.make_symlink(
            self.tmp_target, self.tmp_link, self.logger, force=False
        )
        self.assertFalse(result)

    def test_handles_nonexistent_target(self):
        """Test make_symlink still creates broken symlink"""
        self.logger.forgive_errors()
        broken_target = self.tmp_target + "-nonexistent"
        result = fileio.make_symlink(broken_target, self.tmp_link, self.logger)
        self.assertTrue(result)
        self.assertTrue(os.path.islink(self.tmp_link))
        self.assertEqual(os.readlink(self.tmp_link), broken_target)


class MigSharedFileio__delete_symlink(MigTestCase):
    """Test the delete_symlink function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_dir = os.path.join(self.tmp_base, DUMMY_SUBDIR)
        ensure_dirs_exist(self.tmp_dir)
        self.tmp_link = os.path.join(self.tmp_dir, DUMMY_FILE_DELETESYMLINKSRC)
        self.tmp_target = os.path.join(
            self.tmp_dir, DUMMY_FILE_DELETESYMLINKDST
        )
        with open(self.tmp_target, "w") as fh:
            fh.write(DUMMY_TEXT)

    def create_symlink(self, target=None, link=None):
        """Helper to create valid symlink before deletion"""
        if target is None:
            target = self.tmp_target
        if link is None:
            link = self.tmp_link
        os.symlink(target, link)

    def test_deletes_existing_symlink(self):
        """Test delete_symlink removes existing symlink"""
        self.create_symlink()
        result = fileio.delete_symlink(self.tmp_link, self.logger)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.tmp_link))

    def test_handles_missing_file_with_allow_missing(self):
        """Test delete_symlink succeeds with allow_missing=True"""
        # First make sure file doesn't exist
        if os.path.exists(self.tmp_link):
            os.remove(self.tmp_link)
        result = fileio.delete_symlink(
            self.tmp_link, self.logger, allow_missing=True
        )
        self.assertTrue(result)

    def test_handles_missing_symlink_without_allow_missing(self):
        """Test delete_symlink fails with allow_missing=False"""
        self.logger.forgive_errors()
        result = fileio.delete_symlink(
            "missing_symlink", self.logger, allow_missing=False
        )
        self.assertFalse(result)

    @unittest.skip("TODO: implement check in tested function and enable again")
    def test_rejects_regular_file(self):
        """Test delete_symlink returns False when path is a regular file"""
        with open(self.tmp_link, "w") as fh:
            fh.write(DUMMY_TEXT)

        with self.assertLogs(level="ERROR") as log_capture:
            result = fileio.delete_symlink(self.tmp_link, self.logger)
        self.assertFalse(result)
        self.assertTrue(
            any("Could not remove" in msg for msg in log_capture.output)
        )

    def test_deletes_broken_symlink(self):
        """Test delete_symlink removes broken symlink"""
        # Create broken symlink
        broken_target = self.tmp_target + "-nonexistent"
        self.create_symlink(broken_target)
        self.assertTrue(os.path.islink(self.tmp_link))
        # Now delete it
        result = fileio.delete_symlink(self.tmp_link, self.logger)
        self.assertTrue(result)


class MigSharedFileio__touch(MigTestCase):
    """Test the touch function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_FILE_TOUCH)

    def test_creates_new_file(self):
        """Test touch creates new file if missing"""
        self.assertFalse(os.path.exists(self.tmp_path))
        result = fileio.touch(self.tmp_path, self.configuration)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.tmp_path))
        self.assertTrue(os.path.isfile(self.tmp_path))

    @unittest.skip(
        "TODO: fix invalid open 'r+w' in tested function and enable again"
    )
    def test_updates_timestamp_on_existing_file(self):
        """Test touch updates timestamp on existing file"""
        # Create initial file
        with open(self.tmp_path, "w") as fh:
            fh.write(DUMMY_TEXT)
        orig_mtime = os.path.getmtime(self.tmp_path)
        time.sleep(0.1)
        result = fileio.touch(self.tmp_path, self.configuration)
        self.assertTrue(result)
        new_mtime = os.path.getmtime(self.tmp_path)
        self.assertNotEqual(orig_mtime, new_mtime)

    @unittest.skip(
        "TODO: fix handling of directory in tested function and enable again"
    )
    def test_succeeds_on_directory(self):
        """Test touch succeeds for existing directory and updates timestamp"""
        ensure_dirs_exist(self.tmp_path)
        orig_mtime = os.path.getmtime(self.tmp_path)
        time.sleep(0.1)
        result = fileio.touch(self.tmp_path, self.configuration)
        self.assertTrue(result)
        self.assertTrue(os.path.isdir(self.tmp_path))
        new_mtime = os.path.getmtime(self.tmp_path)
        self.assertNotEqual(orig_mtime, new_mtime)

    def test_fails_on_missing_parent(self):
        """Test touch fails when parent directory doesn't exist"""
        self.logger.forgive_errors()
        nested_path = os.path.join(self.tmp_path, "missing", DUMMY_FILE_ONE)
        result = fileio.touch(nested_path, self.configuration)
        self.assertFalse(result)
        self.assertFalse(os.path.exists(nested_path))


class MigSharedFileio__remove_dir(MigTestCase):
    """Test the remove_dir function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_DIRECTORY_REMOVE)
        # NOTE: we prepare tmp_path as directory here
        ensure_dirs_exist(self.tmp_path)

    def test_removes_empty_directory(self):
        """Test remove_dir removes empty directory"""
        self.assertTrue(os.path.exists(self.tmp_path))
        result = fileio.remove_dir(self.tmp_path, self.configuration)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.tmp_path))

    def test_fails_on_nonempty_directory(self):
        """Test remove_dir returns False for non-empty directory"""
        self.logger.forgive_errors()
        # Add a file to the directory
        with open(os.path.join(self.tmp_path, DUMMY_FILE_ONE), "w") as fh:
            fh.write(DUMMY_TEXT)
        result = fileio.remove_dir(self.tmp_path, self.configuration)
        self.assertFalse(result)
        self.assertTrue(os.path.exists(self.tmp_path))

    def test_fails_on_file(self):
        """Test remove_dir returns False for file"""
        self.logger.forgive_errors()
        # Add a file to the directory
        file_path = os.path.join(self.tmp_path, DUMMY_FILE_ONE)
        with open(file_path, "w") as fh:
            fh.write(DUMMY_TEXT)
        result = fileio.remove_dir(file_path, self.configuration)
        self.assertFalse(result)
        self.assertTrue(os.path.exists(file_path))


class MigSharedFileio__remove_rec(MigTestCase):
    """Test the remove_rec function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_DIRECTORY_REMOVEREC)
        # Create a nested directory structure with files
        # fileio/remove_rec/
        # ├── file1.txt
        # └── subdir/
        #     └── file2.txt
        ensure_dirs_exist(os.path.join(self.tmp_path, DUMMY_SUBDIR))
        with open(os.path.join(self.tmp_path, DUMMY_FILE_ONE), "w") as fh:
            fh.write(DUMMY_TEXT)
        with open(
            os.path.join(self.tmp_path, DUMMY_SUBDIR, DUMMY_FILE_TWO), "w"
        ) as fh:
            fh.write(DUMMY_TWICE)

    def test_removes_directory_recursively(self):
        """Test remove_rec removes directory and contents"""
        self.assertTrue(os.path.exists(self.tmp_path))
        result = fileio.remove_rec(self.tmp_path, self.configuration)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.tmp_path))

    def test_removes_directory_recursively_with_symlink(self):
        """Test remove_rec removes directory and contents with symlink"""
        link_src = os.path.join(self.tmp_path, DUMMY_FILE_ONE)
        link_dst = os.path.join(self.tmp_path, DUMMY_FILE_ONE + ".lnk")
        os.symlink(link_src, link_dst)
        self.assertTrue(os.path.exists(self.tmp_path))
        result = fileio.remove_rec(self.tmp_path, self.configuration)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.tmp_path))

    def test_removes_directory_recursively_with_broken_symlink(self):
        """Test remove_rec removes directory and contents with broken symlink"""
        link_src = os.path.join(self.tmp_path, DUMMY_FILE_MISSING)
        link_dst = os.path.join(self.tmp_path, DUMMY_FILE_MISSING + ".lnk")
        os.symlink(link_src, link_dst)
        self.assertTrue(os.path.exists(self.tmp_path))
        result = fileio.remove_rec(self.tmp_path, self.configuration)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.tmp_path))

    def test_removes_directory_recursively_despite_readonly(self):
        """Test remove_rec removes directory and contents despite set readonly"""
        os.chmod(self.tmp_path, 0o500)
        file_path = os.path.join(self.tmp_path, DUMMY_FILE_ONE)
        os.chmod(file_path, 0o400)
        self.assertTrue(os.path.exists(self.tmp_path))
        result = fileio.remove_rec(self.tmp_path, self.configuration)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.tmp_path))

    def test_rejects_regular_file(self):
        """Test remove_rec returns False when path is a regular file"""
        file_path = os.path.join(self.tmp_path, DUMMY_FILE_ONE)
        with self.assertLogs(level="ERROR") as log_capture:
            result = fileio.remove_rec(file_path, self.configuration)
        self.assertFalse(result)
        self.assertTrue(
            any("Could not remove" in msg for msg in log_capture.output)
        )
        self.assertTrue(os.path.exists(file_path))


class MigSharedFileio__move_file(MigTestCase):
    """Test the move_file function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_src = os.path.join(self.tmp_base, DUMMY_FILE_MOVE_SRC)
        self.tmp_dst = os.path.join(self.tmp_base, DUMMY_FILE_MOVE_DST)
        with open(self.tmp_src, "w") as fh:
            fh.write(DUMMY_TEXT)

    def test_moves_file(self):
        """Test move_file successfully moves a file"""
        success, msg = fileio.move_file(
            self.tmp_src, self.tmp_dst, self.configuration
        )
        self.assertTrue(success)
        self.assertFalse(msg)
        self.assertFalse(os.path.exists(self.tmp_src))
        self.assertTrue(os.path.exists(self.tmp_dst))

    def test_overwrites_existing_destination(self):
        """Test move_file overwrites existing destination file"""
        # Create initial destination file
        with open(self.tmp_dst, "w") as fh:
            fh.write(DUMMY_TWICE)
        success, msg = fileio.move_file(
            self.tmp_src, self.tmp_dst, self.configuration
        )
        self.assertTrue(success)
        self.assertFalse(msg)
        with open(self.tmp_dst, "r") as fh:
            content = fh.read()
        self.assertEqual(content, DUMMY_TEXT)


class MigSharedFileio__move_rec(MigTestCase):
    """Test the move_rec function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_DIRECTORY_REMOVE)
        self.tmp_src = os.path.join(self.tmp_base, DUMMY_DIRECTORY_MOVE_SRC)
        self.tmp_dst = os.path.join(self.tmp_base, DUMMY_DIRECTORY_MOVE_DST)
        # Create a nested directory structure with files
        # fileio/move_dir_src/
        # ├── file1.txt
        # └── subdir/
        #     └── file2.txt
        ensure_dirs_exist(os.path.join(self.tmp_src, DUMMY_SUBDIR))
        with open(os.path.join(self.tmp_src, DUMMY_FILE_ONE), "w") as fh:
            fh.write(DUMMY_TEXT)
        with open(
            os.path.join(self.tmp_src, DUMMY_SUBDIR, DUMMY_FILE_TWO), "w"
        ) as fh:
            fh.write(DUMMY_TWICE)

    def test_moves_directory_recursively(self):
        """Test move_rec moves directory and contents"""
        result = fileio.move_rec(self.tmp_src, self.tmp_dst, self.configuration)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.tmp_src))
        self.assertTrue(os.path.exists(self.tmp_dst))
        # Verify structure
        self.assertTrue(
            os.path.exists(os.path.join(self.tmp_dst, DUMMY_FILE_ONE))
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(self.tmp_dst, DUMMY_SUBDIR, DUMMY_FILE_TWO)
            )
        )

    def test_extends_existing_destination(self):
        """Test move_rec extends existing destination directory"""
        # Create initial destination with some content
        ensure_dirs_exist(os.path.join(self.tmp_dst, DUMMY_TESTDIR))
        success, msg = fileio.move_rec(
            self.tmp_src, self.tmp_dst, self.configuration
        )
        self.assertTrue(success)
        self.assertFalse(msg)

        # Verify structure with new src subdir and existing dir
        new_sub = os.path.basename(DUMMY_DIRECTORY_MOVE_SRC)
        self.assertTrue(
            os.path.exists(os.path.join(self.tmp_dst, new_sub, DUMMY_FILE_ONE))
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.tmp_dst, new_sub, DUMMY_SUBDIR, DUMMY_FILE_TWO
                )
            )
        )
        self.assertTrue(
            os.path.exists(os.path.join(self.tmp_dst, DUMMY_TESTDIR))
        )


class MigSharedFileio__copy_file(MigTestCase):
    """Test the copy_file function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)

        self.tmp_src = os.path.join(self.tmp_base, DUMMY_FILE_COPY_SRC)
        self.tmp_dst = os.path.join(self.tmp_base, DUMMY_FILE_COPY_DST)
        with open(self.tmp_src, "w") as fh:
            fh.write(DUMMY_TEXT)

    def test_copies_file(self):
        """Test copy_file successfully copies a file"""
        result = fileio.copy_file(
            self.tmp_src, self.tmp_dst, self.configuration
        )
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.tmp_src))
        self.assertTrue(os.path.exists(self.tmp_dst))

    def test_overwrites_existing_destination(self):
        """Test copy_file overwrites existing destination file"""
        # Create initial destination file
        with open(self.tmp_dst, "w") as fh:
            fh.write(DUMMY_TWICE)
        result = fileio.copy_file(
            self.tmp_src, self.tmp_dst, self.configuration
        )
        self.assertTrue(result)
        with open(self.tmp_dst, "r") as fh:
            content = fh.read()
        self.assertEqual(content, DUMMY_TEXT)


class MigSharedFileio__copy_rec(MigTestCase):
    """Test the copy_rec function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_src = os.path.join(self.tmp_base, DUMMY_DIRECTORY_COPYRECSRC)
        self.tmp_dst = os.path.join(self.tmp_base, DUMMY_DIRECTORY_COPYRECDST)
        # Create a nested directory structure with files
        ensure_dirs_exist(self.tmp_src)
        ensure_dirs_exist(os.path.join(self.tmp_src, DUMMY_SUBDIR))
        with open(os.path.join(self.tmp_src, DUMMY_FILE_ONE), "w") as fh:
            fh.write(DUMMY_TEXT)
        with open(
            os.path.join(self.tmp_src, DUMMY_SUBDIR, DUMMY_FILE_TWO), "w"
        ) as fh:
            fh.write(DUMMY_TWICE)

    def test_copies_directory_recursively(self):
        """Test copy_rec copies directory and contents"""
        result = fileio.copy_rec(self.tmp_src, self.tmp_dst, self.configuration)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.tmp_src))
        self.assertTrue(os.path.exists(self.tmp_dst))
        # Verify structure
        self.assertTrue(
            os.path.exists(os.path.join(self.tmp_dst, DUMMY_FILE_ONE))
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(self.tmp_dst, DUMMY_SUBDIR, DUMMY_FILE_TWO)
            )
        )


class MigSharedFileio__check_empty_dir(MigTestCase):
    """Test the check_empty_dir function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.empty_path = os.path.join(self.tmp_base, DUMMY_DIRECTORY_EMPTY)
        self.nonempty_path = os.path.join(self.tmp_base, DUMMY_DIRECTORY_NESTED)
        ensure_dirs_exist(self.empty_path)
        # Create non-empty directory structure
        ensure_dirs_exist(self.nonempty_path)
        with open(os.path.join(self.nonempty_path, DUMMY_FILE_ONE), "w") as fh:
            fh.write(DUMMY_TEXT)

    def test_returns_true_for_empty(self):
        """Test check_empty_dir returns True for empty directory"""
        self.assertTrue(fileio.check_empty_dir(self.empty_path))

    def test_returns_false_for_nonempty(self):
        """Test check_empty_dir returns False for non-empty directory"""
        self.assertFalse(fileio.check_empty_dir(self.nonempty_path))

    def test_returns_false_for_file(self):
        """Test check_empty_dir returns False for file path"""
        file_path = os.path.join(self.nonempty_path, DUMMY_FILE_ONE)
        result = fileio.check_empty_dir(file_path)
        self.assertFalse(result)


class MigSharedFileio__makedirs_rec(MigTestCase):
    """Test the makedirs_rec function from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_path = os.path.join(self.tmp_base, DUMMY_DIRECTORY_MAKEDIRSREC)

    def test_creates_directory_path(self):
        """Test makedirs_rec creates nested directories"""
        nested_path = os.path.join(
            self.tmp_path, DUMMY_TESTDIR, DUMMY_SUBDIR, DUMMY_TESTDIR
        )
        result = fileio.makedirs_rec(nested_path, self.configuration)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(nested_path))

    def test_returns_true_for_existing_directory(self):
        """Test makedirs_rec returns True for existing path"""
        ensure_dirs_exist(self.tmp_path)
        result = fileio.makedirs_rec(self.tmp_path, self.configuration)
        self.assertTrue(result)

    def test_fails_for_file_path(self):
        """Test makedirs_rec returns False if path is file"""
        self.logger.forgive_errors()
        # Create a file at the path
        ensure_dirs_exist(self.tmp_path)
        file_path = os.path.join(self.tmp_path, DUMMY_FILE_ONE)
        with open(file_path, "w") as fh:
            fh.write(DUMMY_TEXT)
        result = fileio.makedirs_rec(file_path, self.configuration)
        self.assertFalse(result)


class MigSharedFileio__check_access(MigTestCase):
    """Test the various check access functions from mig.shared.fileio module"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return "testconfig"

    def before_each(self):
        """Setup test environment before each test method"""
        self.tmp_base = os.path.join(
            self.configuration.mig_system_run, DUMMY_TESTDIR
        )
        ensure_dirs_exist(self.tmp_base)
        self.tmp_dir = os.path.join(self.tmp_base, DUMMY_DIRECTORY_CHECKACCESS)
        ensure_dirs_exist(self.tmp_dir)
        self.writeonly_file = os.path.join(self.tmp_dir, DUMMY_FILE_WO)
        self.readonly_file = os.path.join(self.tmp_dir, DUMMY_FILE_RO)
        self.readwrite_file = os.path.join(self.tmp_dir, DUMMY_FILE_RW)

        # Create test files with different permissions
        with open(self.writeonly_file, "w") as fh:
            fh.write(DUMMY_TEXT)
        with open(self.readonly_file, "w") as fh:
            fh.write(DUMMY_TEXT)
        with open(self.readwrite_file, "w") as fh:
            fh.write(DUMMY_TEXT)

        # Set permissions
        os.chmod(self.tmp_base, 0o755)
        os.chmod(self.tmp_dir, 0o700)
        os.chmod(self.writeonly_file, 0o200)
        os.chmod(self.readonly_file, 0o400)
        os.chmod(self.readwrite_file, 0o600)

    def test_check_read_access_file(self):
        """Test check_read_access with readable file"""
        self.assertTrue(fileio.check_read_access(self.readwrite_file))
        self.assertTrue(fileio.check_read_access(self.readonly_file))
        self.assertTrue(fileio.check_read_access(self.tmp_dir, parent_dir=True))
        # Super-user has access to read and write all files!
        if os.getuid() == 0:
            self.assertTrue(fileio.check_read_access(self.writeonly_file))
        else:
            self.assertFalse(fileio.check_read_access(self.writeonly_file))
        self.assertFalse(fileio.check_read_access("/invalid/path"))

    def test_check_write_access_file(self):
        """Test check_write_access with writable file"""
        self.assertTrue(fileio.check_write_access(self.writeonly_file))
        self.assertTrue(fileio.check_write_access(self.readwrite_file))
        # Super-user has access to read and write all files!
        if os.getuid() == 0:
            self.assertTrue(fileio.check_write_access(self.readonly_file))
        else:
            self.assertFalse(fileio.check_write_access(self.readonly_file))
        self.assertFalse(fileio.check_write_access("/invalid/path"))

    def test_check_read_access_with_parent(self):
        """Test check_read_access with parent_dir True"""
        sub_file = os.path.join(self.tmp_dir, DUMMY_FILE_ONE)
        result = fileio.check_read_access(sub_file, parent_dir=True)
        self.assertTrue(result)

    def test_check_write_access_with_parent(self):
        """Test check_write_access with parent_dir True"""
        sub_file = os.path.join(self.tmp_dir, DUMMY_FILE_ONE)
        result = fileio.check_write_access(sub_file, parent_dir=True)
        self.assertTrue(result)

    def test_check_readable(self):
        """Test check_readable wrapper function"""
        self.assertTrue(
            fileio.check_readable(self.configuration, self.readwrite_file)
        )
        self.assertTrue(
            fileio.check_readable(self.configuration, self.readonly_file)
        )
        # Super-user has access to read and write all files!
        if os.getuid() == 0:
            self.assertTrue(
                fileio.check_readable(self.configuration, self.writeonly_file)
            )
        else:
            self.assertFalse(
                fileio.check_readable(self.configuration, self.writeonly_file)
            )
        self.assertFalse(
            fileio.check_readable(self.configuration, "/invalid/path")
        )

    def test_check_writable(self):
        """Test check_writable wrapper function"""
        self.assertTrue(
            fileio.check_writable(self.configuration, self.readwrite_file)
        )
        self.assertTrue(
            fileio.check_writable(self.configuration, self.writeonly_file)
        )
        # Super-user has access to read and write all files!
        if os.getuid() == 0:
            self.assertTrue(
                fileio.check_writable(self.configuration, self.readonly_file)
            )
        else:
            self.assertFalse(
                fileio.check_writable(self.configuration, self.readonly_file)
            )
        self.assertFalse(
            fileio.check_writable(self.configuration, "/no/such/file")
        )

    def test_check_readonly(self):
        """Test check_readonly wrapper function"""
        # Super-user has access to read and write all files!
        if os.getuid() == 0:
            # Test with read-only file path
            self.assertFalse(
                fileio.check_readonly(self.configuration, self.readonly_file)
            )

            # Test with writable file
            self.assertFalse(
                fileio.check_readonly(self.configuration, self.writeonly_file)
            )
            self.assertFalse(
                fileio.check_readonly(self.configuration, self.readwrite_file)
            )
        else:
            # Test with read-only file path
            self.assertTrue(
                fileio.check_readonly(self.configuration, self.readonly_file)
            )

            # Test with writable file
            self.assertFalse(
                fileio.check_readonly(self.configuration, self.writeonly_file)
            )
            self.assertFalse(
                fileio.check_readonly(self.configuration, self.readwrite_file)
            )

    def test_check_readwritable(self):
        """Test check_readwritable wrapper function"""
        self.assertTrue(
            fileio.check_readwritable(self.configuration, self.readwrite_file)
        )
        # Super-user has access to read and write all files!
        if os.getuid() == 0:
            self.assertTrue(
                fileio.check_readwritable(
                    self.configuration, self.readonly_file
                )
            )
            self.assertTrue(
                fileio.check_readwritable(
                    self.configuration, self.writeonly_file
                )
            )
        else:
            self.assertFalse(
                fileio.check_readwritable(
                    self.configuration, self.readonly_file
                )
            )
            self.assertFalse(
                fileio.check_readwritable(
                    self.configuration, self.writeonly_file
                )
            )

        self.assertFalse(
            fileio.check_readwritable(self.configuration, "/invalid/file")
        )

    def test_special_cases(self):
        """Test various special cases for access checks"""
        # Check directory paths
        self.assertTrue(fileio.check_read_access(self.tmp_dir))
        self.assertTrue(fileio.check_write_access(self.tmp_dir))

        # Check non-existent paths
        missing_path = os.path.join(self.tmp_dir, DUMMY_FILE_MISSING)
        self.assertFalse(fileio.check_read_access(missing_path))
        self.assertFalse(fileio.check_write_access(missing_path))

        # Check with custom follow_symlink=False
        self.assertTrue(
            fileio.check_read_access(self.readwrite_file, follow_symlink=False)
        )
        self.assertTrue(
            fileio.check_read_access(self.tmp_dir, True, follow_symlink=False)
        )


if __name__ == "__main__":
    testmain()
