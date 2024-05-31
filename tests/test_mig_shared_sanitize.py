# -*- coding: utf-8 -*-

import importlib
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MigTestCase, testmain

from mig.shared.sanitize import safename_encode, safename_decode

DUMMY_EXOTIC = u'UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®'


class MigSharedSanitize_safename(MigTestCase):
    def test_executes_encode(self):
        safename_encode("")

    def test_encode_exotic(self):
        encoded = safename_encode(DUMMY_EXOTIC)

        self.assertEqual(
            encoded, "UniCode123@$-lna3a4dm6e3ftgua80ewlwka88boszo7i7iv930g")

    def test_executes_decode(self):
        safename_decode("")

    def test_roundtrip_empty(self):
        inputvalue = ""

        outputvalue = safename_decode(safename_encode(inputvalue))

        self.assertEqual(outputvalue, inputvalue)

    def test_roundtrip_ascii(self):
        inputvalue = "abcde123467890"

        outputvalue = safename_decode(safename_encode(inputvalue))

        self.assertEqual(outputvalue, inputvalue)


if __name__ == '__main__':
    testmain()
