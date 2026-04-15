# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_useradm - unit test of the corresponding mig shared module
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

import binascii
import datetime
import difflib
import io
import os
import pwd
import sys
import time
import unittest

from past.builtins import basestring

# Imports required for the unit test wrapping
from mig.shared.defaults import (
    DEFAULT_USER_ID_FORMAT,
    htaccess_filename,
    keyword_auto,
)

# Imports of the code under test
from mig.shared.useradm import (
    _ensure_dirs_needed_for_userdb,
    assure_current_htaccess,
    create_user, user_account_notify,
)

# Imports required for the unit tests themselves
from tests.support import (
    MIG_BASE,
    TEST_OUTPUT_DIR,
    FakeConfiguration,
    MigTestCase,
    cleanpath,
    ensure_dirs_exist,
    is_path_within,
    testmain,
)
from tests.support.fixturesupp import FixtureAssertMixin
from tests.support.picklesupp import PickleAssertMixin
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin

TEST_USER_EMAIL = TEST_USER_DN.split("/emailAddress=", 1)[-1]
TEST_USER_EXPIRE = 1776031200
OTHER_USER_DN = '/C=DK/ST=NA/L=NA/O=Other Org/OU=NA/CN=Other User/emailAddress=other@example.com'
OTHER_USER_EMAIL = 'other@email.org'

DUMMY_USER = "dummy-user"
DUMMY_STALE_USER = "dummy-stale-user"
DUMMY_HOME_DIR = "dummy_user_home"
DUMMY_SETTINGS_DIR = "dummy_user_settings"
DUMMY_MRSL_FILES_DIR = "dummy_mrsl_files"
DUMMY_RESOURCE_PENDING_DIR = "dummy_resource_pending"
DUMMY_CACHE_DIR = "dummy_user_cache"
DUMMY_HOME_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_HOME_DIR)
DUMMY_SETTINGS_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_SETTINGS_DIR)
DUMMY_MRSL_FILES_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_MRSL_FILES_DIR)
DUMMY_RESOURCE_PENDING_PATH = os.path.join(
    TEST_OUTPUT_DIR, DUMMY_RESOURCE_PENDING_DIR
)
DUMMY_CACHE_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_CACHE_DIR)
DUMMY_USER_DICT = {
    "distinguished_name": DUMMY_USER,
    "short_id": "%s@my.org" % DUMMY_USER,
}
DUMMY_REL_HTACCESS_PATH = os.path.join(
    DUMMY_HOME_DIR, DUMMY_USER, htaccess_filename
)
DUMMY_HTACCESS_PATH = DUMMY_REL_HTACCESS_PATH.replace(
    DUMMY_HOME_DIR, DUMMY_HOME_PATH
)
DUMMY_REL_HTACCESS_BACKUP_PATH = os.path.join(
    DUMMY_CACHE_DIR, DUMMY_USER, "%s.old" % htaccess_filename
)
DUMMY_HTACCESS_BACKUP_PATH = DUMMY_REL_HTACCESS_BACKUP_PATH.replace(
    DUMMY_CACHE_DIR, DUMMY_CACHE_PATH
)
DUMMY_REQUIRE_USER = 'require user "%s"' % DUMMY_USER
DUMMY_REQUIRE_STALE_USER = 'require user "%s"' % DUMMY_STALE_USER
DUMMY_CONF = FakeConfiguration(
    user_home=DUMMY_HOME_PATH,
    user_settings=DUMMY_SETTINGS_PATH,
    user_cache=DUMMY_CACHE_PATH,
    mrsl_files_dir=DUMMY_MRSL_FILES_PATH,
    resource_pending=DUMMY_RESOURCE_PENDING_PATH,
    site_user_id_format=DEFAULT_USER_ID_FORMAT,
    short_title="dummysite",
    support_email="support@dummysite.org",
    user_openid_providers=["dummyoidprovider.org"],
)


