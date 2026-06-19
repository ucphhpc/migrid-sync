# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_accountstate - unit test of the corresponding mig shared module
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

"""Unit tests for the mig shared accountstate module"""

import os
import time
import unittest

# Imports of the code under test
from mig.shared.accountstate import (
    account_expire_info,
    check_account_accessible,
    check_account_expire,
    check_account_status,
    check_update_account_expire,
    default_account_expire,
    default_account_valid_days,
    detect_special_login,
    get_account_expire_cache,
    get_account_status_cache,
    reset_account_expire_cache,
    update_account_expire_cache,
    update_account_status_cache,
)

# Imports required for the unit test wrapping
from mig.shared.base import client_id_dir
from mig.shared.defaults import (
    AUTH_CERTIFICATE,
    AUTH_GENERIC,
    AUTH_OPENID_CONNECT,
    AUTH_OPENID_V2,
    cert_auto_extend_days,
    expire_marks_dir,
    oid_auto_extend_days,
    oidc_auto_extend_days,
    status_marks_dir,
)
from mig.shared.useradm import _ensure_dirs_needed_for_userdb
from mig.shared.userdb import load_user_dict, update_user_dict

# Imports required for the unit tests themselves
from tests.support import (
    MigTestCase,
    UserAssertMixin,
    ensure_dirs_exist,
    testmain,
)
from tests.support.usersupp import OTHER_USER_DN, TEST_USER_DN

# Test constants
TEST_EXPIRE_TIMESTAMP = 1776031200
TEST_STATUS_ACTIVE = "active"
TEST_STATUS_LOCKED = "locked"
TEST_STATUS_SUSPENDED = "suspended"
TEST_STATUS_TEMPORAL = "temporal"
TEST_RW_SHARE_ID = "klmnop4567"
TEST_JOB_ID = "0419b45ebc1dedbdcb91fa6251035a2096758f5d700e15478b27a90734454107"
TEST_JUPYTER_SESSION_ID = (
    "ohNo4ii9geeyei3Jai8aif6gae6Eebiechai3chegh0moo9NieveKu3AC8ooshuo"
)
TEST_USER_EMAIL = TEST_USER_DN.split("/emailAddress=", 1)[-1]
TEST_USER_DIR = client_id_dir(TEST_USER_DN)
OTHER_USER_DIR = client_id_dir(OTHER_USER_DN)


class TestMigSharedAccountstate__default_account_valid_days(MigTestCase):
    """Coverage of accountstate default_account_valid_days function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

    def test_default_account_valid_days_auth_cert(self):
        """Test that cert_valid_days is returned for AUTH_CERTIFICATE."""
        configuration = self.configuration

        result = default_account_valid_days(configuration, AUTH_CERTIFICATE)
        self.assertEqual(result, 365)

    def test_default_account_valid_days_auth_oid(self):
        """Test that oid_valid_days is returned for AUTH_OPENID_V2."""
        configuration = self.configuration

        result = default_account_valid_days(configuration, AUTH_OPENID_V2)
        self.assertEqual(result, 30)

    def test_default_account_valid_days_auth_oidc(self):
        """Test that oidc_valid_days is returned for AUTH_OPENID_CONNECT."""
        configuration = self.configuration

        result = default_account_valid_days(configuration, AUTH_OPENID_CONNECT)
        self.assertEqual(result, 30)

    def test_default_account_valid_days_auth_generic(self):
        """Test that generic_valid_days is returned for AUTH_GENERIC."""
        configuration = self.configuration

        result = default_account_valid_days(configuration, AUTH_GENERIC)
        self.assertEqual(result, 14)

    def test_default_account_valid_days_auth_unknown(self):
        """Test that generic_valid_days is fallback for unknown auth type."""
        configuration = self.configuration

        result = default_account_valid_days(configuration, "UNKNOWN_AUTH_TYPE")
        self.assertEqual(result, 14)


class TestMigSharedAccountstate__default_account_expire(MigTestCase):
    """Coverage of accountstate default_account_expire function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

    def test_default_account_expire_for_auth_cert(self):
        """Test expire calculation for AUTH_CERTIFICATE."""
        configuration = self.configuration

        start_time = time.time()
        result = default_account_expire(
            configuration, AUTH_CERTIFICATE, start_time=start_time
        )
        expected = int(start_time + 365 * 24 * 60 * 60)
        self.assertEqual(result, expected)

    def test_default_account_expire_for_auth_oid(self):
        """Test expire calculation for AUTH_OPENID_V2."""
        configuration = self.configuration

        start_time = time.time()
        result = default_account_expire(
            configuration, AUTH_OPENID_V2, start_time=start_time
        )
        expected = int(start_time + 30 * 24 * 60 * 60)
        self.assertEqual(result, expected)

    def test_default_account_expire_for_auth_oidc(self):
        """Test expire calculation for AUTH_OPENID_CONNECT."""
        configuration = self.configuration

        start_time = time.time()
        result = default_account_expire(
            configuration, AUTH_OPENID_CONNECT, start_time=start_time
        )
        expected = int(start_time + 30 * 24 * 60 * 60)
        self.assertEqual(result, expected)

    def test_default_account_expire_for_auth_generic(self):
        """Test expire calculation for AUTH_GENERIC."""
        configuration = self.configuration

        start_time = time.time()
        result = default_account_expire(
            configuration, AUTH_GENERIC, start_time=start_time
        )
        expected = int(start_time + 14 * 24 * 60 * 60)
        self.assertEqual(result, expected)

    def test_default_account_expire_without_start_time(self):
        """Test that current time is used when start_time is not provided."""
        configuration = self.configuration

        before = int(time.time())
        result = default_account_expire(configuration, AUTH_CERTIFICATE)
        after = int(time.time())

        # Result should be between before + 364 days and after + 365 days
        min_expected = before + 364 * 24 * 60 * 60
        max_expected = after + 365 * 24 * 60 * 60
        self.assertTrue(min_expected <= result <= max_expected)


