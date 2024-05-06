from __future__ import print_function
import sys

from unittest import TestCase

class TestBooleans(TestCase):
    def test_true(self):
        self.assertEqual(True, True)

    def test_false(self):
        self.assertEqual(False, False)
