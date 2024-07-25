# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_trabsferfunctions - unit test of the corresponding mig shared module
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

from contextlib import contextmanager
import errno
import fcntl
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from tests.support import MigTestCase, fixturepath, temppath, testmain
from mig.shared.transferfunctions import load_data_transfers, \
    create_data_transfer, delete_data_transfer, lock_data_transfers, \
    unlock_data_transfers

DUMMY_TRANSFERS = "dummy-transfers"


@contextmanager
def managed_transfersfile(tfd):
    """Helper to assure transfer pickle files are properly handled"""

    try:
        yield tfd
    finally:
        if tfd.get_lock_mode() != fcntl.LOCK_UN:
            pass
        if not tfd.closed:
            tfd.close()


class MigSharedTransferfunctions(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def test_transfers_locking(self):
        transfers_file = temppath(DUMMY_TRANSFERS, self)

        ro_lock = lock_data_transfers(DUMMY_TRANSFERS, exclusive=False)
        ro_lock_again = lock_data_transfers(DUMMY_TRANSFERS, exclusive=False)
        assert(ro_lock and ro_lock_again)
        unlock_data_transfers(ro_lock_again)
        unlock_data_transfers(ro_lock)


if __name__ == '__main__':
    testmain()