class TestMigSharedUseradm__create_user(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin
):
    """Coverage of useradm create_user function."""

    TEST_USER_DN_GDP = "%s/GDP" % (TEST_USER_DN,)
    TEST_USER_PASSWORD_HASH = (
        "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM2134uix"
    )

    def before_each(self):
        configuration = self.configuration

        _ensure_dirs_needed_for_userdb(self.configuration)

        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        ensure_dirs_exist(self.configuration.mig_system_files)

    def _provide_configuration(self):
        return "testconfig"

    def test_user_db_is_created(self):
        user_dict = {}
        user_dict["full_name"] = "Test User"
        user_dict["organization"] = "Test Org"
        user_dict["state"] = "NA"
        user_dict["country"] = "DK"
        user_dict["email"] = "user@example.com"
        user_dict["comment"] = "This is the create comment"
        user_dict["password"] = "password"
        create_user(
            user_dict, self.configuration, keyword_auto, default_renew=True
        )

        # presence of user home
        path_kind = MigTestCase._absolute_path_kind(self.expected_user_db_home)
        self.assertEqual(path_kind, "dir")

        # presence of user db
        path_kind = MigTestCase._absolute_path_kind(self.expected_user_db_file)
        self.assertEqual(path_kind, "file")

    def test_user_creation_records_a_user(self):
        def _adjust_user_dict_for_compare(user_obj):
            obj = dict(user_obj)
            obj["created"] = 9999999999.9999999
            obj["expire"] = 9999999999.9999999
            obj["unique_id"] = "__UNIQUE_ID__"
            return obj

        expected_user_id = TEST_USER_DN
        expected_user_password_hash = self.TEST_USER_PASSWORD_HASH

        user_dict = {}
        user_dict["full_name"] = "Test User"
        user_dict["organization"] = "Test Org"
        user_dict["state"] = "NA"
        user_dict["country"] = "DK"
        user_dict["email"] = "test@example.com"
        user_dict["comment"] = "This is the create comment"
        user_dict["locality"] = ""
        user_dict["organizational_unit"] = ""
        user_dict["password"] = ""
        user_dict["password_hash"] = expected_user_password_hash

        create_user(
            user_dict, self.configuration, keyword_auto, default_renew=True
        )

        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        self.assertIn(expected_user_id, pickled)

        prepared = self.prepareFixtureAssert(
            "MiG-users.db--example", fixture_format="json"
        )

        # TODO: remove resetting the handful of keys here
        #       this is done to allow the comparision to succeed
        actual_user_object = _adjust_user_dict_for_compare(
            pickled[expected_user_id]
        )
        expected_user_object = _adjust_user_dict_for_compare(
            prepared.fixture_data[expected_user_id]
        )

        self.maxDiff = None
        self.assertEqual(actual_user_object, expected_user_object)

    def test_user_creation_records_a_user_with_gdp(self):
        self.configuration.site_enable_gdp = True

        user_dict = {}
        user_dict["full_name"] = "Test User"
        user_dict["organization"] = "Test Org"
        user_dict["state"] = "NA"
        user_dict["country"] = "DK"
        user_dict["email"] = "test@example.com"
        user_dict["comment"] = "This is the create comment"
        user_dict["locality"] = ""
        user_dict["organizational_unit"] = ""
        user_dict["password"] = ""
        user_dict["password_hash"] = self.TEST_USER_PASSWORD_HASH
        # explicitly setting set a DN suffixed user DN to force GDP
        user_dict["distinguished_name"] = self.TEST_USER_DN_GDP

        try:
            create_user(
                user_dict, self.configuration, keyword_auto, default_renew=True
            )
        except:
            self.assertFalse(True, "should not be reached")

    def test_user_creation_and_renew_records_a_user(self):
        user_dict = {}
        user_dict["full_name"] = "Test User"
        user_dict["organization"] = "Test Org"
        user_dict["state"] = "NA"
        user_dict["country"] = "DK"
        user_dict["email"] = "test@example.com"
        user_dict["comment"] = "This is the create comment"
        user_dict["locality"] = ""
        user_dict["organizational_unit"] = ""
        user_dict["password"] = ""
        user_dict["password_hash"] = self.TEST_USER_PASSWORD_HASH

        try:
            create_user(
                user_dict,
                self.configuration,
                keyword_auto,
                default_renew=True,
                ask_renew=False,
            )
        except:
            self.assertFalse(True, "should not be reached")

        try:
            create_user(
                user_dict,
                self.configuration,
                keyword_auto,
                default_renew=True,
                ask_renew=False,
            )
        except:
            self.assertFalse(True, "should not be reached")

    def test_user_creation_fails_in_renew_when_locked(self):
        user_dict = {}
        user_dict["full_name"] = "Test User"
        user_dict["organization"] = "Test Org"
        user_dict["state"] = "NA"
        user_dict["country"] = "DK"
        user_dict["email"] = "test@example.com"
        user_dict["comment"] = "This is the create comment"
        user_dict["locality"] = ""
        user_dict["organizational_unit"] = ""
        user_dict["password"] = ""
        user_dict["password_hash"] = self.TEST_USER_PASSWORD_HASH
        # explicitly setting set a DN suffixed user DN to force GDP
        user_dict["distinguished_name"] = self.TEST_USER_DN_GDP
        user_dict["status"] = "locked"

        try:
            create_user(
                user_dict,
                self.configuration,
                keyword_auto,
                default_renew=True,
                ask_renew=False,
            )
        except:
            self.assertFalse(True, "should not be reached")

    def test_user_creation_with_id_collission_fails(self):
        user_dict = {}
        user_dict["full_name"] = "Test User"
        user_dict["organization"] = "Test Org"
        user_dict["state"] = "NA"
        user_dict["country"] = "DK"
        user_dict["email"] = "user@example.com"
        user_dict["comment"] = "This is the create comment"
        user_dict["password"] = "password"
        user_dict["distinguished_name"] = TEST_USER_DN

        try:
            create_user(
                user_dict, self.configuration, keyword_auto, default_renew=True
            )
        except:
            self.assertFalse(True, "should not be reached")

        # NOTE: reset distinguished_name and introduce an ID conflict to test
        del user_dict["distinguished_name"]
        user_dict["organization"] = "Another Org"
        with self.assertRaises(Exception):
            create_user(
                user_dict,
                self.configuration,
                keyword_auto,
                default_renew=True,
                ask_renew=False,
            )