class TestMigSharedAccountstate__update_account_expire_cache(MigTestCase):
    """Coverage of accountstate update_account_expire_cache function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for expire cache tests."""
        configuration = self.configuration
        # Ensure necessary directories exist
        ensure_dirs_exist(configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, expire_marks_dir)
        )

    def test_update_account_expire_cache_creates_mark(self):
        """Test that update_account_expire_cache creates an expire mark."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": TEST_EXPIRE_TIMESTAMP,
        }

        result = update_account_expire_cache(configuration, user_dict)
        self.assertTrue(result)

        # Verify the mark was created
        cached_expire = get_account_expire_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_expire, TEST_EXPIRE_TIMESTAMP)

    def test_update_account_expire_cache_with_missing_client_id(self):
        """Test that update fails gracefully when client_id is missing."""
        configuration = self.configuration
        user_dict = {
            "expire": TEST_EXPIRE_TIMESTAMP,
        }

        with self.assertLogs(level="ERROR") as log_capture:
            result = update_account_expire_cache(configuration, user_dict)
            self.assertFalse(result)
        self.assertTrue(
            any("no client ID" in msg for msg in log_capture.output)
        )

    def test_update_account_expire_cache_with_missing_expire(self):
        """Test that update returns True when expire is missing."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
        }

        with self.assertLogs(level="INFO") as log_capture:
            result = update_account_expire_cache(configuration, user_dict)
            self.assertTrue(result)
        self.assertTrue(
            any("no expire set" in msg for msg in log_capture.output)
        )

    def test_update_account_expire_cache_with_string_expire(self):
        """Test that update fails when expire is a string."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": "not_a_number",
        }

        with self.assertLogs(level="WARNING") as log_capture:
            result = update_account_expire_cache(configuration, user_dict)
            self.assertFalse(result)
        self.assertTrue(
            any("string expire value" in msg for msg in log_capture.output)
        )

    def test_update_account_expire_cache_with_delete(self):
        """Test that delete=True removes the expire mark."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": TEST_EXPIRE_TIMESTAMP,
        }

        # First create the mark
        update_account_expire_cache(configuration, user_dict)
        cached_expire = get_account_expire_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_expire, TEST_EXPIRE_TIMESTAMP)

        # Then delete it
        result = update_account_expire_cache(
            configuration, user_dict, delete=True
        )
        self.assertTrue(result)

        # Verify the mark was removed
        cached_expire = get_account_expire_cache(configuration, TEST_USER_DN)
        self.assertIsNone(cached_expire)

    def test_update_account_expire_cache_with_invalid_user_dict(self):
        """Test that update fails when user_dict is not a dictionary."""
        configuration = self.configuration

        with self.assertLogs(level="ERROR") as log_capture:
            result = update_account_expire_cache(configuration, "not_a_dict")
            self.assertFalse(result)
        self.assertTrue(
            any("invalid user_dict" in msg for msg in log_capture.output)
        )


class TestMigSharedAccountstate__get_account_expire_cache(MigTestCase):
    """Coverage of accountstate get_account_expire_cache function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for expire cache tests."""
        configuration = self.configuration
        # Ensure necessary directories exist
        ensure_dirs_exist(configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, expire_marks_dir)
        )

    def test_get_account_expire_cache_returns_cached_value(self):
        """Test that get_account_expire_cache returns cached expire value."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": TEST_EXPIRE_TIMESTAMP,
        }

        # Create the mark first
        update_account_expire_cache(configuration, user_dict)

        # Then retrieve it
        result = get_account_expire_cache(configuration, TEST_USER_DN)
        self.assertEqual(result, TEST_EXPIRE_TIMESTAMP)

    def test_get_account_expire_cache_with_missing_client_id(self):
        """Test that get fails gracefully when client_id is missing."""
        configuration = self.configuration

        with self.assertLogs(level="ERROR") as log_capture:
            result = get_account_expire_cache(configuration, "")
            self.assertFalse(result)
        self.assertTrue(
            any("invalid client ID" in msg for msg in log_capture.output)
        )


class TestMigSharedAccountstate__reset_account_expire_cache(MigTestCase):
    """Coverage of accountstate reset_account_expire_cache function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for expire cache tests."""
        configuration = self.configuration
        # Ensure necessary directories exist
        ensure_dirs_exist(configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, expire_marks_dir)
        )
        self.expire_base = os.path.join(
            configuration.mig_system_run, expire_marks_dir
        )

    def test_reset_account_expire_cache_resets_all_marks(self):
        """Test that reset_account_expire_cache resets all expire marks."""
        configuration = self.configuration
        # Create a couple of marks first
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": TEST_EXPIRE_TIMESTAMP,
        }
        update_account_expire_cache(configuration, user_dict)
        cached_expire = get_account_expire_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_expire, TEST_EXPIRE_TIMESTAMP)
        user_dict = {
            "distinguished_name": OTHER_USER_DN,
            "expire": TEST_EXPIRE_TIMESTAMP + 42,
        }
        update_account_expire_cache(configuration, user_dict)
        cached_expire = get_account_expire_cache(configuration, OTHER_USER_DN)
        self.assertEqual(cached_expire, TEST_EXPIRE_TIMESTAMP + 42)

        # Then reset all
        result = reset_account_expire_cache(configuration)
        self.assertTrue(result)

        # Verify all marks were reset but not removed
        marks_path = os.path.join(self.expire_base, TEST_USER_DIR)
        self.assertTrue(os.path.exists(marks_path))
        cached_expire = get_account_expire_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_expire, 0.0)
        marks_path = os.path.join(self.expire_base, OTHER_USER_DIR)
        self.assertTrue(os.path.exists(marks_path))
        cached_expire = get_account_expire_cache(configuration, OTHER_USER_DN)
        self.assertEqual(cached_expire, 0.0)

    def test_reset_account_expire_cache_resets_specific_mark(self):
        """Test that reset_account_expire_cache resets given expire mark."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": TEST_EXPIRE_TIMESTAMP,
        }

        marks_path = os.path.join(self.expire_base, TEST_USER_DIR)
        # Create the mark first
        update_account_expire_cache(configuration, user_dict)
        self.assertTrue(os.path.exists(marks_path))
        cached_expire = get_account_expire_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_expire, TEST_EXPIRE_TIMESTAMP)

        # Then reset it
        result = reset_account_expire_cache(configuration, TEST_USER_DN)
        self.assertTrue(result)

        # Verify the mark was reset but not removed
        self.assertTrue(os.path.exists(marks_path))
        cached_expire = get_account_expire_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_expire, 0.0)


