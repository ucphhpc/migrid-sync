from __future__ import print_function

from tests.support import MigTestCase, testmain

class TestBooleans(MigTestCase):
    def test_true(self):
        self.assertEqual(True, True)

    def test_false(self):
        self.assertEqual(False, False)


if __name__ == '__main__':
    testmain()
