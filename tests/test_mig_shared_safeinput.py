# -*- coding: utf-8 -*-

import importlib
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MigTestCase, testmain


class MigSharedSafeinput(MigTestCase):

    def test_basic_import(self):
        safeimport = importlib.import_module("mig.shared.safeinput")

    def test_existing_main(self):
        safeimport = importlib.import_module("mig.shared.safeinput")
        safeimport.main(_print=lambda _: None)


if __name__ == '__main__':
    testmain()
