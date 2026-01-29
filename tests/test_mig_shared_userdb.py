# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_userdb - unit tests for shared user database handling
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# -- END_HEADER ---
#

"""Unit tests for user database functionality"""

import os
import time
import unittest

from mig.shared.base import distinguished_name_to_user
from mig.shared.fileio import delete_file
from mig.shared.serial import loads, dumps
from mig.shared.userdb import default_db_path, load_user_db, load_user_dict, \
    lock_user_db, save_user_db, save_user_dict, unlock_user_db, \
    update_user_dict
from tests.support import MigTestCase, ensure_dirs_exist, testmain

TEST_USER_ID = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
THIS_USER_ID = '/C=DK/ST=NA/L=NA/O=Local Org/OU=NA/CN=This User/emailAddress=this.user@here.org'
OTHER_USER_ID = '/C=DK/ST=NA/L=NA/O=Other Org/OU=NA/CN=Other User/emailAddress=other.user@there.org'


class TestMigSharedUserDB(MigTestCase):
    """Unit tests for user database functions in mig/shared/userdb.py"""

    def _provide_configuration(self):
        """Get test configuration"""
        return 'testconfig'

    # Helper methods
    def _generate_sample_db(self, content=None):
        """Generate a sample user DB dictionary with content"""
        if content is None:
            sample_db = {
                TEST_USER_ID: distinguished_name_to_user(TEST_USER_ID),
                THIS_USER_ID: distinguished_name_to_user(THIS_USER_ID)
            }
        else:
            sample_db = content
        return sample_db

    def _create_sample_db(self, content=None, db_path=None):
        """Create sample user DB file with given content"""
        if db_path is None:
            db_path = self.user_db_path
        sample_db = self._generate_sample_db(content)
        save_user_db(sample_db, db_path)
        return sample_db

    def before_each(self):
        """Set up test configuration and reset user DB paths"""
        ensure_dirs_exist(self.configuration.user_db_home)
        ensure_dirs_exist(self.configuration.mig_server_home)
        self.user_db_path = os.path.join(self.configuration.user_db_home,
                                         "MiG-users.db")
        self.legacy_db_path = os.path.join(self.configuration.mig_server_home,
                                           "MiG-users.db")

        # Clear any existing test DBs
        if os.path.exists(self.user_db_path):
            delete_file(self.user_db_path, self.logger)
        if os.path.exists(self.legacy_db_path):
            delete_file(self.legacy_db_path, self.logger)

        # Make empty test DBs
        self._create_sample_db(content={}, db_path=self.user_db_path)
        self._create_sample_db(content={}, db_path=self.legacy_db_path)

    def test_default_db_path(self):
        """Test default_db_path returns correct path structure"""
        expected = os.path.join(self.configuration.user_db_home,
                                "MiG-users.db")
        result = default_db_path(self.configuration)
        self.assertEqual(result, expected)

        # Test legacy path fallback
        self.configuration.user_db_home = '/no-such-dir'
        expected_legacy = os.path.join(self.configuration.mig_server_home,
                                       "MiG-users.db")
        result = default_db_path(self.configuration)
        self.assertEqual(result, expected_legacy)

    def test_shared_lock_unlock_user_db(self):
        """Test shared (non-exclusive) lock/unlock cycle for user database"""
        flock = lock_user_db(self.user_db_path, exclusive=False)
        self.assertTrue(flock is not None)
        self.assertTrue(flock.readable)
        # TODO: expose this attribute as false in the backend and enable next?
        # self.assertFalse(flock.writable)
        unlock_user_db(flock)

    def test_exclusive_lock_unlock_user_db(self):
        """Test exclusive lock/unlock cycle for user database"""
        flock = lock_user_db(self.user_db_path, exclusive=True)
        self.assertTrue(flock is not None)
        self.assertTrue(flock.readable)
        self.assertTrue(flock.writable)
        unlock_user_db(flock)

    def test_load_user_db_empty(self):
        """Test loading empty user database"""
        empty_db = {}
        with open(self.user_db_path, "wb") as fh:
            fh.write(dumps(empty_db))
        try:
            loaded = load_user_db(self.user_db_path)
        except Exception:
            loaded = None
        self.assertEqual(loaded, empty_db)

    def test_load_user_db_direct(self):
        """Test loading valid directly saved user database"""
        # Verify direct saved loading
        sample_db = self._generate_sample_db()
        with open(self.user_db_path, "wb") as fh:
            fh.write(dumps(sample_db))
        try:
            loaded = load_user_db(self.user_db_path)
        except Exception:
            loaded = None
        self.assertEqual(loaded, sample_db)

    def test_load_user_db_missing(self):
        """Test loading missing user database"""
        db_path = os.path.join(
            self.configuration.user_db_home, "no-such-db.db")
        try:
            loaded = load_user_db(db_path)
        except Exception:
            loaded = None
        self.assertEqual(loaded, None)

    def test_save_user_db_empty(self):
        """Test saving empty user database"""
        save_user_db({}, self.user_db_path)
        with open(self.user_db_path, "rb") as fh:
            pickled = fh.read()
            loaded = loads(pickled)
        self.assertEqual(loaded, {})

    def test_save_user_db_direct(self):
        """Test saving user database content"""
        sample_db = self._generate_sample_db()
        # Update DB
        sample_db["user3"] = {"field": "value3"}
        save_user_db(sample_db, self.user_db_path)
        with open(self.user_db_path, "rb") as fh:
            pickled = fh.read()
            loaded = loads(pickled)
        self.assertEqual(loaded, sample_db)

    def test_save_load_user_db_cycle(self):
        """Test complete cycle of saving and loading valid user database"""
        sample_db = self._generate_sample_db()
        save_user_db(sample_db, self.user_db_path)
        try:
            loaded = load_user_db(self.user_db_path)
        except Exception:
            loaded = None
        self.assertEqual(loaded, sample_db)

    def test_load_user_dict_missing(self):
        """Test loading non-existent user from DB"""
        self._create_sample_db()
        try:
            loaded = load_user_dict(self.logger, "no-such-user",
                                    self.user_db_path)
        except Exception:
            loaded = None
        self.assertIsNone(loaded)

    def test_load_user_dict_existing(self):
        """Test loading existing user from DB"""
        sample_db = self._create_sample_db()
        try:
            test_user_data = load_user_dict(self.logger, TEST_USER_ID,
                                            self.user_db_path)
        except Exception:
            test_user_data = None
        self.assertEqual(test_user_data, sample_db[TEST_USER_ID])

    def test_save_user_dict_new_user(self):
        """Test saving new user to database"""
        other_user = distinguished_name_to_user(OTHER_USER_ID)
        save_status = save_user_dict(self.logger, OTHER_USER_ID,
                                     other_user, self.user_db_path)
        self.assertTrue(save_status)

        with open(self.user_db_path, "rb") as fh:
            pickled = fh.read()
            loaded = loads(pickled)
        self.assertEqual(loaded[OTHER_USER_ID], other_user)

    def test_save_user_dict_update(self):
        """Test updating existing user in database"""
        sample_db = self._create_sample_db()
        changed = distinguished_name_to_user(THIS_USER_ID)
        changed.update({"Organization": "UPDATED", "new_field": "ADDED"})
        save_status = save_user_dict(self.logger, THIS_USER_ID,
                                     changed, self.user_db_path)
        self.assertTrue(save_status)

        with open(self.user_db_path, "rb") as fh:
            pickled = fh.read()
            loaded = loads(pickled)
        self.assertEqual(loaded[THIS_USER_ID], changed)

    def test_update_user_dict(self):
        """Test update_user_dict with partial changes"""
        sample_db = self._create_sample_db()
        updated = update_user_dict(self.logger, THIS_USER_ID,
                                   {"Organization": "CHANGED"},
                                   self.user_db_path)
        self.assertEqual(updated["Organization"], "CHANGED")

        with open(self.user_db_path, "rb") as fh:
            pickled = fh.read()
            loaded = loads(pickled)
        self.assertEqual(loaded[THIS_USER_ID]["Organization"], "CHANGED")

    def test_update_user_dict_requirements(self):
        """Test update_user_dict with invalid user ID"""
        self.logger.forgive_errors()
        try:
            result = update_user_dict(self.logger, "no-such-user",
                                      {"field": "test"}, self.user_db_path)
        except Exception:
            result = None
        self.assertIsNone(result)

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires locking fix")
    def test_concurrent_load_save(self):
        """Test concurrent access protection through locking"""
        # First thread acquires exclusive lock
        flock1 = lock_user_db(self.user_db_path)
        self.assertIsNotNone(flock1)

        # Second thread trying to lock should block
        self._create_sample_db()

        def delayed_load():
            try:
                loaded = load_user_db(self.user_db_path)
            except Exception:
                loaded = None
            return loaded

        import threading
        delayed_thread = threading.Thread(target=delayed_load)
        delayed_thread.start()
        time.sleep(0.2)
        self.assertTrue(delayed_thread.is_alive())

        # Release first lock and verify second completes
        unlock_user_db(flock1)
        delayed_thread.join(1.0)
        self.assertFalse(delayed_thread.is_alive())

    def test_save_user_db_pickle_abi(self):
        """Check save pickle compatibility to warn on underlying ABI changes"""
        orig_db = self._create_sample_db()
        with open(self.user_db_path, "rb") as fh:
            pickled = fh.read()
        loaded = loads(pickled)
        self.assertEqual(orig_db, loaded)

    def test_load_user_db_pickle_abi(self):
        """Check load pickle compatibility to warn on underlying ABI changes"""
        orig_db = self._generate_sample_db()
        with open(self.user_db_path, "wb") as fh:
            fh.write(dumps(orig_db))
        try:
            loaded = load_user_db(self.user_db_path)
        except Exception:
            loaded = None
        self.assertEqual(orig_db, loaded)

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires locking fix")
    def test_lock_user_db_invalid_path(self):
        """Test locking on non-existent database path"""
        invalid_path = os.path.join(
            self.configuration.user_db_home, "missing", "MiG-users.db")
        flock = lock_user_db(invalid_path)
        self.assertIsNone(flock)

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires locking fix")
    def test_unlock_user_db_invalid(self):
        """Test unlocking with None and invalid lock objects"""
        # Should handle without exceptions
        unlock_user_db(None)
        unlock_user_db("not a lock object")

    def test_load_user_db_corrupted(self):
        """Test loading corrupted user database"""
        with open(self.user_db_path, 'w') as fh:
            fh.write("invalid pickle content")
        with self.assertRaises(Exception):
            load_user_db(self.user_db_path)

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires error handling fix")
    def test_save_user_db_readonly(self):
        """Test saving to read-only database path"""
        sample_db = self._create_sample_db()
        try:
            os.chmod(self.user_db_path, 0o444)  # Read-only
        except Exception:
            self.skipTest("Read-only test not supported")
        try:
            with self.assertRaises(PermissionError):
                save_user_db({"test": "data"}, self.user_db_path)
        finally:
            os.chmod(self.user_db_path, 0o644)

    def test_load_user_dict_empty_db(self):
        """Test loading user from empty database"""
        self._create_sample_db(content={})
        loaded = load_user_dict(self.logger, TEST_USER_ID, self.user_db_path)
        self.assertIsNone(loaded)

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires ID validation fix")
    def test_save_user_dict_invalid_id(self):
        """Test saving user with invalid characters in ID"""
        invalid_id = "../../invalid.user"
        user_dict = distinguished_name_to_user(TEST_USER_ID)
        save_status = save_user_dict(self.logger, invalid_id,
                                     user_dict, self.user_db_path)
        self.assertFalse(save_status)

    def test_update_user_dict_empty_changes(self):
        """Test update_user_dict with empty changes dictionary"""
        # Let log error about o changes pass
        self.logger.forgive_errors()
        sample_db = self._create_sample_db()
        original = sample_db[THIS_USER_ID].copy()
        updated = update_user_dict(self.logger, THIS_USER_ID, {},
                                   self.user_db_path)
        self.assertEqual(updated, original)

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires error handling fix")
    def test_default_db_path_no_valid_paths(self):
        """Test default_db_path with no valid locations"""
        self.configuration.user_db_home = None
        self.configuration.mig_server_home = None
        with self.assertRaises(ValueError):
            default_db_path(self.configuration)

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires validation fix")
    def test_save_user_db_datatypes(self):
        """Test saving non-dictionary database content"""
        with self.assertRaises(TypeError):
            save_user_db("invalid content", self.user_db_path)

    def test_load_user_db_allows_concurrent_read_access(self):
        """Test (emulated) thread-safe multiple-reader load with shared lock"""
        flock = lock_user_db(self.user_db_path, exclusive=False)
        try:
            # Existing shared lock should still allow concurrent reads
            loaded = load_user_db(self.user_db_path)
            self.assertIsInstance(loaded, dict)
        finally:
            unlock_user_db(flock)


if __name__ == '__main__':
    testmain()
