# -*- coding: utf-8 -*-

import binascii
from contextlib import contextmanager
import fcntl
import os
import sys
import zipfile

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MigTestCase, fixturepath, projectrelative, temppath, testmain
from mig.shared.serverfile import LOCK_EX
from mig.shared.localfile import LocalFile

DUMMY_FILE = 'some_file'


@contextmanager
def managed_localfile(f):
    assert isinstance(f, LocalFile)
    try:
        yield f
    finally:
        if f.get_lock_mode() != fcntl.LOCK_UN:
            pass
        if not f.closed:
            f.close()


class MigSharedLocalfile(MigTestCase):
    def assertPathLocked(self, file_path):
        with open(file_path) as conflicting_f:
            reraise = False
            try:
                self.assertRaises(OSError, lambda: fcntl.flock(
                    conflicting_f, fcntl.LOCK_NB | LOCK_EX))
            except AssertionError:
                # if it did raise, clean up the lock we have but shouldn't
                fcntl.flock(conflicting_f, fcntl.LOCK_NB | fcntl.LOCK_UN)
                # delay throwing a user-friendly error to aovid nested raise
                reraise = True
            if reraise:
                # now raise something hospitable
                raise AssertionError(
                    "expected locked file: %s" % projectrelative(file_path))

    def test_localfile_locking(self):
        some_file = temppath(DUMMY_FILE, self)

        with managed_localfile(LocalFile(some_file, 'w')) as f:
            f.lock(LOCK_EX)

            self.assertEqual(f.get_lock_mode(), LOCK_EX)

            self.assertPathLocked(some_file)


if __name__ == '__main__':
    testmain()