class TestMigSharedAccountstate__update_account_status_cache(MigTestCase):
    """Coverage of accountstate update_account_status_cache function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for status cache tests."""
        configuration = self.configuration
        # Ensure necessary directories exist
        ensure_dirs_exist(configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, status_marks_dir)
        )

    def test_update_account_status_cache_creates_mark(self):
        """Test that update_account_status_cache creates a status mark."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": TEST_STATUS_ACTIVE,
        }

        result = update_account_status_cache(configuration, user_dict)
        self.assertTrue(result)

        # Verify the mark was created
        cached_status = get_account_status_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_status, TEST_STATUS_ACTIVE)

    def test_update_account_status_cache_with_different_status(self):
        """Test that update_account_status_cache handles different status values."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": TEST_STATUS_LOCKED,
        }

        result = update_account_status_cache(configuration, user_dict)
        self.assertTrue(result)

        # Verify the mark was created with correct status
        cached_status = get_account_status_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_status, TEST_STATUS_LOCKED)

    def test_update_account_status_cache_with_missing_client_id(self):
        """Test that update fails gracefully when client_id is missing."""
        configuration = self.configuration
        user_dict = {
            "status": TEST_STATUS_ACTIVE,
        }

        with self.assertLogs(level="ERROR") as log_capture:
            result = update_account_status_cache(configuration, user_dict)
            self.assertFalse(result)
        self.assertTrue(
            any("no client ID" in msg for msg in log_capture.output)
        )

    def test_update_account_status_cache_with_missing_status(self):
        """Test that update returns True when status is missing."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
        }

        with self.assertLogs(level="INFO") as log_capture:
            result = update_account_status_cache(configuration, user_dict)
            self.assertTrue(result)
        self.assertTrue(
            any("no status set" in msg for msg in log_capture.output)
        )

    def test_update_account_status_cache_with_invalid_status(self):
        """Test that update fails when status is invalid."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "invalid_status",
        }

        with self.assertLogs(level="ERROR") as log_capture:
            result = update_account_status_cache(configuration, user_dict)
            self.assertFalse(result)
        self.assertTrue(
            any("invalid account status" in msg for msg in log_capture.output)
        )

    def test_update_account_status_cache_with_delete(self):
        """Test that delete=True removes the status mark."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": TEST_STATUS_ACTIVE,
        }

        # First create the mark
        update_account_status_cache(configuration, user_dict)
        cached_status = get_account_status_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_status, TEST_STATUS_ACTIVE)

        # Then delete it
        result = update_account_status_cache(
            configuration, user_dict, delete=True
        )
        self.assertTrue(result)

        # Verify the mark was removed
        cached_status = get_account_status_cache(configuration, TEST_USER_DN)
        self.assertIsNone(cached_status)

    def test_update_account_status_cache_with_invalid_user_dict(self):
        """Test that update fails when user_dict is not a dictionary."""
        configuration = self.configuration

        with self.assertLogs(level="ERROR") as log_capture:
            result = update_account_status_cache(configuration, "not_a_dict")
            self.assertFalse(result)
        self.assertTrue(
            any("invalid user_dict" in msg for msg in log_capture.output)
        )


class TestMigSharedAccountstate__get_account_status_cache(MigTestCase):
    """Coverage of accountstate get_account_status_cache function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for status cache tests."""
        configuration = self.configuration
        # Ensure necessary directories exist
        ensure_dirs_exist(configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, status_marks_dir)
        )

    def test_get_account_status_cache_returns_cached_value(self):
        """Test that get_account_status_cache returns cached status value."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": TEST_STATUS_ACTIVE,
        }

        # Create the mark first
        update_account_status_cache(configuration, user_dict)

        # Then retrieve it
        result = get_account_status_cache(configuration, TEST_USER_DN)
        self.assertEqual(result, TEST_STATUS_ACTIVE)

    def test_get_account_status_cache_with_missing_client_id(self):
        """Test that get fails gracefully when client_id is missing."""
        configuration = self.configuration

        with self.assertLogs(level="ERROR") as log_capture:
            result = get_account_status_cache(configuration, "")
            self.assertFalse(result)
        self.assertTrue(
            any("invalid client ID" in msg for msg in log_capture.output)
        )

    def test_get_account_status_cache_returns_none_when_not_set(self):
        """Test that get_account_status_cache returns None when status not set."""
        configuration = self.configuration

        result = get_account_status_cache(configuration, TEST_USER_DN)
        self.assertIsNone(result)


