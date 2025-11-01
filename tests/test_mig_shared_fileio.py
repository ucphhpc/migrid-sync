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

assert isinstance(DUMMY_BYTES, bytes)


class MigSharedFileio__write_chunk(MigTestCase):
    """Test the write_chunk function from mig.shared.fileio module"""

    def setUp(self):
        """Initialize test environment for write_chunk tests"""
        super(MigSharedFileio__write_chunk, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_WRITECHUNK, self)
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


if __name__ == '__main__':
    testmain()
