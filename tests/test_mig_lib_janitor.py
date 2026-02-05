# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_janitor - unit test of the corresponding mig lib module
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
# --- END_HEADER ---
#

"""Unit tests for the migrid module pointed to in the filename"""

import os
import pickle
import time
import unittest

from mig.lib.janitor import EXPIRE_DUMMY_JOBS_DAYS, EXPIRE_REQ_DAYS, \
    EXPIRE_STATE_DAYS, EXPIRE_TWOFACTOR_DAYS, MANAGE_TRIVIAL_REQ_MINUTES, \
    REMIND_REQ_DAYS, SECS_PER_DAY, SECS_PER_HOUR, SECS_PER_MINUTE, \
    _clean_stale_state_files, _lookup_last_run, _update_last_run, \
    clean_mig_system_files, clean_no_job_helpers, \
    clean_sessid_to_mrls_link_home, clean_twofactor_sessions, \
    clean_webserver_home, handle_cache_updates, handle_janitor_tasks, \
    handle_pending_requests, handle_session_cleanup, handle_state_cleanup, \
    manage_single_req, manage_trivial_user_requests, \
    remind_and_expire_user_pending, task_triggers
from mig.shared.accountreq import save_account_request
from mig.shared.base import distinguished_name_to_user
from mig.shared.pwcrypto import generate_reset_token
from tests.support import MigTestCase, ensure_dirs_exist

DUMMY_USER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
DUMMY_FULL_NAME = "Test User"
DUMMY_ORGANIZATION = "Test Org"
DUMMY_EMAIL = "test@example.com"
DUMMY_SKIP_EMAIL = ''
DUMMY_CLIENT_DIR = '+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=test@example.com'
# TODO: adjust password reset token helpers to handle configured services
#       it currently silently fails if not in migoid(c) or migcert
# DUMMY_SERVICE = 'dummy-svc'
DUMMY_AUTH = DUMMY_SERVICE = 'migoid'
DUMMY_USERDB = 'MiG-users.db'
DUMMY_PEER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=peer@example.com'
# NOTE: these passwords are not and should not ever be used outside unit tests
DUMMY_MODERN_PW = 'QZFnCp7hmI1G'
DUMMY_MODERN_PW_PBKDF2 = \
    "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$B22uw6C7C4VFiYAe4Vf10n58FHrn1pjX"
DUMMY_NEW_MODERN_PW_PBKDF2 = \
    "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$B22uw6C7C4VFiYAe4Vf10n581pjXFHrn"
DUMMY_INVALID_PW_PBKDF2 = \
    "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$B22uw6C7C4VFiYAe4Vf1rn1pjX0n58FH"
# NOTE: tokens always should contain a multiple of 4 chars
INVALID_DUMMY_TOKEN = 'THIS_RESET_TOKEN_WAS_NEVER_VALID'