class MigSharedUseradm__assure_current_htaccess(MigTestCase):
    """Coverage of useradm behaviours around htaccess."""

    def before_each(self):
        """The create_user call requires quite a few helper dirs"""
        os.makedirs(os.path.join(DUMMY_HOME_PATH, DUMMY_USER))
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        os.makedirs(os.path.join(DUMMY_MRSL_FILES_PATH, DUMMY_USER))
        os.makedirs(os.path.join(DUMMY_RESOURCE_PENDING_PATH, DUMMY_USER))
        os.makedirs(os.path.join(DUMMY_CACHE_PATH, DUMMY_USER))
        cleanpath(DUMMY_HOME_PATH, self)
        cleanpath(DUMMY_SETTINGS_PATH, self)
        cleanpath(DUMMY_MRSL_FILES_PATH, self)
        cleanpath(DUMMY_RESOURCE_PENDING_PATH, self)
        cleanpath(DUMMY_CACHE_PATH, self)

    def assertHtaccessRequireUserClause(self, generated, expected):
        """Makes sure generated htaccess file contains the expected string"""
        if isinstance(generated, basestring):
            with io.open(generated) as htaccess_file:
                generated = htaccess_file.read()

        generated_lines = generated.split("\n")
        if not expected in generated_lines:
            raise AssertionError("no such require user line: %s" % expected)

    def test_skips_accounts_without_short_id(self):
        user_dict = {}
        user_dict.update(DUMMY_USER_DICT)
        del user_dict["short_id"]
        assure_current_htaccess(DUMMY_CONF, DUMMY_USER, user_dict, False,
                                False)

        try:
            path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_PATH)
            # File should not exist here at all
            self.assertNotEqual(path_kind, "file")
        except OSError as ignore_oserr:
            pass

    def test_creates_missing_htaccess_file(self):
        user_dict = {}
        user_dict.update(DUMMY_USER_DICT)
        assure_current_htaccess(DUMMY_CONF, DUMMY_USER, user_dict, False,
                                False)

        path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_PATH)
        # File should exist here and be valid
        self.assertEqual(path_kind, "file")
        path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_BACKUP_PATH)
        # Backup file should exist here and be empty
        self.assertEqual(path_kind, "file")

        self.assertHtaccessRequireUserClause(
            DUMMY_HTACCESS_PATH, DUMMY_REQUIRE_USER
        )

    def test_repairs_existing_stale_htaccess_file(self):
        user_dict = {}
        user_dict.update(DUMMY_USER_DICT)
        # Fake stale user ID directly through DN
        user_dict["distinguished_name"] = DUMMY_STALE_USER
        assure_current_htaccess(DUMMY_CONF, DUMMY_USER, user_dict, False,
                                False)

        # Verify stale
        self.assertHtaccessRequireUserClause(
            DUMMY_HTACCESS_PATH, DUMMY_REQUIRE_STALE_USER
        )

        # Reset stale user ID and retry
        user_dict = {}
        user_dict.update(DUMMY_USER_DICT)
        assure_current_htaccess(DUMMY_CONF, DUMMY_USER, user_dict, False,
                                False)

        path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_PATH)
        # File should exist here and be valid
        self.assertEqual(path_kind, "file")
        path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_BACKUP_PATH)
        # Backup file should exist here and be empty
        self.assertEqual(path_kind, "file")

        self.assertHtaccessRequireUserClause(
            DUMMY_HTACCESS_PATH, DUMMY_REQUIRE_USER
        )


