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
    check_account_expire,
    default_account_expire,
    default_account_valid_days,
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
    expire_marks_dir,
    status_marks_dir,
)
from mig.shared.useradm import _ensure_dirs_needed_for_userdb
from mig.shared.userdb import update_user_dict

# Imports required for the unit tests themselves
from tests.support import (
    MigTestCase,
    ensure_dirs_exist,
    testmain,
)
from tests.support.usersupp import OTHER_USER_DN, TEST_USER_DN

# Test constants
TEST_EXPIRE_TIMESTAMP = 1776031200
TEST_STATUS_ACTIVE = "active"
TEST_STATUS_LOCKED = "locked"

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
        print("DEBUG: before %s, result %s , after %s" %
              (min_expected, result, max_expected))
        self.assertTrue(min_expected <= result <= max_expected)


class TestMigSharedAccountstate__update_account_expire_cache(MigTestCase):
    """Coverage of accountstate update_account_expire_cache function."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up test environment for expire cache tests."""
        configuration = self.configuration
        # Ensure the mig_system_run sub directory exists for expire marks
        marks_path = os.path.join(
            configuration.mig_system_run, expire_marks_dir
        )
        ensure_dirs_exist(marks_path)

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
        # Ensure the mig_system_run sub directory exists for expire marks
        marks_path = os.path.join(
            configuration.mig_system_run, expire_marks_dir
        )
        ensure_dirs_exist(marks_path)

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
        # Ensure the mig_system_run sub directory exists for expire marks
        marks_path = os.path.join(
            configuration.mig_system_run, expire_marks_dir
        )
        ensure_dirs_exist(marks_path)

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
        # Ensure the mig_system_run sub directory exists for status marks
        marks_path = os.path.join(
            configuration.mig_system_run, status_marks_dir
        )
        ensure_dirs_exist(marks_path)

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
        # Ensure the mig_system_run sub directory exists for status marks
        marks_path = os.path.join(
            configuration.mig_system_run, status_marks_dir
        )
        ensure_dirs_exist(marks_path)

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
        # Ensure the mig_system_run directory exists for expire marks
        marks_path = os.path.join(
            configuration.mig_system_run, expire_marks_dir
        )
        ensure_dirs_exist(marks_path)

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
        """Test that check_account_expire returns expired if expire is not a number."""
        configuration = self.configuration
        logger = self.logger
        user_dict = {
            "distinguished_name": TEST_USER_DN,
            "expire": "invalid",
        }
        update_user_dict(
            logger, TEST_USER_DN, user_dict, self.expected_user_db_file
        )
        with self.assertRaises(TypeError):
            pending, expire, _ = check_account_expire(
                configuration, TEST_USER_DN
            )
            self.assertFalse(pending)
            self.assertEqual(expire, -42)

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


if __name__ == "__main__":
    testmain()
