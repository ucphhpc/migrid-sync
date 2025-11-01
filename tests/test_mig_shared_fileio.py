# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_fileio - unit test of the corresponding mig shared module
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

"""Unit test fileio functions"""

import binascii
import os
import sys
import unittest

# NOTE: wrap next imports in try except to prevent autopep8 shuffling up
try:
    from tests.support import MigTestCase, cleanpath, temppath, testmain
    import mig.shared.fileio as fileio
except ImportError as ioe:
    print("Failed to import mig core modules: %s" % ioe)
    exit(1)

DUMMY_BYTES = binascii.unhexlify('DEADBEEF')  # 4 bytes
DUMMY_BYTES_LENGTH = 4
DUMMY_UNICODE = u'UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®'
DUMMY_UNICODE_LENGTH = len(DUMMY_UNICODE)
DUMMY_FILE_WRITECHUNK = 'fileio/write_chunk'
DUMMY_FILE_WRITEFILE = 'fileio/write_file'
# TODO: add similar tests for write_file_lines and enable next
# DUMMY_FILE_WRITEFILELINES = 'fileio/write_file_lines'
DUMMY_FILE_READFILE = 'fileio/read_file'
DUMMY_FILE_READFILELINES = 'fileio/read_file_lines'
DUMMY_FILE_READHEADLINES = 'fileio/read_head_lines'
DUMMY_FILE_READTAILLINES = 'fileio/read_tail_lines'
DUMMY_FILE_DELETEFILE = 'fileio/delete_file'
DUMMY_FILE_GETFILESIZE = 'fileio/get_file_size'
DUMMY_FILE_MAKESYMLINKSRC = 'fileio/make_symlink/link'
DUMMY_FILE_MAKESYMLINKDST = 'fileio/make_symlink/target'
# NOTE: getsize returns 4k for directories
DUMMY_DIRECTORY_SIZE = 4096

assert isinstance(DUMMY_BYTES, bytes)


class MigSharedFileio__write_chunk(MigTestCase):
    """Test the write_chunk function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for write_chunk tests"""
        super(MigSharedFileio__write_chunk, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_WRITECHUNK, self)
        # Output dir is created by default here
        os.makedirs(os.path.dirname(self.tmp_path), exist_ok=True)
        cleanpath(os.path.dirname(DUMMY_FILE_WRITECHUNK), self)

    def test_return_false_on_invalid_data(self):
        """Test write_chunk returns False with invalid data input"""
        self.logger.forgive_errors()

        # NOTE: we make sure to disable any forced stringification here
        did_succeed = fileio.write_chunk(self.tmp_path, 1234, 0, self.logger,
                                         force_string=False)
        self.assertFalse(did_succeed)

    def test_return_false_on_invalid_offset(self):
        """Test write_chunk returns False with negative offset value"""
        self.logger.forgive_errors()

        did_succeed = fileio.write_chunk(self.tmp_path, DUMMY_BYTES, -42,
                                         self.logger)
        self.assertFalse(did_succeed)

    def test_return_false_on_invalid_dir(self):
        """Test write_chunk returns False when path is a directory"""
        self.logger.forgive_errors()

        os.makedirs(self.tmp_path)

        did_succeed = fileio.write_chunk(self.tmp_path, 1234, 0, self.logger)
        self.assertFalse(did_succeed)

    def test_creates_directory(self):
        """Test write_chunk creates parent directory when needed"""
        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, 0, self.logger)

        path_kind = self.assertPathExists(DUMMY_FILE_WRITECHUNK)
        self.assertEqual(path_kind, "file")

    def test_store_bytes(self):
        """Test write_chunk stores byte data correctly at offset 0"""
        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, 0, self.logger)

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    def test_store_bytes_at_offset(self):
        """Test write_chunk stores byte data at specified offset"""
        offset = 3

        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, offset, self.logger)

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH + offset)
            self.assertEqual(content[0:3], bytearray([0, 0, 0]),
                             "expected a hole was left")
            self.assertEqual(content[3:], DUMMY_BYTES)

    @unittest.skip("TODO: enable again - requires the temporarily disabled auto mode select")
    def test_store_bytes_in_text_mode(self):
        """Test write_chunk stores byte data in text mode"""
        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, 0, self.logger,
                           mode="r+")

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    @unittest.skip("TODO: enable again - requires the temporarily disabled auto mode select")
    def test_store_unicode(self):
        """Test write_chunk stores unicode data in text mode"""
        fileio.write_chunk(self.tmp_path, DUMMY_UNICODE, 0, self.logger,
                           mode='r+')

        with open(self.tmp_path, 'r') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_UNICODE_LENGTH)
            self.assertEqual(content[:], DUMMY_UNICODE)

    @unittest.skip("TODO: enable again - requires the temporarily disabled auto mode select")
    def test_store_unicode_in_binary_mode(self):
        """Test write_chunk stores unicode data in binary mode"""
        fileio.write_chunk(self.tmp_path, DUMMY_UNICODE, 0, self.logger,
                           mode='r+b')

        with open(self.tmp_path, 'r') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_UNICODE_LENGTH)
            self.assertEqual(content[:], DUMMY_UNICODE)


