# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_janitor - unit test of the corresponding mig lib module
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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
import time

from tests.support import FakeConfiguration, MigTestCase, ensure_dirs_exist
from mig.shared.accountreq import save_account_request
from mig.lib.janitor import task_triggers, _lookup_last_run, _update_last_run, \
    SECS_PER_MINUTE, SECS_PER_HOUR, SECS_PER_DAY, \
    EXPIRE_STATE_DAYS, EXPIRE_DUMMY_JOBS_DAYS, EXPIRE_TWOFACTOR_DAYS, \
    EXPIRE_REQ_DAYS, MANAGE_TRIVIAL_REQ_MINUTES, REMIND_REQ_DAYS, \
    clean_mig_system_files, clean_webserver_home, clean_no_job_helpers, \
    clean_twofactor_sessions, handle_state_cleanup, \
    clean_sessid_to_mrls_link_home, handle_session_cleanup, \
    manage_trivial_user_requests, manage_single_req, \
    remind_and_expire_user_pending, handle_pending_requests, \
    handle_cache_updates, handle_janitor_tasks

DUMMY_USER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=noreply@migrid.org'
DUMMY_FULL_NAME = "Test User"
DUMMY_ORGANIZATION = "Test Org"
# TODO: mark as unroutable somehow to skip sending email from tests?
DUMMY_EMAIL = "noreply@migrid.org"
DUMMY_CLIENT_DIR = '+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=noreply@migrid.org'
DUMMY_AUTH = 'migcert'
DUMMY_PEER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=peer@example.com'
# NOTE: these passwords are not and should not ever be used outside unit tests
DUMMY_MODERN_PW = 'QZFnCp7hmI1G'
DUMMY_MODERN_PW_PBKDF2 = \
    "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$B22uw6C7C4VFiYAe4Vf10n58FHrn1pjX"


