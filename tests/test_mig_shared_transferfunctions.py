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

from __future__ import print_function
import os
import sys
import tempfile

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from tests.support import TEST_OUTPUT_DIR, MigTestCase, FakeConfiguration, \
    cleanpath, temppath, testmain
from mig.shared.transferfunctions import get_transfers_path, \
    load_data_transfers, create_data_transfer, delete_data_transfer, \
    lock_data_transfers, unlock_data_transfers

DUMMY_USER = "dummy-user"
DUMMY_ID = "dummy-id"
DUMMY_HOME_DIR = 'dummy_user_home'
DUMMY_HOME_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_HOME_DIR)
DUMMY_SETTINGS_DIR = 'dummy_user_settings'
DUMMY_SETTINGS_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_SETTINGS_DIR)


def noop(*args, **kwargs):
    if args:
        return args[0]
    return None


class MigSharedTransferfunctions(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def test_transfers_basic_locking(self):
        os.makedirs(os.path.join(DUMMY_HOME_PATH, DUMMY_USER))
        cleanpath(DUMMY_HOME_DIR, self)
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        cleanpath(DUMMY_SETTINGS_DIR, self)
        dummy_conf = FakeConfiguration(user_home=DUMMY_HOME_PATH,
                                       user_settings=DUMMY_SETTINGS_PATH)
        transfers_path = get_transfers_path(dummy_conf, DUMMY_USER)

        # Lock shared twice should be fine
        ro_lock = lock_data_transfers(transfers_path, exclusive=False)
        ro_lock_again = lock_data_transfers(transfers_path, exclusive=False)
        assert(ro_lock and ro_lock_again)

        # Non-blocking repeated exclusive locking must fail
        rw_lock_again = lock_data_transfers(
            transfers_path, exclusive=True, blocking=False)
        assert(not rw_lock_again)

        # Unlock all to leave critical section and allow exclusive locking
        unlock_data_transfers(ro_lock)
        unlock_data_transfers(ro_lock_again)

        # Take exclusive lock
        rw_lock = lock_data_transfers(transfers_path, exclusive=True)
        # Non-blocking repeated shared or exclusive locking must fail
        ro_lock_again = lock_data_transfers(
            transfers_path, exclusive=False, blocking=False)
        rw_lock_again = lock_data_transfers(
            transfers_path, exclusive=True, blocking=False)
        assert(rw_lock and not ro_lock_again and not rw_lock_again)

        unlock_data_transfers(rw_lock)

    def test_create_and_delete_transfer(self):
        os.makedirs(os.path.join(DUMMY_HOME_PATH, DUMMY_USER))
        cleanpath(DUMMY_HOME_DIR, self)
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        cleanpath(DUMMY_SETTINGS_DIR, self)
        dummy_conf = FakeConfiguration(user_home=DUMMY_HOME_PATH,
                                       user_settings=DUMMY_SETTINGS_PATH)
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID})
        assert(success and DUMMY_ID in out)

        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER)

        assert(success and transfers.get(DUMMY_ID, None))

        (success, out) = delete_data_transfer(dummy_conf, DUMMY_USER, DUMMY_ID)
        assert(success and out == DUMMY_ID)

        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER)

        assert(success and transfers.get(DUMMY_ID, None) is None)

    def test_transfers_shared_read_locking(self):
        os.makedirs(os.path.join(DUMMY_HOME_PATH, DUMMY_USER))
        cleanpath(DUMMY_HOME_DIR, self)
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        cleanpath(DUMMY_SETTINGS_DIR, self)
        dummy_conf = FakeConfiguration(user_home=DUMMY_HOME_PATH,
                                       user_settings=DUMMY_SETTINGS_PATH)
        transfers_path = get_transfers_path(dummy_conf, DUMMY_USER)
        # Init a dummy transfer to read and delete later
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=True, blocking=False)

        # Lock shared to limit the next section to reading transfers
        ro_lock = lock_data_transfers(transfers_path, exclusive=False)
        assert(ro_lock)

        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER)
        assert(success and DUMMY_ID in transfers)

        # Create with repeated locking should fail
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=True, blocking=False)
        assert(not success)

        # Delete with repeated locking should fail
        (success, out) = delete_data_transfer(dummy_conf, DUMMY_USER, DUMMY_ID,
                                              do_lock=True, blocking=False)
        assert(not success)

        # Verify unchanged
        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER)
        assert(success and DUMMY_ID in transfers)

        # Unlock all to leave critical section and allow clean up
        unlock_data_transfers(ro_lock)

        # Delete with locking should be fine again
        (success, out) = delete_data_transfer(dummy_conf, DUMMY_USER, DUMMY_ID,
                                              do_lock=True)
        assert(success and out == DUMMY_ID)

    def test_transfers_exclusive_write_locking(self):
        os.makedirs(os.path.join(DUMMY_HOME_PATH, DUMMY_USER))
        cleanpath(DUMMY_HOME_DIR, self)
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        cleanpath(DUMMY_SETTINGS_DIR, self)
        dummy_conf = FakeConfiguration(user_home=DUMMY_HOME_PATH,
                                       user_settings=DUMMY_SETTINGS_PATH)
        transfers_path = get_transfers_path(dummy_conf, DUMMY_USER)

        # Take exclusive lock
        rw_lock = lock_data_transfers(transfers_path, exclusive=True)
        assert(rw_lock)

        # Non-blocking load with repeated locking should fail
        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER,
                                                   do_lock=True, blocking=False)
        assert(not success)

        # Load without repeated locking should be fine
        (success, transfers) = load_data_transfers(dummy_conf, DUMMY_USER,
                                                   do_lock=False)
        assert(success)

        # Non-blocking create with repeated locking should fail
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=True, blocking=False)
        assert(not success)

        # Create without repeated locking should be fine
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=False)
        assert(success)

        # Non-blocking delete with repeated locking should fail
        (success, out) = create_data_transfer(dummy_conf, DUMMY_USER,
                                              {'transfer_id': DUMMY_ID},
                                              do_lock=True, blocking=False)
        assert(not success)

        # Delete without repeated locking should be fine
        (success, out) = delete_data_transfer(dummy_conf, DUMMY_USER, DUMMY_ID,
                                              do_lock=False)
        assert(success)

        unlock_data_transfers(rw_lock)


if __name__ == '__main__':
    testmain()
