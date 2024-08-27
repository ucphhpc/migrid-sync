# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_transferfunctions - unit test of the corresponding mig shared module
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

import os
import sys
import tempfile

from tests.support import TEST_OUTPUT_DIR, MigTestCase, FakeConfiguration, \
    cleanpath, temppath, testmain
from mig.shared.transferfunctions import get_transfers_path, \
    load_data_transfers, create_data_transfer, delete_data_transfer, \
    lock_data_transfers, unlock_data_transfers

DUMMY_USER = "dummy-user"
DUMMY_ID = "dummy-id"
DUMMY_HOME_DIR = 'dummy_user_home'
DUMMY_SETTINGS_DIR = 'dummy_user_settings'


def noop(*args, **kwargs):
    if args:
        return args[0]
    return None


class MigSharedTransferfunctions(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def before_each(self):
        test_user_home = temppath(DUMMY_HOME_DIR, self, ensure_dir=True)
        test_user_settings = cleanpath(
            DUMMY_SETTINGS_DIR, self, ensure_dir=True)
        # make two requisite root folders for the dummy user
        os.mkdir(os.path.join(test_user_home, DUMMY_USER))
        os.mkdir(os.path.join(test_user_settings, DUMMY_USER))
        # now create a configuration
        self.dummy_conf = FakeConfiguration(user_home=test_user_home,
                                            user_settings=test_user_settings)

    def test_transfers_basic_locking_shared(self):
        dummy_conf = self.dummy_conf
        transfers_path = get_transfers_path(dummy_conf, DUMMY_USER)

        # Lock shared twice should be fine
        ro_lock = lock_data_transfers(transfers_path, exclusive=False)
        ro_lock_again = lock_data_transfers(transfers_path, exclusive=False)
        self.assertTrue(ro_lock)
        self.assertTrue(ro_lock_again)

        unlock_data_transfers(ro_lock)
        unlock_data_transfers(ro_lock_again)

    def test_transfers_basic_locking_ro_to_rw_exclusive(self):
        dummy_conf = self.dummy_conf
        transfers_path = get_transfers_path(dummy_conf, DUMMY_USER)

        # Non-blocking exclusive locking of shared lock must fail
        ro_lock = lock_data_transfers(
            transfers_path, exclusive=True, blocking=False)
        rw_lock = lock_data_transfers(
            transfers_path, exclusive=True, blocking=False)

        self.assertTrue(ro_lock)
        self.assertFalse(rw_lock)

        unlock_data_transfers(ro_lock)

    def test_transfers_basic_locking_exclusive(self):
        dummy_conf = self.dummy_conf
        transfers_path = get_transfers_path(dummy_conf, DUMMY_USER)

        # Take exclusive lock
        rw_lock = lock_data_transfers(transfers_path, exclusive=True)
        # Non-blocking repeated shared or exclusive locking must fail
        ro_lock_again = lock_data_transfers(
            transfers_path, exclusive=False, blocking=False)
        rw_lock_again = lock_data_transfers(
            transfers_path, exclusive=True, blocking=False)

        self.assertTrue(rw_lock)
        self.assertFalse(ro_lock_again)
        self.assertFalse(rw_lock_again)

        unlock_data_transfers(rw_lock)

    def test_create_and_delete_transfer(self):
        dummy_conf = self.dummy_conf

        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID})
        self.assertTrue(success and DUMMY_ID in out)

        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER)

        self.assertTrue(success and transfers.get(DUMMY_ID, None))

        (success, out) = delete_data_transfer(dummy_conf, DUMMY_USER, DUMMY_ID)
        self.assertTrue(success and out == DUMMY_ID)

        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER)

        self.assertTrue(success and transfers.get(DUMMY_ID, None) is None)

    def test_transfers_shared_read_locking(self):
        dummy_conf = self.dummy_conf
        transfers_path = get_transfers_path(dummy_conf, DUMMY_USER)
        # Init a dummy transfer to read and delete later
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=True, blocking=False)
        # take a shared ro lock up front
        ro_lock = lock_data_transfers(transfers_path, exclusive=False)

        # cases:

        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER)
        self.assertTrue(success and DUMMY_ID in transfers)

        # Create with repeated locking should fail
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=True, blocking=False)
        self.assertFalse(success)

        # Delete with repeated locking should fail
        (success, out) = delete_data_transfer(dummy_conf, DUMMY_USER, DUMMY_ID,
                                              do_lock=True, blocking=False)
        self.assertFalse(success)

        # Verify unchanged
        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER)
        self.assertTrue(success and DUMMY_ID in transfers)

        # Unlock all to leave critical section and allow clean up
        unlock_data_transfers(ro_lock)

        # Delete with locking should be fine again
        (success, out) = delete_data_transfer(dummy_conf, DUMMY_USER, DUMMY_ID,
                                              do_lock=True)
        self.assertTrue(success and out == DUMMY_ID)

    def test_transfers_exclusive_write_locking(self):
        dummy_conf = self.dummy_conf
        transfers_path = get_transfers_path(dummy_conf, DUMMY_USER)
        # take excluse rw lock up front
        rw_lock = lock_data_transfers(transfers_path, exclusive=True)

        # cases:

        # Non-blocking load with repeated locking should fail
        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER,
                                                   do_lock=True, blocking=False)
        self.assertFalse(success)

        # Load without repeated locking should be fine
        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER,
                                                   do_lock=False)
        self.assertTrue(success)

        # Non-blocking create with repeated locking should fail
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=True, blocking=False)
        self.assertFalse(success)

        # Create without repeated locking should be fine
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=False)
        self.assertTrue(success)

        # Non-blocking delete with repeated locking should fail
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=True, blocking=False)
        self.assertFalse(success)

        # Delete without repeated locking should be fine
        (success, out) = delete_data_transfer(dummy_conf, DUMMY_USER, DUMMY_ID,
                                              do_lock=False)
        self.assertTrue(success)

        unlock_data_transfers(rw_lock)


if __name__ == '__main__':
    testmain(failfast=True)