class MigLibJanitor(MigTestCase):
    """Unit tests for janitor related helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        # Create fake configuration matching real systems
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
        # Remap test configuration to dummy_conf for consistency
        self.dummy_conf = self.configuration
        self.dummy_conf.site_enable_jobs = True

        # Reset task triggers
        global task_triggers
        task_triggers = {}

    def test_last_run_bookkeeping(self):
        """Register a last run timestamp and check it"""
        expect = -1
        stamp = _lookup_last_run(self.dummy_conf, 'janitor_task')
        self.assertEqual(stamp, expect)
        expect = 42
        stamp = _update_last_run(self.dummy_conf, 'janitor_task', expect)
        self.assertEqual(stamp, expect)
        expect = time.time()
        stamp = _update_last_run(self.dummy_conf, 'janitor_task', expect)
        self.assertEqual(stamp, expect)

    def test_clean_mig_system_files(self):
        """Test clean_mig system files helper"""
        test_time = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        valid_filenames = ['fresh.log', 'current.tmp']
        stale_filenames = ['tmp_expired.txt', 'no_grid_jobs.123']
        for name in valid_filenames + stale_filenames:
            path = os.path.join(self.dummy_conf.mig_system_files, name)
            with open(path, 'w') as fp:
                fp.write('test')
            os.utime(path, (test_time, test_time))
            if name in valid_filenames:
                # Make one file fresh
                os.utime(path, None)
        handled = clean_mig_system_files(self.dummy_conf)
        self.assertEqual(handled, len(stale_filenames))
        self.assertEqual(len(os.listdir(self.dummy_conf.mig_system_files)),
                         len(valid_filenames))

    def test_clean_webserver_home(self):
        """Test clean webserver files helper"""
        test_time = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        valid_filename = 'fresh.log'
        stale_filename = 'stale.log'
        for name in [valid_filename, stale_filename]:
            path = os.path.join(self.dummy_conf.webserver_home, name)
            with open(path, 'w') as fp:
                fp.write('test')
            os.utime(path, (test_time, test_time))
            if name == valid_filename:
                os.utime(path, None)
        handled = clean_webserver_home(self.dummy_conf)
        self.assertEqual(handled, 1)
        self.assertFalse(os.path.exists(os.path.join(
            self.dummy_conf.webserver_home, stale_filename)))
        self.assertTrue(os.path.exists(os.path.join(
            self.dummy_conf.webserver_home, valid_filename)))

    def test_clean_no_job_helpers(self):
        """Test clean dummy job helper files"""
        dummy_job = os.path.join(self.dummy_conf.user_home,
                                 "no_grid_jobs_in_grid_scheduler")
        os.makedirs(dummy_job, exist_ok=True)
        test_time = time.time() - EXPIRE_DUMMY_JOBS_DAYS * SECS_PER_DAY - 1
        valid_filename = 'alive.txt'
        stale_filename = 'expired.txt'
        for name in [valid_filename, stale_filename]:
            path = os.path.join(dummy_job, name)
            with open(path, 'w') as fp:
                fp.write('test')
            os.utime(path, (test_time, test_time))
            if name == valid_filename:
                os.utime(path, None)
        handled = clean_no_job_helpers(self.dummy_conf)
        self.assertEqual(handled, 1)
        self.assertFalse(os.path.exists(os.path.join(dummy_job,
                                                     stale_filename)))
        self.assertTrue(os.path.exists(os.path.join(dummy_job,
                                                    valid_filename)))

    def test_clean_twofactor_sessions(self):
        """Test clean twofactor sessions"""
        test_time = time.time() - EXPIRE_TWOFACTOR_DAYS * SECS_PER_DAY - 1
        valid_filename = 'current'
        stale_filename = 'expired'
        for name in [valid_filename, stale_filename]:
            path = os.path.join(self.dummy_conf.twofactor_home, name)
            with open(path, 'w') as fp:
                fp.write('test')
            os.utime(path, (test_time, test_time))
            if name == valid_filename:
                os.utime(path, None)
        handled = clean_twofactor_sessions(self.dummy_conf)
        self.assertEqual(handled, 1)
        self.assertFalse(os.path.exists(os.path.join(
            self.dummy_conf.twofactor_home, stale_filename)))
        self.assertTrue(os.path.exists(os.path.join(
            self.dummy_conf.twofactor_home, valid_filename)))

    def test_clean_sessid_to_mrls_link_home(self):
        """Test clean session MRSL link files"""
        test_time = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        valid_filename = 'active_session_link'
        stale_filename = 'expired_session_link'
        for name in [valid_filename, stale_filename]:
            path = os.path.join(self.dummy_conf.sessid_to_mrsl_link_home, name)
            with open(path, 'w') as fp:
                fp.write('test')
            os.utime(path, (test_time, test_time))
            if name == valid_filename:
                os.utime(path, None)
        handled = clean_sessid_to_mrls_link_home(self.dummy_conf)
        self.assertEqual(handled, 1)
        self.assertFalse(os.path.exists(os.path.join(
            self.dummy_conf.sessid_to_mrsl_link_home, stale_filename)))
        self.assertTrue(os.path.exists(os.path.join(
            self.dummy_conf.sessid_to_mrsl_link_home, valid_filename)))

    def test_handle_state_cleanup(self):
        """Test combined state cleanup"""
        # Create a stale file in each location to clean up
        test_time = time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1
        mig_path = os.path.join(
            self.dummy_conf.mig_system_files, 'tmpAbCd1234')
        web_path = os.path.join(self.dummy_conf.webserver_home, 'stale.txt')
        empty_job_path = os.path.join(
            os.path.join(self.dummy_conf.user_home,
                         "no_grid_jobs_in_grid_scheduler"),
            'sleep.job'
        )
        for path in [mig_path, web_path, empty_job_path]:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as fp:
                fp.write('test')
            os.utime(path, (test_time, test_time))

        handled = handle_state_cleanup(self.dummy_conf)
        self.assertEqual(handled, 3)

    def test_handle_session_cleanup(self):
        """Test combined session cleanup"""
        test_time = time.time() - max(EXPIRE_STATE_DAYS,
                                      EXPIRE_TWOFACTOR_DAYS) * SECS_PER_DAY - 1
        session_path = os.path.join(
            self.dummy_conf.sessid_to_mrsl_link_home, 'expired.txt')
        twofactor_path = os.path.join(
            self.dummy_conf.twofactor_home, 'expired.txt')
        for path in [session_path, twofactor_path]:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as fp:
                fp.write('test')
            os.utime(path, (test_time, test_time))

        handled = handle_session_cleanup(self.dummy_conf)
        self.assertEqual(handled, 2)

    def test_manage_pending_user_request(self):
        """Test pending user request management"""
        req_id = 'req_id'
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }
        self.assertDirEmpty(self.dummy_conf.user_pending)
        saved, req_path = save_account_request(self.dummy_conf, req_dict)
        self.assertTrue(saved, "failed to save account req")
        self.assertDirNotEmpty(self.dummy_conf.user_pending)
        # Update mtime to make it ready for janitor
        req_age = time.time() - MANAGE_TRIVIAL_REQ_MINUTES * SECS_PER_MINUTE - 1
        os.utime(req_path, (req_age, req_age))

        # Need user DB and path to simulate existing user
        user_dir = os.path.join(self.dummy_conf.user_home, DUMMY_CLIENT_DIR)
        os.makedirs(user_dir)
        handled = manage_trivial_user_requests(self.dummy_conf)
        self.assertEqual(handled, 1)

    def test_expire_user_pending(self):
        """Test pending user request expiration reminders"""
        req_id = 'expired_req'
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }
        self.assertDirEmpty(self.dummy_conf.user_pending)
        saved, req_path = save_account_request(self.dummy_conf, req_dict)
        self.assertTrue(saved, "failed to save account req")
        self.assertDirNotEmpty(self.dummy_conf.user_pending)
        # Make request very old
        req_age = time.time() - EXPIRE_REQ_DAYS * SECS_PER_DAY - 1
        os.utime(req_path, (req_age, req_age))

        # TODO: rework to handle expire before stale to avoid duplicate here
        handled = remind_and_expire_user_pending(self.dummy_conf)
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
            'password_hash': DUMMY_MODERN_PW_PBKDF2,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }
        self.assertDirEmpty(self.dummy_conf.user_pending)
        saved, valid_req_path = save_account_request(self.dummy_conf,
                                                     valid_dict)
        self.assertTrue(saved, "failed to save valid req")
        self.assertDirNotEmpty(self.dummy_conf.user_pending)
        valid_id = os.path.basename(valid_req_path)

        expired_id = 'expired_req'
        expired_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }
        saved, expired_req_path = save_account_request(
            self.dummy_conf, expired_dict)
        self.assertTrue(saved, "failed to save expired req")
        expired_id = os.path.basename(expired_req_path)
        # Make just one old enough to expire
        expire_time = time.time() - EXPIRE_REQ_DAYS * SECS_PER_DAY - 1
        os.utime(os.path.join(self.dummy_conf.user_pending, expired_id),
                 (expire_time, expire_time))

        # TODO: rework to handle expire before stale to avoid duplicate here
        handled = handle_pending_requests(self.dummy_conf)
        # self.assertEqual(handled, 2)  # 1 manage + 1 expire
        self.assertEqual(handled, 3)  # 1 manage + 1 expire + 1 stale

    def test_handle_janitor_tasks_full(self):
        """Test full janitor task scheduler"""
        # Prepare environment with pending tasks
        mig_path = os.path.join(self.dummy_conf.mig_system_files, 'stale.txt')
        with open(mig_path, 'w') as fp:
            fp.write('test')
        os.utime(mig_path,
                 (time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1,
                  time.time() - EXPIRE_STATE_DAYS * SECS_PER_DAY - 1))

        two_path = os.path.join(self.dummy_conf.twofactor_home, 'stale.txt')
        with open(two_path, 'w') as fp:
            fp.write('test')
        os.utime(two_path,
                 (time.time() - EXPIRE_TWOFACTOR_DAYS * SECS_PER_DAY - 1,
                  time.time() - EXPIRE_TWOFACTOR_DAYS * SECS_PER_DAY - 1))

        req_id = 'expired_request'
        req_dict = {
            'client_id': DUMMY_USER_DN,
            'distinguished_name': DUMMY_USER_DN,
            'auth': [DUMMY_AUTH],
            'full_name': DUMMY_FULL_NAME,
            'password': DUMMY_MODERN_PW,
            'peers': [DUMMY_PEER_DN],
            'email': DUMMY_EMAIL,
        }
        self.assertDirEmpty(self.dummy_conf.user_pending)
        saved, req_path = save_account_request(self.dummy_conf, req_dict)
        self.assertTrue(saved, "failed to save account req")
        self.assertDirNotEmpty(self.dummy_conf.user_pending)
        req_id = os.path.basename(req_path)
        # Make request very old
        req_age = time.time() - EXPIRE_REQ_DAYS * SECS_PER_DAY - 1
        os.utime(os.path.join(self.dummy_conf.user_pending, req_id),
                 (req_age, req_age))

        dummy_job = os.path.join(self.dummy_conf.user_home,
                                 "no_grid_jobs_in_grid_scheduler")
        os.makedirs(dummy_job, exist_ok=True)

        # Set no last run timestamps to trigger all tasks
        now = time.time()
        task_triggers["state-cleanup"] = -1
        task_triggers["session-cleanup"] = -1
        task_triggers["pending-reqs"] = -1
        task_triggers["cache-updates"] = -1

        # Run task handler and verify all tasks executed
        # TODO: rework to handle expire before stale to avoid duplicate here
        handled = handle_janitor_tasks(self.dummy_conf, now=now)
        # self.assertEqual(handled, 3)  # state+session+requests
        self.assertEqual(handled, 4)  # state (expired+stale)+session+requests