class TestMigSharedAccountstate__check_account_expire(MigTestCase):
    """Coverage of accountstate check_account_expire function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for check_account_expire."""
        configuration = self.configuration
        # Ensure necessary directories exist
        ensure_dirs_exist(configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, expire_marks_dir)
        )
        # Set up user DB and keep paths for later use
        _ensure_dirs_needed_for_userdb(configuration)
        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        self._provision_test_user(self, TEST_USER_DN)

    def test_check_account_expire_expired(self):
        """Test that check_account_expire returns False for an expired account."""
        configuration = self.configuration
        logger = self.logger
        # Expired account
        account_expire = time.time() - 400 * 24 * 3600
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": account_expire,
        }
        # Update expire and delete cache for user
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict, delete=True)
        pending, expire, _ = check_account_expire(configuration, TEST_USER_DN)
        self.assertFalse(pending)
        self.assertEqual(expire, account_expire)

    def test_check_account_expire_active(self):
        """Test that check_account_expire returns expire pending for an active account."""
        configuration = self.configuration
        logger = self.logger
        # Active account
        account_expire = time.time() + 42 * 24 * 3600
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": account_expire,
        }
        # Update expire and cache for user
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        pending, expire, _ = check_account_expire(configuration, TEST_USER_DN)
        self.assertTrue(pending)
        self.assertEqual(expire, account_expire)

    @unittest.skip("TODO: init account without expire value and enable test?")
    def test_check_account_expire_no_expire_field(self):
        """Test that check_account_expire returns expire pending if expire is missing."""
        configuration = self.configuration
        logger = self.logger
        user_dict = {
            "distinguished_name": TEST_USER_DN,
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict, delete=True)
        pending, expire, _ = check_account_expire(configuration, TEST_USER_DN)
        self.assertTrue(pending)
        self.assertEqual(expire, -1)

    def test_check_account_expire_invalid_expire_type(self):
        """Test that check_account_expire returns expired if expire is not a valid number."""
        configuration = self.configuration
        logger = self.logger
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            # Example invalid values that will pass assertions
            "expire": "invalid",
            # "expire": "-41"
            # "expire": "-41.2"
            # "expire": "11111111111111141.2"
            #
            # Example valid values that will fail assertions
            # "expire": "4242"
            # "expire": 4242
            # "expire": -41.2
            # "expire": 11111111111111141.2
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        # Make sure cache doesn't interfere with type parsing
        reset_account_expire_cache(configuration)
        # Use expected error values to trigger asserts if assertRaises doesn't
        pending, expire = False, -42
        # Make sure function under test either fails with TypeError or returns
        # values indicating failure to prevent further login use.
        with self.assertRaises(TypeError):
            pending, expire, _ = check_account_expire(
                configuration, TEST_USER_DN
            )
        self.assertFalse(pending, "got expected TypeError but not expired")
        self.assertEqual(
            expire, -42, "got expected TypeError but unexpected expire time"
        )

    def test_check_account_expire_no_user_db_entry(self):
        """Test that check_account_expire returns expired if user is not in the DB."""
        configuration = self.configuration
        with self.assertLogs(level="ERROR") as log_capture:
            pending, expire, _ = check_account_expire(
                configuration, "nosuchuser"
            )
            self.assertFalse(pending)
            self.assertEqual(expire, -42)
        self.assertTrue(
            any("no such account:" in msg for msg in log_capture.output)
        )

    def test_check_account_expire_with_cache_miss(self):
        """Test that check_account_expire updates the cache if not cached."""
        configuration = self.configuration
        logger = self.logger
        # Active account
        account_expire = time.time() + 42 * 24 * 3600
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": account_expire,
        }
        # Update user and delete cache
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict, delete=True)
        pending, expire, _ = check_account_expire(configuration, TEST_USER_DN)
        self.assertTrue(pending)
        self.assertEqual(expire, account_expire)
        cached_expire = get_account_expire_cache(configuration, TEST_USER_DN)
        self.assertEqual(cached_expire, account_expire)

    @unittest.skip("TODO: init account without expire value and enable test?")
    def test_check_account_expire_with_current_time(self):
        """Test that check_account_expire uses current time if expire is not set."""
        configuration = self.configuration
        logger = self.logger
        user_dict = {
            "distinguished_name": TEST_USER_DN,
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        pending, expire, _ = check_account_expire(configuration, TEST_USER_DN)
        now = time.time()
        self.assertTrue(pending)
        self.assertTrue(expire <= now - 3)

    def test_check_account_expire_with_expired_account_and_cache(self):
        """Test that check_account_expire works if the account is expired and cached."""
        configuration = self.configuration
        logger = self.logger
        account_expire = time.time() - 400 * 24 * 3600
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": account_expire,
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        pending, expire, _ = check_account_expire(configuration, TEST_USER_DN)
        self.assertFalse(pending)
        self.assertEqual(expire, account_expire)


class TestMigSharedAccountstate__account_expire_info(MigTestCase):
    """Coverage of accountstate account_expire_info function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for account_expire_info."""
        configuration = self.configuration
        # Ensure necessary directories exist
        ensure_dirs_exist(configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, expire_marks_dir)
        )
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, status_marks_dir)
        )
        # Set up user DB and keep paths for later use
        _ensure_dirs_needed_for_userdb(configuration)
        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        self._provision_test_user(self, TEST_USER_DN)

        # Set up configuration for auto-renew tests
        configuration.auto_add_oid_user = True
        configuration.auto_add_oidc_user = True
        configuration.auto_add_cert_user = True
        configuration.site_user_id_format = "X509"  # Default format

    def test_account_expire_info_about_to_expire_cert(self):
        """Test account_expire_info for certificate user about to expire."""
        configuration = self.configuration
        logger = self.logger
        # Set expire to be within min_days_left (14 days)
        expect_expire = time.time() + (10 * 24 * 3600)  # 10 days from now
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": expect_expire,
            "status": "active",
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "some agent",
        }
        base_url = "https://cert.example.com"
        configuration.migserver_https_ext_cert_url = base_url
        environ["SCRIPT_URI"] = "%s/wsgi-bin/something.py" % base_url

        expire_warn, account_expire, renew_days, extend_days = (
            account_expire_info(
                configuration, TEST_USER_DN, environ, min_days_left=14
            )
        )
        self.assertTrue(expire_warn)
        self.assertEqual(account_expire, expect_expire)
        self.assertEqual(renew_days, configuration.cert_valid_days)
        self.assertEqual(extend_days, cert_auto_extend_days)

    def test_account_expire_info_about_to_expire_oid(self):
        """Test account_expire_info for OID user about to expire."""
        configuration = self.configuration
        logger = self.logger
        # Set expire to be within min_days_left (14 days)
        expect_expire = time.time() + (10 * 24 * 3600)  # 10 days from now
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": expect_expire,
            "status": "active",
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        # Simulate OID login environment
        environ = {
            "REMOTE_ADDR": "127.0.0.1",  # Not localhost to allow renew
            "HTTP_USER_AGENT": "some agent",
        }
        base_url = "https://oid.example.com"
        configuration.migserver_https_ext_oid_url = base_url
        environ["SCRIPT_URI"] = "%s/wsgi-bin/something.py" % base_url

        expire_warn, account_expire, renew_days, extend_days = (
            account_expire_info(
                configuration, TEST_USER_DN, environ, min_days_left=14
            )
        )
        self.assertTrue(expire_warn)
        self.assertEqual(account_expire, expect_expire)
        self.assertEqual(renew_days, configuration.oid_valid_days)
        self.assertEqual(extend_days, oid_auto_extend_days)

    def test_account_expire_info_about_to_expire_oidc(self):
        """Test account_expire_info for OIDC user about to expire."""
        configuration = self.configuration
        logger = self.logger
        # Set expire to be within min_days_left (14 days)
        expect_expire = time.time() + (10 * 24 * 3600)  # 10 days from now
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": expect_expire,
            "status": "active",
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        # Simulate OIDC login environment
        environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "some agent",
        }
        base_url = "https://oidc.example.com"
        configuration.migserver_https_ext_oidc_url = base_url
        environ["SCRIPT_URI"] = "%s/wsgi-bin/something.py" % base_url

        expire_warn, account_expire, renew_days, extend_days = (
            account_expire_info(
                configuration, TEST_USER_DN, environ, min_days_left=14
            )
        )
        self.assertTrue(expire_warn)
        self.assertEqual(account_expire, expect_expire)
        self.assertEqual(renew_days, configuration.oidc_valid_days)
        self.assertEqual(extend_days, oidc_auto_extend_days)

    def test_account_expire_info_not_about_to_expire(self):
        """Test account_expire_info for user not about to expire."""
        configuration = self.configuration
        logger = self.logger
        # Set expire to be beyond min_days_left (14 days)
        expect_expire = time.time() + (20 * 24 * 3600)  # 20 days from now
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": expect_expire,
            "status": "active",
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "some agent",
        }
        base_url = "https://oidc.example.com"
        configuration.migserver_https_ext_oidc_url = base_url
        environ["SCRIPT_URI"] = "%s/wsgi-bin/something.py" % base_url

        expire_warn, account_expire, renew_days, extend_days = (
            account_expire_info(
                configuration, TEST_USER_DN, environ, min_days_left=14
            )
        )
        self.assertFalse(expire_warn)
        self.assertEqual(account_expire, expect_expire)
        self.assertEqual(renew_days, 0)
        self.assertEqual(extend_days, 0)

    def test_account_expire_info_about_to_expire_oid_no_auto_renew(self):
        """Test account_expire_info for OID user about to expire but auto-renew disabled."""
        configuration = self.configuration
        logger = self.logger
        # Set expire to be within min_days_left (14 days)
        expect_expire = time.time() + (10 * 24 * 3600)  # 10 days from now
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": expect_expire,
            "status": "active",
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        # Disable auto-renew for OID
        configuration.auto_add_oid_user = False

        environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "some agent",
        }
        base_url = "https://oid.example.com"
        configuration.migserver_https_ext_oid_url = base_url
        environ["SCRIPT_URI"] = "%s/wsgi-bin/something.py" % base_url

        expire_warn, account_expire, renew_days, extend_days = (
            account_expire_info(
                configuration, TEST_USER_DN, environ, min_days_left=14
            )
        )
        self.assertTrue(expire_warn)
        self.assertEqual(account_expire, expect_expire)
        self.assertEqual(renew_days, configuration.oid_valid_days)
        self.assertEqual(extend_days, 0)  # Because auto-renew is disabled

    def test_account_expire_info_with_different_min_days_left(self):
        """Test account_expire_info with a custom min_days_left."""
        configuration = self.configuration
        logger = self.logger
        # Set expire to be 10 days from now
        expect_expire = time.time() + (10 * 24 * 3600)
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": expect_expire,
            "status": "active",
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "some agent",
        }
        base_url = "https://oidc.example.com"
        configuration.migserver_https_ext_oidc_url = base_url
        environ["SCRIPT_URI"] = "%s/wsgi-bin/something.py" % base_url

        # Test with min_days_left=7 (so 10 days is beyond 7 -> not about to expire)
        expire_warn, account_expire, renew_days, extend_days = (
            account_expire_info(
                configuration, TEST_USER_DN, environ, min_days_left=7
            )
        )
        self.assertFalse(expire_warn)
        self.assertEqual(account_expire, expect_expire)
        self.assertEqual(renew_days, 0)
        self.assertEqual(extend_days, 0)

        # Test with min_days_left=15 (so 10 days is within 15 -> about to expire)
        expire_warn, account_expire, renew_days, extend_days = (
            account_expire_info(
                configuration, TEST_USER_DN, environ, min_days_left=15
            )
        )
        self.assertTrue(expire_warn)
        self.assertEqual(account_expire, expect_expire)
        self.assertEqual(renew_days, configuration.oidc_valid_days)
        self.assertEqual(extend_days, oidc_auto_extend_days)


