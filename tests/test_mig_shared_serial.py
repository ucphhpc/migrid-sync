# -*- coding: utf-8 -*-

import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MigTestCase, temppath, testmain
from mig.shared.serial import *

class BasicSerial(MigTestCase):
    BASIC_OBJECT = {'abc': 123, 'def': 'def', 'ghi': 42.0, 'accented': 'TéstÆøå'}

    def test_pickle_string(self):
        orig = BasicSerial.BASIC_OBJECT
        data = loads(dumps(orig))
        self.assertEqual(data, orig, "mismatch pickling string")

    def test_pickle_file(self):
        tmp_path = temppath("dummyserial.tmp", self)
        orig = BasicSerial.BASIC_OBJECT
        dump(orig, tmp_path)
        data = load(tmp_path)
        self.assertEqual(data, orig, "mismatch pickling string")

if __name__ == '__main__':
    testmain()
