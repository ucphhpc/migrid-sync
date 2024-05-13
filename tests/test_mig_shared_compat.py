# -*- coding: utf-8 -*-

import binascii
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))
from support import MigTestCase, testmain

from mig.shared.compat import \
    ensure_native_string

DUMMY_BYTECHARS = b'DEADBEEF'
DUMMY_BYTESRAW = binascii.unhexlify('DEADBEEF') # 4 bytes

class MigSharedCompat__ensure_native_string(MigTestCase):
    def test_char_bytes_conversion(self):
        actual = ensure_native_string(DUMMY_BYTECHARS)
        self.assertEqual(actual, 'DEADBEEF')

    def test_raw_bytes_conversion(self):
        with self.assertRaises(UnicodeDecodeError):
            ensure_native_string(DUMMY_BYTESRAW)


if __name__ == '__main__':
    testmain()