class TestMigSharedAccountstate__detect_special_login(MigTestCase):
    """Coverage of accountstate detect_special_login function."""

    def _provide_configuration(self):
        """Return a minimal configuration object for the test."""
        return "testconfig"

    def before_each(self):
        """Create the directories that the function may touch."""
        configuration = self.configuration
        configuration.site_enable_sharelinks = True
        configuration.site_enable_jobs = True
        configuration.site_enable_jupyter = True
        # Ensure the home directories that the function may reference exist
        ensure_dirs_exist(configuration.user_home)
        ensure_dirs_exist(configuration.mrsl_files_dir)
        ensure_dirs_exist(configuration.resource_pending)
        ensure_dirs_exist(configuration.sessid_to_mrsl_link_home)
        ensure_dirs_exist(configuration.sessid_to_jupyter_mount_link_home)
        self._provision_test_user(self, TEST_USER_DN)

    def test_special_login_sharelink_is_detected(self):
        """Test that a sharelink ID is recognised as a special login."""
        configuration = self.configuration
        # Create a dummy RW sharelink to user home
        sharelink_path = os.path.join(
            configuration.sharelink_home, "read-write", TEST_RW_SHARE_ID
        )
        sharelink_target = os.path.join(configuration.user_home, TEST_USER_DIR)
        ensure_dirs_exist(sharelink_target)
        ensure_dirs_exist(os.path.dirname(sharelink_path))
        os.symlink(sharelink_target, sharelink_path)

        # Call the function – it should return True for this special login
        result = detect_special_login(configuration, TEST_RW_SHARE_ID, "sftp")
        self.assertTrue(result)

    def test_special_login_job_is_detected(self):
        """Test that a job ID is recognised as a special login."""
        configuration = self.configuration
        # Create a dummy job link to mrsl files entry
        job_target_path = os.path.join(
            configuration.mrsl_files_dir, TEST_JOB_ID
        )
        ensure_dirs_exist(job_target_path)
        job_link_path = os.path.join(
            configuration.sessid_to_mrsl_link_home, TEST_JOB_ID + ".mRSL"
        )
        ensure_dirs_exist(os.path.dirname(job_link_path))
        os.symlink(job_target_path, job_link_path)

        result = detect_special_login(configuration, TEST_JOB_ID, "sftp")
        self.assertTrue(result)

    def test_special_login_jupyter_mount_is_detected(self):
        """Test that a jupyter‑mount ID is recognised as a special login."""
        configuration = self.configuration
        # Create a dummy jupyter‑mount link to user home
        jupyter_link_path = os.path.join(
            configuration.sessid_to_jupyter_mount_link_home,
            TEST_JUPYTER_SESSION_ID,
        )
        jupyter_target = os.path.join(configuration.user_home, TEST_USER_DIR)
        ensure_dirs_exist(jupyter_target)
        ensure_dirs_exist(os.path.dirname(jupyter_link_path))
        os.symlink(jupyter_target, jupyter_link_path)

        result = detect_special_login(
            configuration, TEST_JUPYTER_SESSION_ID, "sftp"
        )
        self.assertTrue(result)

    def test_special_login_normal_user_is_not_detected(self):
        """Test that a normal user DN is *not* recognised as a special login."""
        configuration = self.configuration
        result = detect_special_login(configuration, TEST_USER_EMAIL, "sftp")
        self.assertFalse(result)

    def test_special_login_without_proto_is_not_detected(self):
        """Test that a value without a recognised protocol is not detected."""
        configuration = self.configuration
        result = detect_special_login(configuration, TEST_USER_EMAIL, "")
        self.assertFalse(result)

    def test_special_login_with_unknown_proto_is_not_detected(self):
        """Test that an unknown protocol string is not detected."""
        configuration = self.configuration
        result = detect_special_login(
            configuration, TEST_USER_EMAIL, "unknown-proto"
        )
        self.assertFalse(result)

    def test_special_login_with_empty_user_is_not_detected(self):
        """Test that an empty user string is not detected."""
        configuration = self.configuration
        result = detect_special_login(configuration, "", "sftp")
        self.assertFalse(result)


