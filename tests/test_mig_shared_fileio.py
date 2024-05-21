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

assert isinstance(DUMMY_BYTES, bytes)

class TestFileioWriteChunk(MigTestCase):
    def setUp(self):
        super(TestFileioWriteChunk, self).setUp()
        self.tmp_path = temppath(DUMMY_FILE_WRITECHUNK, self, skip_clean=True)
        cleanpath(os.path.dirname(DUMMY_FILE_WRITECHUNK), self)

    def test_write_chunk_error_on_invalid_data(self):
        did_succeed = fileio.write_chunk(self.tmp_path, 1234, 0, self.logger)
        self.assertFalse(did_succeed)

    def test_write_chunk_creates_directory(self):
        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, 0, self.logger)

        path_kind = self.assertPathExists(DUMMY_FILE_WRITECHUNK)
        self.assertEqual(path_kind, "file")

    def test_write_chunk_store_bytes(self):
        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, 0, self.logger)

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH)
            self.assertEqual(content[:], DUMMY_BYTES)

    def test_write_chunk_store_bytes_at_offset(self):
        offset = 3

        fileio.write_chunk(self.tmp_path, DUMMY_BYTES, offset, self.logger)

        with open(self.tmp_path, 'rb') as file:
            content = file.read(1024)
            self.assertEqual(len(content), DUMMY_BYTES_LENGTH + offset)
            self.assertEqual(content[0:3], bytearray([0, 0, 0]), "expected a hole was left")
            self.assertEqual(content[3:], DUMMY_BYTES)

if __name__ == '__main__':
    testmain()
