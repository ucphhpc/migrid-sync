# -*- coding: utf-8 -*-

import binascii
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MigTestCase, cleanpath, temppath, testmain

import mig.shared.fileio as fileio

DUMMY_BYTES = binascii.unhexlify('DEADBEEF') # 4 bytes
DUMMY_BYTES_LENGTH = 4
DUMMY_FILE_WRITECHUNK = 'fileio/write_chunk'
DUMMY_FILE_WRITEFILE = 'fileio/write_file'

assert isinstance(DUMMY_BYTES, bytes)

class MigSharedFileio__write_chunk(MigTestCase):
    def setUp(self):
        super(MigSharedFileio__write_chunk, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_WRITECHUNK, self, skip_clean=True)
        cleanpath(os.path.dirname(DUMMY_FILE_WRITECHUNK), self)

    def test_return_false_on_invalid_data(self):
        did_succeed = fileio.write_chunk(self.tmp_path, 1234, 0, self.logger)
        self.assertFalse(did_succeed)

    def test_return_false_on_invalid_dir(self):
        os.makedirs(self.tmp_path)

        did_succeed = fileio.write_chunk(self.tmp_path, 1234, 0, self.logger)
        self.assertFalse(did_succeed)

    def test_creates_directory(self):
        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, 0, self.logger)

        path_kind = self.assertPathExists(DUMMY_FILE_WRITECHUNK)
        self.assertEqual(path_kind, "file")

    def test_store_bytes(self):
        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, 0, self.logger)

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    def test_store_bytes_at_offset(self):
        offset = 3

        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, offset, self.logger)

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH + offset)
            self.assertEqual(content[0:3], bytearray([0, 0, 0]), "expected a hole was left")
            self.assertEqual(content[3:], DUMMY_BYTES)


class MigSharedFileio__write_file(MigTestCase):
    def setUp(self):
        super(MigSharedFileio__write_file, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_WRITEFILE, self, skip_clean=True)
        cleanpath(os.path.dirname(DUMMY_FILE_WRITEFILE), self)

    def test_return_false_on_invalid_data(self):
        did_succeed = fileio.write_file(1234, self.tmp_path, self.logger)
        self.assertFalse(did_succeed)

    def test_return_false_on_invalid_dir(self):
        os.makedirs(self.tmp_path)

        did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path, self.logger)
        self.assertFalse(did_succeed)

    def test_return_false_on_missing_dir(self):
        did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path, self.logger, make_parent=False)
        self.assertFalse(did_succeed)

    def test_creates_directory(self):
        did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path, self.logger)
        self.assertTrue(did_succeed)

        path_kind = self.assertPathExists(DUMMY_FILE_WRITEFILE)
        self.assertEqual(path_kind, "file")

    def test_store_bytes(self):
        did_succeed = fileio.write_file(DUMMY_BYTES, self.tmp_path, self.logger)
        self.assertTrue(did_succeed)

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)


if __name__ == '__main__':
    testmain()
