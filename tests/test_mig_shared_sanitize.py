# -*- coding: utf-8 -*-

import importlib
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))
from support import MigTestCase, testmain

from mig.shared.sanitize import safename_encode, safename_decode, NotAnExistingSafenameError

DUMMY_ASCII = u'abcde123467890'
DUMMY_ASCII_WITH_REPLACE = "$abcde$123467890$"
DUMMY_EXOTIC = u'UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®'


class MigSharedSanitize_safename(MigTestCase):
    def test_encode_basic(self):
        safename_encode("")

    def test_encode_ascii(self):
        encoded = safename_encode(DUMMY_ASCII)

        self.assertEqual(
            encoded, "abcde123467890\x1b\x1b")

    def test_encode_exotic(self):
        encoded = safename_encode(DUMMY_EXOTIC)

        self.assertEqual(
            encoded, "UniCode123@\x1b24\x1b\x1blna3a4dm6e3ftgua80ewlwka88boszo7i7iv930g")

    def test_decode_a_non_safename(self):
        with self.assertRaises(Exception) as asserted:
            safename_decode("foobar")

        the_exception = asserted.exception
        self.assertIsInstance(the_exception, NotAnExistingSafenameError)

    def test_decode_basic(self):
        safename_decode("")

    def test_decode_ascii(self):
        decoded = safename_decode("abcde123467890\x1b\x1b")

        self.assertEqual(decoded, DUMMY_ASCII)

    def test_decode_exotic(self):
        decoded = safename_decode("UniCode123@\x1b24\x1b\x1blna3a4dm6e3ftgua80ewlwka88boszo7i7iv930g")

        self.assertEqual(decoded, DUMMY_EXOTIC)

    def test_roundtrip_empty(self):
        inputvalue = ""

        outputvalue = safename_decode(safename_encode(inputvalue))

        self.assertEqual(outputvalue, inputvalue)

    def test_roundtrip_ascii(self):
        inputvalue = DUMMY_ASCII_WITH_REPLACE

        outputvalue = safename_decode(safename_encode(inputvalue))

        self.assertEqual(outputvalue, inputvalue)


def main():
    testmain(failfast=True)


if __name__ == '__main__':
    main()