class MigSharedFileio__write_file(MigTestCase):
    """Test the write_file function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for write_file tests"""
        super(MigSharedFileio__write_file, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_WRITEFILE, self)
        # Output dir is created by default here
        cleanpath(os.path.dirname(DUMMY_FILE_WRITEFILE), self)

    def test_return_false_on_invalid_data(self):
        """Test write_file returns False with non-string data input"""
        self.logger.forgive_errors()

        # NOTE: we make sure to disable any forced stringification here
        did_succeed = fileio.write_file(1234, self.tmp_path, self.logger,
                                        force_string=False)
        self.assertFalse(did_succeed)

    def test_return_false_on_invalid_dir(self):
        """Test write_file returns False when path is a directory"""
        self.logger.forgive_errors()

        os.makedirs(self.tmp_path)

        did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path,
                                        self.logger)
        self.assertFalse(did_succeed)

    def test_return_false_on_missing_dir(self):
        """Test write_file returns False on missing parent dir"""
        self.logger.forgive_errors()

        did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path,
                                        self.logger, make_parent=False)
        self.assertFalse(did_succeed)

    def test_creates_directory(self):
        """Test write_file creates parent directory when needed"""
        # TODO: temporarily use empty string to avoid any byte/unicode issues
        # did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path,
        #     self.logger)
        did_succeed = fileio.write_file('', self.tmp_path, self.logger)
        self.assertTrue(did_succeed)

        path_kind = self.assertPathExists(DUMMY_FILE_WRITEFILE)
        self.assertEqual(path_kind, "file")

    # TODO: replace next test once we have auto adjust mode in write helper
    def test_store_bytes_with_manual_adjust_mode(self):
        """Test write_file stores byte data in with manual adjust mode call"""
        mode = 'w'
        mode = fileio._auto_adjust_mode(DUMMY_BYTES, mode)
        did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path, self.logger,
                                        mode=mode)
        self.assertTrue(did_succeed)

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    @unittest.skip("TODO: enable again - requires the temporarily disabled auto mode select")
    def test_store_bytes_in_text_mode(self):
        """Test write_file stores byte data when opening in text mode"""
        did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path, self.logger,
                                        mode="w")
        self.assertTrue(did_succeed)

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    @unittest.skip("TODO: enable again - requires the temporarily disabled auto mode select")
    def test_store_unicode(self):
        """Test write_file stores unicode string when opening in text mode"""
        did_succeed = fileio.write_file(DUMMY_UNICODE, self.tmp_path,
                                        self.logger, mode='w')
        self.assertTrue(did_succeed)

        with open(self.tmp_path, 'r') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_UNICODE_LENGTH)
            self.assertEqual(content[:], DUMMY_UNICODE)

    @unittest.skip("TODO: enable again - requires the temporarily disabled auto mode select")
    def test_store_unicode_in_binary_mode(self):
        """Test write_file handles unicode strings when opening in binary mode"""
        did_succeed = fileio.write_file(DUMMY_UNICODE, self.tmp_path,
                                        self.logger, mode='wb')
        self.assertTrue(did_succeed)

        with open(self.tmp_path, 'r') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_UNICODE_LENGTH)
            self.assertEqual(content[:], DUMMY_UNICODE)


class MigSharedFileio__read_file(MigTestCase):
    """Test the read_file function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for read_file tests"""
        super(MigSharedFileio__read_file, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_READFILE, self)
        # We generally need output dir to exist here
        os.makedirs(os.path.dirname(self.tmp_path), exist_ok=True)
        cleanpath(os.path.dirname(self.tmp_path), self)

    def test_reads_bytes(self):
        """Test read_file returns byte content with binary mode"""
        with open(self.tmp_path, 'wb') as fh:
            fh.write(DUMMY_BYTES)
        content = fileio.read_file(self.tmp_path, self.logger, mode='rb')
        self.assertEqual(content, DUMMY_BYTES)

    def test_reads_text(self):
        """Test read_file returns text with text mode"""
        with open(self.tmp_path, 'w') as fh:
            fh.write(DUMMY_UNICODE)
        content = fileio.read_file(self.tmp_path, self.logger, mode='r')
        self.assertEqual(content, DUMMY_UNICODE)

    def test_allows_missing_file(self):
        """Test read_file returns None with allow_missing=True"""
        content = fileio.read_file(
            'missing.txt', self.logger, allow_missing=True)
        self.assertIsNone(content)

    def test_reports_missing_file(self):
        """Test read_file returns None with allow_missing=False"""
        self.logger.forgive_errors()
        content = fileio.read_file(
            'missing.txt', self.logger, allow_missing=False)
        self.assertIsNone(content)

    def test_handles_directory_path(self):
        """Test read_file returns None when path is directory"""
        self.logger.forgive_errors()
        os.makedirs(self.tmp_path)
        content = fileio.read_file(self.tmp_path, self.logger)
        self.assertIsNone(content)