class TestMigSharedUseradm__user_account_notify(MigTestCase, UserAssertMixin):
    """Coverage of useradm user_account_notify function."""

    expected_expire = -1

    def _provide_configuration(self):
        """Return configuration to use"""
        return "testconfig"

    def before_each(self):
        """Create test environment for useradm tests"""
        configuration = self.configuration

        _ensure_dirs_needed_for_userdb(self.configuration)

        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        ensure_dirs_exist(self.configuration.mig_system_files)
        self._provision_test_user(self, TEST_USER_DN)
        adjusted_datetime = datetime.date.today() + datetime.timedelta(days=5)
        self.expected_expire = int(time.mktime(adjusted_datetime.timetuple()))

    def test_default_address_and_expire(self):
        """Test addresses and expire for test account"""
        (_, username, full_name, expire, addresses, errors) = \
            user_account_notify(TEST_USER_DN, {'email': ['AUTO']},
                                self.configuration,
                                self.expected_user_db_file, False,
                                False)
        self.assertEqual(addresses, {'email': [TEST_USER_EMAIL]})
        self.assertEqual(expire, self.expected_expire)
        self.assertEqual(errors, [])

    def test_extra_address_and_expire(self):
        """Test addresses and expire for test with extra account"""
        (_, username, full_name, expire, addresses, errors) = \
            user_account_notify(TEST_USER_DN, {'email':
                                               ['AUTO', OTHER_USER_EMAIL]},
                                self.configuration,
                                self.expected_user_db_file, False,
                                False)
        self.assertEqual(addresses, {'email':
                                     [TEST_USER_EMAIL, OTHER_USER_EMAIL]})
        self.assertEqual(expire, self.expected_expire)
        self.assertEqual(errors, [])

    def test_missing_user_fails(self):
        """Test failure for missing user account"""
        (_, username, full_name, expire, addresses, errors) = \
            user_account_notify(OTHER_USER_DN, {'email': ['AUTO']},
                                self.configuration,
                                self.expected_user_db_file, False,
                                False)
        self.assertEqual(addresses, {'email': []})
        self.assertEqual(expire, None)
        self.assertTrue(errors and 'No such user' in errors[0])

    def test_missing_user_db_bails_out(self):
        """Test failure for missing user db"""
        with self.assertLogs(level='ERROR') as log_capture:
            (_, username, full_name, expire, addresses, errors) = \
                user_account_notify(OTHER_USER_DN, {'email': ['AUTO']},
                                    self.configuration,
                                    'no_such_user_db', False,
                                    False)
        self.assertEqual(addresses, [])
        self.assertEqual(expire, None)
        self.assertTrue(errors and 'Failed to load user DB' in errors[0])
        self.assertTrue(any('Failed to load user DB' in msg for msg in
                            log_capture.output))


if __name__ == "__main__":
    testmain()