class TestMigSharedAccountstate__check_account_status(
    MigTestCase, UserAssertMixin
):
    """Coverage of accountstate check_account_status function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for check_account_status tests."""
        configuration = self.configuration
        # Ensure necessary directories exist
        ensure_dirs_exist(self.configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, expire_marks_dir)
        )
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, status_marks_dir)
        )
        # Set up user DB and keep paths for later use
        _ensure_dirs_needed_for_userdb(configuration)
        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        # Provision a known test user
        self._provision_test_user(self, TEST_USER_DN)

    def test_check_account_status_active(self):
        """Test that an active account is reported as accessible."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
        }
        # Create a DB entry for the user
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        # Populate the status cache
        update_account_status_cache(configuration, user_dict)

        accessible, status, _ = check_account_status(
            configuration, TEST_USER_DN
        )
        self.assertTrue(accessible)
        self.assertEqual(status, "active")

    def test_check_account_status_locked(self):
        """Test that a locked account is reported as not accessible."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": TEST_STATUS_LOCKED,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_status_cache(configuration, user_dict)

        accessible, status, _ = check_account_status(
            configuration, TEST_USER_DN
        )
        self.assertFalse(accessible)
        self.assertEqual(status, TEST_STATUS_LOCKED)

    def test_check_account_status_suspended(self):
        """Test that a suspended account is reported as not accessible."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": TEST_STATUS_SUSPENDED,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_status_cache(configuration, user_dict)

        accessible, status, _ = check_account_status(
            configuration, TEST_USER_DN
        )
        self.assertFalse(accessible)
        self.assertEqual(status, TEST_STATUS_SUSPENDED)

    def test_check_account_status_unset_means_active(self):
        """Test that an account without status is active and accessible."""
        configuration = self.configuration
        expire_ts = time.time() + 42 * 24 * 3600  # expired in 42 days
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": expire_ts,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_status_cache(configuration, user_dict)

        accessible, status, _ = check_account_status(
            configuration, TEST_USER_DN
        )
        self.assertTrue(accessible)
        self.assertEqual(status, "active")

    def test_check_account_status_unchanged_by_expire(self):
        """Test that account status itself remains unchanged after expire."""
        configuration = self.configuration
        expire_ts = time.time() - 42 * 24 * 3600  # expired 42 days ago
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
            "expire": expire_ts,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_status_cache(configuration, user_dict)

        accessible, status, _ = check_account_status(
            configuration, TEST_USER_DN
        )
        self.assertTrue(accessible)
        self.assertEqual(status, "active")

    def test_check_account_status_missing_user(self):
        """Test that check_account_status fails gracefully for a missing user."""
        configuration = self.configuration
        with self.assertLogs(level="WARNING") as log_capture:
            accessible, _, _ = check_account_status(
                configuration, OTHER_USER_DN
            )
            self.assertFalse(accessible)
        self.assertTrue(
            any("no such account" in msg for msg in log_capture.output)
        )


class TestMigSharedAccountstate__check_account_accessible(
    MigTestCase, UserAssertMixin
):
    """Coverage of accountstate check_account_accessible function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for check_account_accessible tests."""
        configuration = self.configuration
        configuration.site_enable_sharelinks = True
        configuration.site_enable_jobs = True
        configuration.site_enable_jupyter = True
        # Ensure necessary directories exist
        ensure_dirs_exist(configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, expire_marks_dir)
        )
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, status_marks_dir)
        )
        # Set up user DB and keep paths for later use
        _ensure_dirs_needed_for_userdb(configuration)
        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        # Provision a known test user
        self._provision_test_user(self, TEST_USER_DN)
        # This simulates an existing short id link to X509 in user_home
        short_id_link_in_home = os.path.join(
            configuration.user_home, TEST_USER_EMAIL
        )
        os.symlink(TEST_USER_DIR, short_id_link_in_home)

    def test_check_account_accessible_active_user_web_access(self):
        """Test that an active user is accessible via web (non-IO)."""
        configuration = self.configuration
        # Ensure the user is active and not expired
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
            "expire": time.time() + 42 * 24 * 3600,  # far future
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_DN, "oidc", io_login=False
        )
        self.assertTrue(accessible)

    def test_check_account_accessible_active_user_io_access(self):
        """Test that an active user is accessible via SFTP (IO)."""
        configuration = self.configuration
        # Ensure the user is active and not expired
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
            "expire": time.time() + 42 * 24 * 3600,  # far future
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_DN, "sftp"
        )
        self.assertTrue(accessible)

    def test_check_account_accessible_active_user_web_access_on_email_alias(
        self,
    ):
        """Test that an active user is accessible via web (non-IO) using email alias."""
        configuration = self.configuration
        # Ensure the user is active and not expired
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
            "expire": time.time() + 42 * 24 * 3600,  # far future
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_EMAIL, "oidc", io_login=False
        )
        self.assertTrue(accessible)

    def test_check_account_accessible_active_user_sftp_access_on_email_alias(
        self,
    ):
        """Test that an active user is accessible via SFTP using email alias."""
        configuration = self.configuration
        # Ensure the user is active and not expired
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
            "expire": time.time() + 42 * 24 * 3600,  # far future
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_EMAIL, "sftp"
        )
        self.assertTrue(accessible)

    def test_check_account_accessible_locked_user_web_blocked(self):
        """Test that a locked user is not accessible on web (non-IO)."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": TEST_STATUS_LOCKED,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_DN, "oidc", io_login=False
        )
        self.assertFalse(accessible)

    def test_check_account_accessible_locked_user_io_blocked(self):
        """Test that a locked user is not accessible on SFTP (IO)."""
        configuration = self.configuration
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": TEST_STATUS_LOCKED,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_DN, "sftp"
        )
        self.assertFalse(accessible)

    def test_check_account_accessible_expired_user_blocked(self):
        """Test that an expired user is inaccessible on web (non-ID) login."""
        configuration = self.configuration
        # Set expire to past
        expire_ts = 42
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
            "expire": expire_ts,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_DN, "oidc", io_login=False
        )
        self.assertFalse(accessible)

    def test_check_account_accessible_expired_user_sftp_access_blocked(self):
        """Test that an expired user is inaccessible on sftp if enenforced."""
        configuration = self.configuration
        configuration.site_io_account_expire = True
        # Set expire to past
        expire_ts = 42
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
            "expire": expire_ts,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_DN, "sftp"
        )
        self.assertFalse(accessible)

    def test_check_account_accessible_special_login_sharelink_access(self):
        """Test that a sharelink is detected as special login and accessible."""
        configuration = self.configuration
        # Create a dummy RW sharelink to user home
        sharelink_path = os.path.join(
            configuration.sharelink_home, "read-write", TEST_RW_SHARE_ID
        )
        sharelink_target = os.path.join(configuration.user_home, TEST_USER_DIR)
        ensure_dirs_exist(sharelink_target)
        ensure_dirs_exist(os.path.dirname(sharelink_path))
        os.symlink(sharelink_target, sharelink_path)

        accessible = check_account_accessible(
            configuration, TEST_RW_SHARE_ID, "sftp"
        )
        self.assertTrue(accessible)

    def test_check_account_accessible_special_login_job_access(self):
        """Test that a job ID is detected as special login and accessible."""
        configuration = self.configuration
        configuration.site_enable_jobs = True
        # Create a dummy job link to mrsl files entry
        job_target_path = os.path.join(
            configuration.mrsl_files_dir, TEST_JOB_ID
        )
        ensure_dirs_exist(job_target_path)
        job_link_path = os.path.join(
            configuration.sessid_to_mrsl_link_home, TEST_JOB_ID + ".mRSL"
        )
        ensure_dirs_exist(os.path.dirname(job_link_path))
        os.symlink(job_target_path, job_link_path)

        accessible = check_account_accessible(
            configuration, TEST_JOB_ID, "sftp"
        )
        self.assertTrue(accessible)

    def test_check_account_accessible_special_login_jupyter_access(self):
        """Test that a jupyter mount ID is detected as special login and accessible."""
        configuration = self.configuration
        configuration.site_enable_jupyter = True
        # Create a dummy jupyter‑mount link to user home
        jupyter_link_path = os.path.join(
            configuration.sessid_to_jupyter_mount_link_home,
            TEST_JUPYTER_SESSION_ID,
        )
        jupyter_target = os.path.join(configuration.user_home, TEST_USER_DIR)
        ensure_dirs_exist(jupyter_target)
        ensure_dirs_exist(os.path.dirname(jupyter_link_path))
        os.symlink(jupyter_target, jupyter_link_path)

        accessible = check_account_accessible(
            configuration, TEST_JUPYTER_SESSION_ID, "sftp"
        )
        self.assertTrue(accessible)

    def test_check_account_accessible_missing_user_web_rejected(self):
        """Test that check_account_accessible rejects a missing user on web (non-IO)."""
        configuration = self.configuration
        accessible = check_account_accessible(
            configuration, OTHER_USER_DN, "oidc", io_login=False
        )
        self.assertFalse(accessible)

    def test_check_account_accessible_missing_user_io_rejected(self):
        """Test that check_account_accessible rejects a missing user on SFTP (IO)."""
        configuration = self.configuration
        accessible = check_account_accessible(
            configuration, OTHER_USER_DN, "sftp"
        )
        self.assertFalse(accessible)

    def test_check_account_accessible_io_expire_disabled(self):
        """Test that account remains accessible on SFTP (IO) when expire is not enforced."""
        configuration = self.configuration
        configuration.site_io_account_expire = False
        # Set expire to past
        expire_ts = 42
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
            "expire": expire_ts,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_DN, "sftp", io_login=True
        )
        self.assertTrue(accessible)  # Because IO expire is disabled

    def test_check_account_accessible_openid_expire_disabled(self):
        """Test that account remains accessible on OpenID (non-IO) when expire is not enforced."""
        configuration = self.configuration
        configuration.user_openid_enforce_expire = False
        # Set expire to past
        expire_ts = 42
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": "active",
            "expire": expire_ts,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(configuration, user_dict)
        update_account_status_cache(configuration, user_dict)

        accessible = check_account_accessible(
            configuration, TEST_USER_DN, "oid", io_login=False
        )
        self.assertTrue(accessible)  # Because OpenID expire is disabled