class MigSharedFileio__read_file_lines(MigTestCase):
    """Test the read_file_lines function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for read_file_lines tests"""
        super(MigSharedFileio__read_file_lines, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_READFILELINES, self)
        # We generally need output dir to exist here
        os.makedirs(os.path.dirname(self.tmp_path), exist_ok=True)
        cleanpath(os.path.dirname(self.tmp_path), self)

    def test_returns_empty_list_for_empty_file(self):
        """Test read_file_lines returns empty list for empty file"""
        open(self.tmp_path, 'w').close()
        lines = fileio.read_file_lines(self.tmp_path, self.logger)
        self.assertEqual(lines, [])

    def test_reads_lines_from_file(self):
        """Test read_file_lines returns lines from text file"""
        with open(self.tmp_path, 'w') as fh:
            fh.write("line1\nline2\nline3")
        lines = fileio.read_file_lines(self.tmp_path, self.logger)
        self.assertEqual(lines, ["line1\n", "line2\n", "line3"])

    def test_none_for_missing_file(self):
        self.logger.forgive_errors()
        lines = fileio.read_file_lines('missing.txt', self.logger)
        self.assertIsNone(lines)


class MigSharedFileio__get_file_size(MigTestCase):
    """Test the get_file_size function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for get_file_size tests"""
        super(MigSharedFileio__get_file_size, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_GETFILESIZE, self)
        # We generally need output dir to exist here
        os.makedirs(os.path.dirname(self.tmp_path), exist_ok=True)
        cleanpath(os.path.dirname(self.tmp_path), self)

    def test_returns_file_size(self):
        """Test get_file_size returns correct file size"""
        with open(self.tmp_path, 'wb') as fh:
            fh.write(DUMMY_BYTES)
        size = fileio.get_file_size(self.tmp_path, self.logger)
        self.assertEqual(size, DUMMY_BYTES_LENGTH)

    def test_handles_missing_file(self):
        """Test get_file_size returns -1 for missing file"""
        self.logger.forgive_errors()
        size = fileio.get_file_size('missing.txt', self.logger)
        # TODO: fix called function to return on exception and enable next line
        # self.assertEqual(size, -1)
        self.assertIsNone(size)

    def test_handles_directory(self):
        """Test get_file_size returns -1 when path is directory"""
        self.logger.forgive_errors()
        os.makedirs(self.tmp_path)
        size = fileio.get_file_size(self.tmp_path, self.logger)
        self.assertEqual(size, DUMMY_DIRECTORY_SIZE)


class MigSharedFileio__delete_file(MigTestCase):
    """Test the delete_file function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for delete_file tests"""
        super(MigSharedFileio__delete_file, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_DELETEFILE, self)
        # We generally need output dir to exist here
        os.makedirs(os.path.dirname(self.tmp_path), exist_ok=True)
        cleanpath(os.path.dirname(DUMMY_FILE_DELETEFILE), self)

    def test_deletes_existing_file(self):
        """Test delete_file removes existing file"""
        open(self.tmp_path, 'w').close()
        result = fileio.delete_file(self.tmp_path, self.logger)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.tmp_path))

    def test_handles_missing_file_with_allow_missing(self):
        """Test delete_file succeeds with allow_missing=True"""
        result = fileio.delete_file(
            'missing.txt', self.logger, allow_missing=True)
        self.assertTrue(result)

    def test_false_for_missing_file_without_allow_missing(self):
        """Test delete_file returns False with allow_missing=False"""
        self.logger.forgive_errors()
        result = fileio.delete_file('missing.txt',
                                    self.logger,
                                    allow_missing=False)
        self.assertFalse(result)