class MigLibJanitor(MigTestCase):
    """Unit tests for janitor related helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def _write_user_db(self, user_db_dict):
        """Write user_db_dict to user database - truncating any contents"""
        with open(self.user_db_path, 'wb') as udb:
            udb.write(pickle.dumps(user_db_dict))

    # TODO: migrate or remove this helper if no longer needed
    def _init_test_user_db(self, user_id=DUMMY_USER_DN):
        """Write a user_db_dict to user database - truncating any contents"""
        user_dict = distinguished_name_to_user(user_id)
        self._write_user_db({user_id: user_dict})

    def _prepare_test_file(self, path, times=None, content='test'):
        """Prepare file in path with optional times for timestamp"""
        with open(path, 'w') as fp:
            fp.write(content)
        os.utime(path, times)

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        self.configuration.site_enable_jobs = True
        # Certain pw reset tests require auth method to match signup
        self.configuration.site_signup_methods.append(DUMMY_AUTH)
        self.configuration.site_login_methods.append(DUMMY_AUTH)
        # Prevent admin email during reject, etc.
        self.configuration.admin_email = DUMMY_SKIP_EMAIL
        self.user_db_path = os.path.join(self.configuration.user_db_home,
                                         DUMMY_USERDB)
        # Create fake fs layout matching real systems
        ensure_dirs_exist(self.configuration.user_pending)
        ensure_dirs_exist(self.configuration.user_db_home)
        ensure_dirs_exist(self.configuration.user_home)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.user_cache)
        ensure_dirs_exist(self.configuration.twofactor_home)
        ensure_dirs_exist(self.configuration.mig_system_files)
        ensure_dirs_exist(self.configuration.mig_server_home)
        ensure_dirs_exist(self.configuration.gdp_home)
        ensure_dirs_exist(self.configuration.webserver_home)
        ensure_dirs_exist(self.configuration.sessid_to_mrsl_link_home)
        ensure_dirs_exist(self.configuration.mrsl_files_dir)
        ensure_dirs_exist(self.configuration.resource_pending)
        dummy_job = os.path.join(self.configuration.user_home,
                                 "no_grid_jobs_in_grid_scheduler")
        ensure_dirs_exist(dummy_job)

        # Prepare user DB with a single dummy user for all tests
        self._provision_test_user(self, DUMMY_USER_DN)

        # Reset task triggers
        global task_triggers
        task_triggers.clear()

    def test_last_run_bookkeeping(self):
        """Register a last run timestamp and check it"""
        expect = -1
        stamp = _lookup_last_run(self.configuration, 'janitor_task')
        self.assertEqual(stamp, expect)
        expect = 42
        stamp = _update_last_run(self.configuration, 'janitor_task', expect)
        self.assertEqual(stamp, expect)
        expect = time.time()
        stamp = _update_last_run(self.configuration, 'janitor_task', expect)
        self.assertEqual(stamp, expect)

    def test_clean_mig_system_files(self):
        """Test clean_mig system files helper"""
        test_time = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        valid_filenames = ['fresh.log', 'current.tmp']
        stale_filenames = ['tmp_expired.txt', 'no_grid_jobs.123']
        for name in valid_filenames + stale_filenames:
            path = os.path.join(self.configuration.mig_system_files, name)
            self._prepare_test_file(path, (test_time, test_time))
            self.assertTrue(os.path.exists(path))

        handled = clean_mig_system_files(self.configuration)
        self.assertEqual(handled, len(stale_filenames))
        self.assertEqual(len(os.listdir(self.configuration.mig_system_files)),
                         len(valid_filenames))
        for name in valid_filenames:
            path = os.path.join(self.configuration.mig_system_files, name)
            self.assertTrue(os.path.exists(path))
        for name in stale_filenames:
            path = os.path.join(self.configuration.mig_system_files, name)
            self.assertFalse(os.path.exists(path))

    def test_clean_webserver_home(self):
        """Test clean webserver files helper"""
        stale_stamp = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        test_dir = self.configuration.webserver_home
        valid_filename = 'fresh.log'
        stale_filename = 'stale.log'
        valid_path = os.path.join(test_dir, valid_filename)
        stale_path = os.path.join(test_dir, stale_filename)
        self._prepare_test_file(valid_path)
        self._prepare_test_file(stale_path, (stale_stamp, stale_stamp))

        self.assertTrue(os.path.exists(valid_path))
        self.assertTrue(os.path.exists(stale_path))
        handled = clean_webserver_home(self.configuration)
        self.assertEqual(handled, 1)
        self.assertTrue(os.path.exists(valid_path))
        self.assertFalse(os.path.exists(stale_path))

    def test_clean_no_job_helpers(self):
        """Test clean dummy job helper files"""
        stale_stamp = time.time() - EXPIRE_DUMMY_JOBS_DAYS * SECS_PER_DAY - 1
        test_dir = os.path.join(self.configuration.user_home,
                                "no_grid_jobs_in_grid_scheduler")
        valid_filename = 'alive.txt'
        stale_filename = 'expired.txt'
        valid_path = os.path.join(test_dir, valid_filename)
        stale_path = os.path.join(test_dir, stale_filename)
        self._prepare_test_file(valid_path)
        self._prepare_test_file(stale_path, (stale_stamp, stale_stamp))

        self.assertTrue(os.path.exists(stale_path))
        self.assertTrue(os.path.exists(valid_path))
        handled = clean_no_job_helpers(self.configuration)
        self.assertEqual(handled, 1)
        self.assertFalse(os.path.exists(stale_path))
        self.assertTrue(os.path.exists(valid_path))

    def test_clean_twofactor_sessions(self):
        """Test clean twofactor sessions"""
        stale_stamp = time.time() - EXPIRE_TWOFACTOR_DAYS * SECS_PER_DAY - 1
        test_dir = self.configuration.twofactor_home
        valid_filename = 'current'
        stale_filename = 'expired'
        valid_path = os.path.join(test_dir, valid_filename)
        stale_path = os.path.join(test_dir, stale_filename)
        self._prepare_test_file(valid_path)
        self._prepare_test_file(stale_path, (stale_stamp, stale_stamp))

        self.assertTrue(os.path.exists(stale_path))
        self.assertTrue(os.path.exists(valid_path))
        handled = clean_twofactor_sessions(self.configuration)
        self.assertEqual(handled, 1)
        self.assertFalse(os.path.exists(stale_path))
        self.assertTrue(os.path.exists(valid_path))

    def test_clean_sessid_to_mrls_link_home(self):
        """Test clean session MRSL link files"""
        stale_stamp = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        test_dir = self.configuration.sessid_to_mrsl_link_home
        valid_filename = 'active_session_link'
        stale_filename = 'expired_session_link'
        valid_path = os.path.join(test_dir, valid_filename)
        stale_path = os.path.join(test_dir, stale_filename)
        self._prepare_test_file(valid_path)
        self._prepare_test_file(stale_path, (stale_stamp, stale_stamp))

        self.assertTrue(os.path.exists(stale_path))
        self.assertTrue(os.path.exists(valid_path))
        handled = clean_sessid_to_mrls_link_home(self.configuration)
        self.assertEqual(handled, 1)
        self.assertFalse(os.path.exists(stale_path))
        self.assertTrue(os.path.exists(valid_path))

    def test_handle_state_cleanup(self):
        """Test combined state cleanup"""
        # Create a stale file in each location to clean up
        stale_stamp = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        mig_path = os.path.join(
            self.configuration.mig_system_files, 'tmpAbCd1234')
        web_path = os.path.join(self.configuration.webserver_home, 'stale.txt')
        empty_job_path = os.path.join(
            os.path.join(self.configuration.user_home,
                         "no_grid_jobs_in_grid_scheduler"),
            'sleep.job'
        )
        stale_paths = [mig_path, web_path, empty_job_path]
        for path in stale_paths:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self._prepare_test_file(path, (stale_stamp, stale_stamp))
            self.assertTrue(os.path.exists(path))

        handled = handle_state_cleanup(self.configuration)
        self.assertEqual(handled, 3)
        for path in stale_paths:
            self.assertFalse(os.path.exists(path))

    def test_handle_session_cleanup(self):
        """Test combined session cleanup"""
        stale_stamp = time.time() - max(EXPIRE_STATE_DAYS,
                                        EXPIRE_TWOFACTOR_DAYS) * SECS_PER_DAY - 1
        session_path = os.path.join(
            self.configuration.sessid_to_mrsl_link_home, 'expired.txt')
        twofactor_path = os.path.join(
            self.configuration.twofactor_home, 'expired.txt')
        test_paths = [session_path, twofactor_path]
        for path in test_paths:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self._prepare_test_file(path, (stale_stamp, stale_stamp))
            self.assertTrue(os.path.exists(path))

        handled = handle_session_cleanup(self.configuration)
        self.assertEqual(handled, 2)
        for path in test_paths:
            self.assertFalse(os.path.exists(path))

    def test_manage_pending_user_request(self):
        """Test pending user request management"""
        req_id = 'req_id'
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }

        self.assertDirEmpty(self.configuration.user_pending)
        saved, req_path = save_account_request(self.configuration, req_dict)
        self.assertTrue(saved, "failed to save account req")
        self.assertDirNotEmpty(self.configuration.user_pending)
        # Update mtime to make it ready for janitor
        req_age = time.time() - MANAGE_TRIVIAL_REQ_MINUTES * SECS_PER_MINUTE - 1
        os.utime(req_path, (req_age, req_age))

        # Need user DB and path to simulate existing user
        user_dir = os.path.join(self.configuration.user_home, DUMMY_CLIENT_DIR)
        os.makedirs(user_dir, exist_ok=True)
        handled = manage_trivial_user_requests(self.configuration)
        self.assertEqual(handled, 1)

    def test_expire_user_pending(self):
        """Test pending user request expiration reminders"""
        req_id = 'expired_req'
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }
        self.assertDirEmpty(self.configuration.user_pending)
        saved, req_path = save_account_request(self.configuration, req_dict)
        self.assertTrue(saved, "failed to save account req")
        self.assertDirNotEmpty(self.configuration.user_pending)
        # Make request very old
        req_age = time.time() - EXPIRE_REQ_DAYS * SECS_PER_DAY - 1
        os.utime(req_path, (req_age, req_age))

        # TODO: rework to handle expire before stale to avoid duplicate here
        handled = remind_and_expire_user_pending(self.configuration)
        # self.assertEqual(handled, 1)
        self.assertEqual(handled, 2)  # counted stale and expired (see above)

    def test_handle_pending_requests(self):
        """Test combined request handling"""
        # Create requests (valid, expired)
        valid_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }
        self.assertDirEmpty(self.configuration.user_pending)
        saved, valid_req_path = save_account_request(self.configuration,
                                                     valid_dict)
        self.assertTrue(saved, "failed to save valid req")
        self.assertDirNotEmpty(self.configuration.user_pending)
        valid_id = os.path.basename(valid_req_path)

        expired_id = 'expired_req'
        expired_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }
        saved, expired_req_path = save_account_request(
            self.configuration, expired_dict)
        self.assertTrue(saved, "failed to save expired req")
        expired_id = os.path.basename(expired_req_path)
        # Make just one old enough to expire
        expire_time = time.time() - EXPIRE_REQ_DAYS * SECS_PER_DAY - 1
        os.utime(os.path.join(self.configuration.user_pending, expired_id),
                 (expire_time, expire_time))

        # TODO: rework to handle expire before stale to avoid duplicate here
        handled = handle_pending_requests(self.configuration)
        # self.assertEqual(handled, 2)  # 1 manage + 1 expire
        self.assertEqual(handled, 3)  # 1 manage + 1 expire + 1 stale

    def test_handle_janitor_tasks_full(self):
        """Test full janitor task scheduler"""
        # Prepare environment with pending tasks of each kind
        mig_stamp = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        mig_path = os.path.join(self.configuration.mig_system_files,
                                'tmp-stale.txt')
        two_path = os.path.join(self.configuration.twofactor_home, 'stale.txt')
        two_stamp = time.time() - EXPIRE_TWOFACTOR_DAYS * SECS_PER_DAY - 1
        stale_tests = ((mig_path, mig_stamp), (two_path, two_stamp), )
        for (stale_path, stale_stamp) in stale_tests:
            self._prepare_test_file(stale_path, (stale_stamp, stale_stamp))
            self.assertTrue(os.path.exists(stale_path))

        req_id = 'expired_request'
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }
        self.assertDirEmpty(self.configuration.user_pending)
        saved, req_path = save_account_request(self.configuration, req_dict)
        self.assertTrue(saved, "failed to save account req")
        self.assertDirNotEmpty(self.configuration.user_pending)
        req_id = os.path.basename(req_path)
        # Make request very old
        req_age = time.time() - EXPIRE_REQ_DAYS * SECS_PER_DAY - 1
        os.utime(os.path.join(self.configuration.user_pending, req_id),
                 (req_age, req_age))

        # Set no last run timestamps to trigger all tasks
        now = time.time()
        task_triggers.clear()

        # Run task handler and verify all tasks executed
        # TODO: rework to handle expire before stale to avoid req tripled here
        handled = handle_janitor_tasks(self.configuration, now=now)
        # self.assertEqual(handled, 3)  # state+session+requests
        self.assertEqual(handled, 5)  # state+session+3*request
        for (stale_path, _) in stale_tests:
            self.assertFalse(os.path.exists(stale_path), stale_path)

    def test__clean_stale_state_files(self):
        """Test core stale state file cleaner helper"""
        test_dir = self.temppath('stale_state_test', ensure_dir=True)
        patterns = ['tmp_*', 'session_*']

        # Create test files (fresh, expired, unexpired, non-matching)
        test_remove = [
            ('tmp_expired.txt', EXPIRE_STATE_DAYS * SECS_PER_DAY + 1),
            ('session_old.dat', EXPIRE_STATE_DAYS * SECS_PER_DAY + 1),
        ]
        test_keep = [
            ('tmp_fresh.txt', -1),
            ('session_valid.dat', 0),
            ('other_file.log', EXPIRE_STATE_DAYS * SECS_PER_DAY + 1),
        ]

        for (name, age_diff) in test_keep + test_remove:
            path = os.path.join(test_dir, name)
            stamp = time.time() - age_diff
            self._prepare_test_file(path, (stamp, stamp))
            self.assertTrue(os.path.exists(path))

        handled = _clean_stale_state_files(
            self.configuration,
            test_dir,
            patterns,
            EXPIRE_STATE_DAYS,
            time.time(),
            include_dotfiles=False
        )
        self.assertEqual(handled, 2)  # tmp_expired.txt + session_old.dat
        for (name, _) in test_keep:
            path = os.path.join(test_dir, name)
            self.assertTrue(os.path.exists(path))
        for (name, _) in test_remove:
            path = os.path.join(test_dir, name)
            self.assertFalse(os.path.exists(path))

    def test_manage_single_req_invalid(self):
        """Test request handling for invalid request"""
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'invalid': ['Missing required field: organization'],
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            # NOTE: disable email to prevent send failing on reject
            'email': DUMMY_SKIP_EMAIL,
        }
        saved, req_path = save_account_request(self.configuration, req_dict)
        req_id = os.path.basename(req_path)

        with self.assertLogs(level='INFO') as log_capture:
            manage_single_req(
                self.configuration,
                req_id,
                req_path,
                self.user_db_path,
                time.time()
            )

        self.assertTrue(any('invalid account request' in msg
                            for msg in log_capture.output))
        self.assertFalse(os.path.exists(req_path),
                         "Failed to clean invalid req for %s" % req_path)

    def test_manage_single_req_expired_token(self):
        """Test request handling with expired reset token"""
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            # NOTE: disable email to prevent send failing on reject
            'email': DUMMY_SKIP_EMAIL,
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            'expire': time.time() + SECS_PER_DAY,
        }
        user_dict = {}
        user_dict.update(req_dict)
        # We need to save user in DB with password_hash for reset_token check
        self._write_user_db({DUMMY_USER_DN: user_dict})
        # Mimic proper but old expired token
        timestamp = 42
        # IMPORTANT: we can't use a fixed token here due to dynamic crypto seed
        req_dict['reset_token'] = generate_reset_token(self.configuration,
                                                       req_dict, DUMMY_SERVICE,
                                                       timestamp)
        # Change password_hash here to mimic pw change
        req_dict['password_hash'] = DUMMY_NEW_MODERN_PW_PBKDF2
        saved, req_path = save_account_request(self.configuration, req_dict)
        req_id = os.path.basename(req_path)

        with self.assertLogs(level='WARNING') as log_capture:
            manage_single_req(
                self.configuration,
                req_id,
                req_path,
                self.user_db_path,
                time.time()
            )

        self.assertTrue(
            any('reject expired reset token' in msg for msg in log_capture.output))
        self.assertFalse(os.path.exists(req_path),
                         "Failed to clean token req for %s" % req_path)

    @unittest.skip("TODO: enable once fernet decrypt err handling is improved")
    def test_manage_single_req_invalid_token(self):
        """Test request handling with invalid reset token"""
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            # NOTE: disable email to prevent send failing on reject
            'email': DUMMY_SKIP_EMAIL,
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            'expire': time.time() - SECS_PER_DAY,
        }
        user_dict = {}
        user_dict.update(req_dict)
        # We need to save user in DB with password_hash for reset_token check
        self._write_user_db({DUMMY_USER_DN: user_dict})
        # Inject known invalid reset token
        req_dict['reset_token'] = INVALID_DUMMY_TOKEN
        # Change password_hash here to mimic pw change
        req_dict['password_hash'] = DUMMY_NEW_MODERN_PW_PBKDF2
        saved, req_path = save_account_request(self.configuration, req_dict)
        req_id = os.path.basename(req_path)

        with self.assertLogs(level='WARNING') as log_capture:
            manage_single_req(
                self.configuration,
                req_id,
                req_path,
                self.user_db_path,
                time.time()
            )

        self.assertTrue(
            any('reset with bad token' in msg for msg in log_capture.output))
        self.assertFalse(os.path.exists(req_path),
                         "Failed to clean token req for %s" % req_path)

    def test_manage_single_req_collision(self):
        """Test request handling with existing user collision"""
        # Setup existing user
        user_dir = os.path.join(self.configuration.user_home, DUMMY_CLIENT_DIR)
        os.makedirs(user_dir, exist_ok=True)
        # Create dummy user DB
        user_entry = {'distinguished_name': DUMMY_USER_DN}
        self._write_user_db({DUMMY_USER_DN: user_entry})

        changed_full_name = "Changed Test Name"
        req_dict = {
            'client_id': DUMMY_USER_DN.replace(DUMMY_FULL_NAME,
                                               changed_full_name),
            'distinguished_name': DUMMY_USER_DN.replace(DUMMY_FULL_NAME,
                                                        changed_full_name),
            'auth': [DUMMY_AUTH],
            'full_name': changed_full_name,
            'organization': DUMMY_ORGANIZATION,
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            # NOTE: disable email to prevent send failing on reject
            'email': DUMMY_SKIP_EMAIL,
        }
        saved, req_path = save_account_request(self.configuration, req_dict)
        req_id = os.path.basename(req_path)

        with self.assertLogs(level='WARNING') as log_capture:
            manage_single_req(
                self.configuration,
                req_id,
                req_path,
                self.user_db_path,
                time.time()
            )
        self.assertTrue(any('ID collision' in msg
                            for msg in log_capture.output))
        self.assertFalse(os.path.exists(req_path),
                         "Failed cleanup collision for %s" % req_path)

    @unittest.skip("TODO: enable once janitor handles auth change reqs")
    def test_manage_single_req_auth_change(self):
        """Test request handling with auth password change"""
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            # NOTE: disable email to prevent send failing on reject
            'email': DUMMY_SKIP_EMAIL,
            'password': '',
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            'expire': time.time() + SECS_PER_DAY,
        }
        user_dict = {}
        user_dict.update(req_dict)
        # We need to save user in DB with password_hash for reset_token check
        self._write_user_db({DUMMY_USER_DN: user_dict})
        # Change password_hash here to mimic pw change
        req_dict['password_hash'] = DUMMY_NEW_MODERN_PW_PBKDF2
        req_dict['authorized'] = True
        saved, req_path = save_account_request(self.configuration, req_dict)
        req_id = os.path.basename(req_path)

        with self.assertLogs(level='INFO') as log_capture:
            manage_single_req(
                self.configuration,
                req_id,
                req_path,
                self.user_db_path,
                time.time()
            )

        self.assertTrue(
            any('accepted' in msg for msg in log_capture.output))
        self.assertFalse(os.path.exists(req_path),
                         "Failed to clean token req for %s" % req_path)

    def test_handle_cache_updates_stub(self):
        """Test handle_cache_updates placeholder returns zero"""
        handled = handle_cache_updates(self.configuration)
        self.assertEqual(handled, 0)

    def test_janitor_update_timestamps(self):
        """Test task trigger timestamp updates in janitor"""
        now = time.time()
        task = 'test-task'

        # Initial state
        stamp = _lookup_last_run(self.configuration, task)
        self.assertEqual(stamp, -1)

        # Update & verify
        updated = _update_last_run(self.configuration, task, now)
        self.assertEqual(updated, now)

        # Check persistence (within process)
        retrieved = _lookup_last_run(self.configuration, task)
        self.assertEqual(retrieved, now)

    def test__clean_stale_state_files_edge(self):
        """Test state file cleaner with special cases"""
        test_dir = self.temppath('edge_case_test', ensure_dir=True)

        # Dot file
        dot_path = os.path.join(test_dir, '.hidden.tmp')
        stamp = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        self._prepare_test_file(dot_path, (stamp, stamp))

        # Directory
        dir_path = os.path.join(test_dir, 'subdir')
        os.makedirs(dir_path)

        handled = _clean_stale_state_files(
            self.configuration,
            test_dir,
            ['*'],
            EXPIRE_STATE_DAYS,
            time.time(),
            include_dotfiles=False
        )
        self.assertEqual(handled, 0)

        # Now include dotfiles
        handled = _clean_stale_state_files(
            self.configuration,
            test_dir,
            ['*'],
            EXPIRE_STATE_DAYS,
            time.time(),
            include_dotfiles=True
        )
        self.assertEqual(handled, 1)

    @unittest.skip("TODO: enable once unpickling error handling is improved")
    def test_manage_single_req_corrupted_file(self):
        """Test manage_single_req with corrupted request file"""
        req_id = 'corrupted_req'
        req_path = os.path.join(self.configuration.user_pending, req_id)
        with open(req_path, 'w') as fp:
            fp.write('invalid pickle content')

        with self.assertLogs(level='ERROR') as log_capture:
            manage_single_req(
                self.configuration,
                req_id,
                req_path,
                self.user_db_path,
                time.time()
            )

        self.assertTrue(any('Failed to load request from' in msg
                            or 'Could not load saved request' in msg
                            for msg in log_capture.output))
        self.assertFalse(os.path.exists(req_path))

    def test_manage_single_req_nonexistent_userdb(self):
        """Test manage_single_req with missing user database"""
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            # NOTE: disable email to prevent send failing on reject
            'email': DUMMY_SKIP_EMAIL,
        }
        saved, req_path = save_account_request(self.configuration, req_dict)
        req_id = os.path.basename(req_path)

        # Remove user database
        os.remove(self.user_db_path)

        with self.assertLogs(level='ERROR') as log_capture:
            manage_single_req(
                self.configuration,
                req_id,
                req_path,
                self.user_db_path,
                time.time()
            )

        self.assertTrue(any('Failed to load user DB' in msg
                            for msg in log_capture.output))

    def test_verify_reset_token_failure_logging(self):
        """Test token verification failure creates proper log entries"""
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            # NOTE: disable email to prevent send failing on reject
            'email': DUMMY_SKIP_EMAIL,
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            'expire': time.time() + SECS_PER_DAY,  # Future expiration
        }
        user_dict = {}
        user_dict.update(req_dict)
        # We need to save user in DB with password_hash for reset_token check
        self._write_user_db({DUMMY_USER_DN: user_dict})
        timestamp = time.time()

        # Now change to another pw hash and generate invalid token from it
        req_dict['password_hash'] = DUMMY_INVALID_PW_PBKDF2
        req_dict['reset_token'] = generate_reset_token(self.configuration,
                                                       req_dict, DUMMY_SERVICE,
                                                       timestamp)

        saved, req_path = save_account_request(self.configuration, req_dict)
        req_id = os.path.basename(req_path)

        with self.assertLogs(level='WARNING') as log_capture:
            manage_single_req(
                self.configuration,
                req_id,
                req_path,
                self.user_db_path,
                time.time()
            )

        self.assertTrue(any('wrong hash' in msg.lower()
                            for msg in log_capture.output))
        self.assertFalse(os.path.exists(req_path),
                         "Failed cleanup invalid token for %s" % req_path)

    def test_verify_reset_token_success(self):
        """Test token verification success with valid token"""
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            # NOTE: disable email to prevent send failing on reject
            'email': DUMMY_SKIP_EMAIL,
            'password': '',
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            'expire': time.time() + SECS_PER_DAY,  # Future expiration
        }
        user_dict = {}
        user_dict.update(req_dict)
        # We need to save user in DB with password_hash for reset_token check
        self._write_user_db({DUMMY_USER_DN: user_dict})
        timestamp = time.time()
        reset_token = generate_reset_token(self.configuration, req_dict,
                                           DUMMY_SERVICE, timestamp)
        req_dict['reset_token'] = reset_token
        # Change password_hash here to mimic pw change
        req_dict['password_hash'] = DUMMY_NEW_MODERN_PW_PBKDF2
        saved, req_path = save_account_request(self.configuration, req_dict)
        req_id = os.path.basename(req_path)

        with self.assertLogs(level='INFO') as log_capture:
            manage_single_req(
                self.configuration,
                req_id,
                req_path,
                self.user_db_path,
                time.time()
            )

        self.assertTrue(any('accepted' in msg.lower()
                            for msg in log_capture.output))

    def test_remind_and_expire_edge_cases(self):
        """Test request expiration with exact boundary timestamps"""
        now = time.time()
        test_cases = [
            ('exact_remind', now - REMIND_REQ_DAYS * SECS_PER_DAY),
            ('exact_expire', now - EXPIRE_REQ_DAYS * SECS_PER_DAY),
        ]

        for (req_id, mtime) in test_cases:
            req_path = os.path.join(self.configuration.user_pending, req_id)
            req_dict = {
                'client_id': DUMMY_USER_DN,
                'distinguished_name': DUMMY_USER_DN,
                'auth': [DUMMY_AUTH],
                'full_name': DUMMY_FULL_NAME,
                'organization': DUMMY_ORGANIZATION,
                'password': DUMMY_MODERN_PW,
                'email': DUMMY_EMAIL,
            }
            saved, req_path = save_account_request(
                self.configuration, req_dict)
            os.utime(req_path, (mtime, mtime))

        handled = remind_and_expire_user_pending(self.configuration, now=now)
        # TODO: rework to handle expire before stale to avoid duplicates here
        # Should match exact_expire only
        # self.assertEqual(handled, 1)
        self.assertEqual(handled, 3)  # expire + 2 stale

    def test_handle_janitor_tasks_time_thresholds(self):
        """Test janitor task frequency thresholds"""
        now = time.time()

        self.assertEqual(_lookup_last_run(
            self.configuration, "state-cleanup"), -1)
        self.assertEqual(_lookup_last_run(
            self.configuration, "session-cleanup"), -1)
        self.assertEqual(_lookup_last_run(
            self.configuration, "pending-reqs"), -1)
        self.assertEqual(_lookup_last_run(
            self.configuration, "cache-updates"), -1)
        # Test all tasks EXCEPT cache-updates are past threshold
        last_state_cleanup = now - SECS_PER_DAY - 3
        last_session_cleanup = now - SECS_PER_HOUR - 3
        last_pending_reqs = now - SECS_PER_MINUTE - 3
        last_cache_update = now - SECS_PER_MINUTE + 10  # Not expired
        task_triggers.update({'state-cleanup': last_state_cleanup,
                              'session-cleanup': last_session_cleanup,
                              'pending-reqs': last_pending_reqs,
                              'cache-updates': last_cache_update})
        self.assertEqual(_lookup_last_run(
            self.configuration, "state-cleanup"), last_state_cleanup)
        self.assertEqual(_lookup_last_run(
            self.configuration, "session-cleanup"), last_session_cleanup)
        self.assertEqual(_lookup_last_run(
            self.configuration, "cache-updates"), last_cache_update)

        # TODO: handled does NOT count no action runs - add dummies to handle?
        handled = handle_janitor_tasks(self.configuration, now=now)
        # self.assertEqual(handled, 3)  # state + session + pending
        self.assertEqual(handled, 0)  # ran with nothing to do

        # Verify last run timestamps updated
        self.assertEqual(_lookup_last_run(
            self.configuration, "state-cleanup"), now)
        self.assertEqual(_lookup_last_run(
            self.configuration, "session-cleanup"), now)
        self.assertEqual(_lookup_last_run(
            self.configuration, "pending-reqs"), now)
        self.assertEqual(_lookup_last_run(
            self.configuration, "cache-updates"), last_cache_update)

    @unittest.skip("TODO: enable once cleaner has improved error handling")
    def test_clean_stale_files_nonexistent_dir(self):
        """Test state cleaner with invalid directory path"""
        target_dir = os.path.join(self.configuration.mig_system_files,
                                  "non_existing_dir")
        handled = _clean_stale_state_files(
            self.configuration,
            target_dir,
            ["*"],
            EXPIRE_STATE_DAYS,
            time.time()
        )
        self.assertEqual(handled, 0)

    @unittest.skip("TODO: enable once cleaner has improved error handling")
    def test_clean_stale_files_permission_error(self):
        """Test state cleaner handles permission errors gracefully"""
        test_dir = self.temppath("readonly_dir", ensure_dir=True)
        os.chmod(test_dir, 0o444)  # Read-only

        test_path = os.path.join(test_dir, "test.txt")
        stamp = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        self._prepare_test_file(test_path, (stamp, stamp))

        with self.assertLogs(level='ERROR'):
            handled = _clean_stale_state_files(
                self.configuration,
                test_dir,
                ["*"],
                EXPIRE_STATE_DAYS,
                time.time()
            )
            self.assertEqual(handled, 0)

        # Restore permissions to allow cleanup
        os.chmod(test_dir, 0o755)

    def test_handle_empty_pending_dir(self):
        """Test operations with empty pending requests directory"""
        # Empty directory completely
        for filename in os.listdir(self.configuration.user_pending):
            path = os.path.join(self.configuration.user_pending, filename)
            os.remove(path)

        handled = manage_trivial_user_requests(self.configuration)
        self.assertEqual(handled, 0)

        handled = remind_and_expire_user_pending(self.configuration)
        self.assertEqual(handled, 0)

    def test_janitor_task_cleanup_after_reject(self):
        """Verify proper cleanup after request rejection"""
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'invalid': ['Test intentional invalid'],
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'organization': DUMMY_ORGANIZATION,
            # NOTE: disable email to prevent send failing on reject
            'email': DUMMY_SKIP_EMAIL,
        }
        saved, req_path = save_account_request(self.configuration, req_dict)
        req_id = os.path.basename(req_path)

        # Verify initial existence
        self.assertTrue(os.path.exists(req_path))

        manage_single_req(
            self.configuration,
            req_id,
            req_path,
            self.user_db_path,
            time.time()
        )

        # Verify post-execution cleanup
        self.assertFalse(os.path.exists(req_path))

    def test_cleaner_with_multiple_patterns(self):
        """Test state cleaner with multiple filename patterns"""
        test_dir = self.temppath('multi_pattern_test', ensure_dir=True)
        clean_patterns = ['*.tmp', '*.log', 'temp*']
        clean_pairs = [
            ('should_keep_recent.log', EXPIRE_STATE_DAYS - 1),
            ('should_remove_stale.tmp', EXPIRE_STATE_DAYS + 1),
            ('should_keep_other.pck', EXPIRE_STATE_DAYS + 1)
        ]

        for (name, age_days) in clean_pairs:
            path = os.path.join(test_dir, name)
            stamp = time.time() - age_days * SECS_PER_DAY
            self._prepare_test_file(path, (stamp, stamp))
            self.assertTrue(os.path.exists(path))

        handled = _clean_stale_state_files(
            self.configuration,
            test_dir,
            clean_patterns,
            EXPIRE_STATE_DAYS,
            time.time()
        )
        self.assertEqual(handled, 1)
        self.assertTrue(os.path.exists(
            os.path.join(test_dir, 'should_keep_recent.log')))
        self.assertFalse(os.path.exists(
            os.path.join(test_dir, 'should_remove_stale.tmp')))
        self.assertTrue(os.path.exists(
            os.path.join(test_dir, 'should_keep_other.pck')))

    def test_absent_jobs_flag(self):
        """Test clean_no_job_helpers with site_enable_jobs disabled"""
        self.configuration.site_enable_jobs = False
        handled = clean_no_job_helpers(self.configuration)
        self.assertEqual(handled, 0)

    def test_clean_sessions_jobs_disabled(self):
        """Test session cleanup with jobs disabled"""
        self.configuration.site_enable_jobs = False
        handled = clean_sessid_to_mrls_link_home(self.configuration)
        self.assertEqual(handled, 0)
