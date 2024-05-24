# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addheader - add license header to all code modules.
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Unit tests for the migrid module pointed to in the filename"""

import binascii
from contextlib import contextmanager
import errno
import fcntl
import os
import sys
import zipfile

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MigTestCase, fixturepath, temppath, testmain
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
    def assertPathLockedExclusive(self, file_path):
        "Custom assertion to check whether a file is exclusively locked."

        with open(file_path) as conflicting_f:
            reraise = None
            try:
                fcntl.flock(
                    conflicting_f, fcntl.LOCK_NB | LOCK_EX)

                # we were errantly able to acquire a lock, mark errored
                reraise = AssertionError("RERAISE_MUST_UNLOCK")
            except Exception as maybeerr:
                if getattr(maybeerr, 'errno', None) == errno.EAGAIN:
                    # this is the expected exception - the logic tried to lock
                    # a file that was (as we intended) already locked, meaning
                    # this assertion has succeeded so we do not need to raise
                    pass
                else:
                    # some other error we did not expect occurred, record it
                    reraise = AssertionError("RERAISE_NO_UNLOCK")

            if reraise is not None:
                # if marked errored and locked, cleanup the lock we acquired but shouldn't
                if str(reraise) == 'RERAISE_MUST_UNLOCK':
                    fcntl.flock(conflicting_f, fcntl.LOCK_NB | fcntl.LOCK_UN)

                # raise a user-friendly error to aovid nested raise
                raise AssertionError(
                    "expected locked file: %s" % self.pretty_display_path(file_path))

    def test_localfile_locking(self):
        some_file = temppath(DUMMY_FILE, self)

        with managed_localfile(LocalFile(some_file, 'w')) as f:
            f.lock(LOCK_EX)

            self.assertEqual(f.get_lock_mode(), LOCK_EX)

            self.assertPathLockedExclusive(some_file)


if __name__ == '__main__':
    testmain()