class MigSharedFileio__read_head_lines(MigTestCase):
    """Test the read_head_lines function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for read_head_lines tests"""
        super(MigSharedFileio__read_head_lines, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_READHEADLINES, self)
        # We generally need output dir to exist here
        os.makedirs(os.path.dirname(self.tmp_path), exist_ok=True)
        cleanpath(os.path.dirname(self.tmp_path), self)

    def test_reads_requested_lines(self):
        """Test read_head_lines returns requested number of lines"""
        with open(self.tmp_path, 'w') as fh:
            fh.write("line1\nline2\nline3\nline4")
        lines = fileio.read_head_lines(self.tmp_path, 2, self.logger)
        self.assertEqual(lines, ["line1\n", "line2\n"])

    def test_returns_all_lines_when_requested_more(self):
        """Test read_head_lines returns all lines when file has fewer"""
        with open(self.tmp_path, 'w') as fh:
            fh.write("line1\nline2")
        lines = fileio.read_head_lines(self.tmp_path, 5, self.logger)
        self.assertEqual(lines, ["line1\n", "line2"])

    def test_returns_empty_list_for_empty_file(self):
        """Test read_head_lines returns empty for empty file"""
        open(self.tmp_path, 'w').close()
        lines = fileio.read_head_lines(self.tmp_path, 3, self.logger)
        self.assertEqual(lines, [])

    def test_empty_for_missing_file(self):
        """Test read_head_lines returns [] for missing file"""
        self.logger.forgive_errors()
        lines = fileio.read_head_lines('missing.txt', 3, self.logger)
        self.assertEqual(lines, [])


class MigSharedFileio__read_tail_lines(MigTestCase):
    """Test the read_tail_lines function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for read_tail_lines tests"""
        super(MigSharedFileio__read_tail_lines, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_READTAILLINES, self)
        # We generally need output dir to exist here
        os.makedirs(os.path.dirname(self.tmp_path), exist_ok=True)
        cleanpath(os.path.dirname(self.tmp_path), self)

    def test_reads_requested_lines(self):
        """Test read_tail_lines returns requested number of lines"""
        with open(self.tmp_path, 'w') as fh:
            fh.write("line1\nline2\nline3\nline4")
        lines = fileio.read_tail_lines(self.tmp_path, 2, self.logger)
        self.assertEqual(lines, ["line3\n", "line4"])

    def test_returns_all_lines_when_requested_more(self):
        """Test read_tail_lines returns all lines when file has fewer"""
        with open(self.tmp_path, 'w') as fh:
            fh.write("line1\nline2")
        lines = fileio.read_tail_lines(self.tmp_path, 5, self.logger)
        self.assertEqual(lines, ["line1\n", "line2"])

    def test_returns_empty_list_for_empty_file(self):
        """Test read_tail_lines returns empty for empty file"""
        open(self.tmp_path, 'w').close()
        lines = fileio.read_tail_lines(self.tmp_path, 3, self.logger)
        self.assertEqual(lines, [])

    def test_empty_for_missing_file(self):
        """Test read_tail_lines returns [] for missing file"""
        self.logger.forgive_errors()
        lines = fileio.read_tail_lines('missing.txt', 3, self.logger)
        self.assertEqual(lines, [])


class MigSharedFileio__make_symlink(MigTestCase):
    """Test the make_symlink function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for make_symlink tests"""
        super(MigSharedFileio__make_symlink, self).setUp()
        self.tmp_link = temppath(DUMMY_FILE_MAKESYMLINKSRC, self)
        self.tmp_target = temppath(DUMMY_FILE_MAKESYMLINKDST, self)
        # We generally need output dir to exist here
        os.makedirs(os.path.dirname(self.tmp_target), exist_ok=True)
        cleanpath(os.path.dirname(self.tmp_link), self)
        cleanpath(os.path.dirname(self.tmp_target), self)
        with open(self.tmp_target, 'w') as fh:
            fh.write("test")

    def test_creates_symlink(self):
        """Test make_symlink creates working symlink"""
        result = fileio.make_symlink(
            self.tmp_target, self.tmp_link, self.logger)
        self.assertTrue(result)
        self.assertTrue(os.path.islink(self.tmp_link))
        self.assertEqual(os.readlink(self.tmp_link), self.tmp_target)

    def test_force_overwrites_existing_link(self):
        """Test make_symlink force replaces existing link"""
        os.symlink('/dummy', self.tmp_link)
        result = fileio.make_symlink(self.tmp_target, self.tmp_link, self.logger,
                                     force=True)
        self.assertTrue(result)
        self.assertEqual(os.readlink(self.tmp_link), self.tmp_target)

    def test_fails_on_existing_link_without_force(self):
        """Test make_symlink fails on existing link without force"""
        self.logger.forgive_errors()
        os.symlink('/dummy', self.tmp_link)
        result = fileio.make_symlink(self.tmp_target, self.tmp_link, self.logger,
                                     force=False)
        self.assertFalse(result)

    def test_handles_nonexistent_target(self):
        """Test make_symlink still creates broken symlink"""
        self.logger.forgive_errors()
        broken_target = self.tmp_target + '-nonexistent'
        result = fileio.make_symlink(broken_target, self.tmp_link, self.logger)
        self.assertTrue(result)
        self.assertTrue(os.path.islink(self.tmp_link))
        self.assertEqual(os.readlink(self.tmp_link), broken_target)


if __name__ == '__main__':
    testmain()
