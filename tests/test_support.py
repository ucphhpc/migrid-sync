from __future__ import print_function
import os
import sys
import unittest

from tests.support import MigTestCase, PY2, testmain, temppath


class SupportTestCase(MigTestCase):
    @unittest.skipIf(PY2, "Python 3 only")
    def test_unclosed_files_are_recorded(self):
        tmp_path = temppath("support-unclosed", self)

        def open_without_close():
            with open(tmp_path, 'w'):
                pass
            open(tmp_path)
            return

        open_without_close()

        with self.assertRaises(RuntimeError):
            self._logger.check_empty_and_reset()

    def test_unclosed_files_are_reset(self):
        # test name is purposefully after ..._recorded in sort order
        # such that we can check the fake logger was cleaned up correctly
        try:
            # will not throw for a clean logger
            self._logger.check_empty_and_reset()
        except:
            self.assertTrue(False, "should not be reachable")


if __name__ == '__main__':
    testmain()