class TestMigSharedAccountstate__check_update_account_expire(
    MigTestCase, UserAssertMixin
):
    """Coverage of accountstate check_update_account_expire function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for check_update_account_expire tests."""
        configuration = self.configuration
        # Ensure necessary directories exist
        ensure_dirs_exist(configuration.mig_system_files)
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, expire_marks_dir)
        )
        ensure_dirs_exist(
            os.path.join(configuration.mig_system_run, status_marks_dir)
        )
        # Set up user DB and keep paths for later use
        _ensure_dirs_needed_for_userdb(configuration)
        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        self._provision_test_user(self, TEST_USER_DN)

    def _update_account_in_db_and_cache(
        self, expire, status=TEST_STATUS_ACTIVE
    ):
        """Write account status and expire data to the DB and cache."""
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "status": status,
            "expire": expire,
        }
        update_user_dict(
            self.logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        update_account_expire_cache(self.configuration, user_dict)
        update_account_status_cache(self.configuration, user_dict)
        return user_dict

    def test_check_update_account_expire_auto_extends_oid(self):
        """Test auto extension for an OID user about to expire."""
        configuration = self.configuration
        expire = time.time() + 5 * 24 * 3600
        self._update_account_in_db_and_cache(expire)
        base_url = "https://oidc.example.com"
        configuration.migserver_https_ext_oid_url = base_url
        configuration.auto_add_oid_user = True
        environ = {
            "REMOTE_ADDR": "192.0.2.10",
            "HTTP_USER_AGENT": "test agent",
            "SCRIPT_URI": "%s/wsgi-bin/something.py" % base_url,
        }

        pending, cached_expire, user_dict = check_update_account_expire(
            configuration, TEST_USER_DN, environ, min_days_left=14
        )

        self.assertTrue(pending)
        self.assertEqual(cached_expire, expire)
        self.assertTrue(user_dict)
        self.assertTrue(user_dict["expire"] > expire)
        self.assertEqual(
            get_account_expire_cache(configuration, TEST_USER_DN),
            user_dict["expire"],
        )
        self.assertEqual(
            load_user_dict(
                self.logger, TEST_USER_DN, self.expected_user_db_file
            )["expire"],
            user_dict["expire"],
        )

    def test_check_update_account_expire_auto_extends_oidc(self):
        """Test auto extension for an OIDC user about to expire."""
        configuration = self.configuration
        expire = time.time() + 5 * 24 * 3600
        self._update_account_in_db_and_cache(expire)
        base_url = "https://oidc.example.com"
        configuration.migserver_https_ext_oidc_url = base_url
        configuration.auto_add_oidc_user = True
        environ = {
            "REMOTE_ADDR": "192.0.2.10",
            "HTTP_USER_AGENT": "test agent",
            "SCRIPT_URI": "%s/wsgi-bin/something.py" % base_url,
        }

        pending, cached_expire, user_dict = check_update_account_expire(
            configuration, TEST_USER_DN, environ, min_days_left=14
        )

        self.assertTrue(pending)
        self.assertEqual(cached_expire, expire)
        self.assertTrue(user_dict)
        self.assertTrue(user_dict["expire"] > expire)
        self.assertEqual(
            get_account_expire_cache(configuration, TEST_USER_DN),
            user_dict["expire"],
        )

    def test_check_update_account_expire_auto_extends_cert(self):
        """Test auto extension for a certificate user about to expire."""
        configuration = self.configuration
        expire = time.time() + 5 * 24 * 3600
        self._update_account_in_db_and_cache(expire)
        base_url = "https://cert.example.com"
        configuration.migserver_https_ext_cert_url = base_url
        configuration.auto_add_cert_user = True
        environ = {
            "REMOTE_ADDR": "192.0.2.10",
            "HTTP_USER_AGENT": "test agent",
            "SCRIPT_URI": "%s/wsgi-bin/something.py" % base_url,
        }

        pending, cached_expire, user_dict = check_update_account_expire(
            configuration, TEST_USER_DN, environ, min_days_left=14
        )

        self.assertTrue(pending)
        self.assertEqual(cached_expire, expire)
        self.assertTrue(user_dict)
        self.assertTrue(user_dict["expire"] > expire)
        self.assertEqual(
            get_account_expire_cache(configuration, TEST_USER_DN),
            user_dict["expire"],
        )

    def test_check_update_account_expire_not_near_expiry(self):
        """Test that users not near expiry are not auto-extended."""
        configuration = self.configuration
        expire = time.time() + 30 * 24 * 3600
        self._update_account_in_db_and_cache(expire)
        base_url = "https://oidc.example.com"
        configuration.migserver_https_ext_oidc_url = base_url
        configuration.auto_add_oidc_user = True
        environ = {
            "REMOTE_ADDR": "192.0.2.10",
            "HTTP_USER_AGENT": "test agent",
            "SCRIPT_URI": "%s/wsgi-bin/something.py" % base_url,
        }

        pending, cached_expire, user_dict = check_update_account_expire(
            configuration, TEST_USER_DN, environ, min_days_left=14
        )

        self.assertTrue(pending)
        self.assertEqual(cached_expire, expire)
        # NOTE: for expired users with cache mark no user_dict is loaded
        self.assertEqual(user_dict, None)
        self.assertEqual(
            get_account_expire_cache(configuration, TEST_USER_DN),
            expire,
        )

    def test_check_update_account_expire_no_matching_auto_update(self):
        """Test that near-expiry users keep expire without matching vhost."""
        configuration = self.configuration
        expire = time.time() + 5 * 24 * 3600
        self._update_account_in_db_and_cache(expire)
        configuration.migserver_https_ext_oidc_url = "https://oidc.example.com"
        configuration.auto_add_oidc_user = True
        environ = {
            "REMOTE_ADDR": "192.0.2.10",
            "HTTP_USER_AGENT": "test agent",
            "SCRIPT_URI": "https://unknown.example.com/wsgi-bin/page.py",
        }

        pending, cached_expire, user_dict = check_update_account_expire(
            configuration, TEST_USER_DN, environ, min_days_left=14
        )

        self.assertTrue(pending)
        self.assertEqual(cached_expire, expire)
        # NOTE: for expired users with cache mark no user_dict is loaded
        self.assertEqual(user_dict, None)
        self.assertEqual(
            get_account_expire_cache(configuration, TEST_USER_DN),
            expire,
        )

    def test_check_update_account_expire_skips_temporal_user_without_peer(self):
        """Test that local (typically external) temporal users are not auto-extended without peer."""
        configuration = self.configuration
        expire = 42
        self._update_account_in_db_and_cache(expire, TEST_STATUS_TEMPORAL)
        base_url = "https://ext.example.com"
        configuration.migserver_https_mig_oid_url = base_url
        # Enable renew with peers but test without any active
        configuration.auto_add_oid_user = True
        self.site_enable_peers = True
        self.site_peers_mandatory = True
        self.site_peers_explicit_fields = ["email"]
        environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "test agent",
            "SCRIPT_URI": "%s/wsgi-bin/something.py" % base_url,
        }

        pending, cached_expire, user_dict = check_update_account_expire(
            configuration, TEST_USER_DN, environ, min_days_left=14
        )

        self.assertFalse(pending)
        self.assertEqual(cached_expire, expire)
        # NOTE: for expired users with cache mark no user_dict is loaded
        self.assertEqual(user_dict, None)
        self.assertEqual(
            get_account_expire_cache(configuration, TEST_USER_DN),
            expire,
        )

    def test_check_update_account_expire_does_not_extend_locked_user(self):
        """Test that locked users are not auto-extended."""
        configuration = self.configuration
        expire = time.time() + 5 * 24 * 3600
        self._update_account_in_db_and_cache(expire, status=TEST_STATUS_LOCKED)
        base_url = "https://oid.example.com"
        configuration.migserver_https_ext_oidc_url = base_url
        configuration.auto_add_oidc_user = True
        environ = {
            "REMOTE_ADDR": "192.0.2.10",
            "HTTP_USER_AGENT": "test agent",
            "SCRIPT_URI": "%s/wsgi-bin/something.py" % base_url,
        }

        pending, cached_expire, user_dict = check_update_account_expire(
            configuration, TEST_USER_DN, environ, min_days_left=14
        )

        self.assertTrue(pending)
        self.assertEqual(cached_expire, expire)
        self.assertTrue(user_dict)
        self.assertEqual(user_dict["expire"], expire)
        self.assertEqual(
            get_account_expire_cache(configuration, TEST_USER_DN),
            expire,
        )

    def test_check_update_account_expire_expired_without_auto_update(self):
        """Test that expired users stay expired without matching auto update."""
        configuration = self.configuration
        expire = 42
        self._update_account_in_db_and_cache(expire)
        base_url = "https://ext.example.com"
        configuration.migserver_https_mig_oid_url = base_url
        configuration.auto_add_oid_user = False
        environ = {
            "REMOTE_ADDR": "192.0.2.10",
            "HTTP_USER_AGENT": "test agent",
            "SCRIPT_URI": "%s/wsgi-bin/page.py" % base_url,
        }

        pending, cached_expire, user_dict = check_update_account_expire(
            configuration, TEST_USER_DN, environ, min_days_left=14
        )

        self.assertFalse(pending)
        self.assertEqual(cached_expire, expire)
        # NOTE: for expired users with cache mark no user_dict is loaded
        self.assertEqual(user_dict, None)
        self.assertEqual(
            get_account_expire_cache(configuration, TEST_USER_DN),
            expire,
        )

    def test_check_update_account_expire_missing_user(self):
        """Test that missing users are reported as expired."""
        configuration = self.configuration
        base_url = "https://oid.example.com"
        environ = {
            "REMOTE_ADDR": "192.0.2.10",
            "HTTP_USER_AGENT": "test agent",
            "SCRIPT_URI": "%s/wsgi-bin/something.py" % base_url,
        }
        with self.assertLogs(level="ERROR") as log_capture:
            pending, expire, user_dict = check_update_account_expire(
                configuration, OTHER_USER_DN, environ, min_days_left=14
            )
            self.assertFalse(pending)
            self.assertEqual(expire, -42)
            self.assertIsNone(user_dict)
        self.assertTrue(
            any("no such account" in msg for msg in log_capture.output)
        )


if __name__ == "__main__":
    testmain()
