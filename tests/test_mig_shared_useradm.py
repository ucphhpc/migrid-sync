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

import datetime
import io
import os
import time
import unittest

from past.builtins import basestring

# Imports required for the unit test wrapping
from mig.shared.base import client_id_dir, distinguished_name_to_user
from mig.shared.defaults import (
    DEFAULT_USER_ID_FORMAT, UUID_USER_ID_FORMAT,
    htaccess_filename,
    keyword_auto,
    ssh_conf_dir,
    davs_conf_dir,
    ftps_conf_dir,
    welcome_filename,
    settings_filename,
    profile_filename,
    widgets_filename,
    default_css_filename,
    user_id_alias_dir,
)

# Imports of the code under test
from mig.shared.useradm import (
    _ensure_dirs_needed_for_userdb,
    _get_required_user_alias_links,
    _get_required_user_dir_links,
    assure_current_htaccess,
    create_user,
    delete_user,
    edit_user,
    get_any_oid_user_dn,
    lookup_client_id_from_uuid,
    user_account_notify,
)

# Imports required for the unit tests themselves
from tests.support import (
    TEST_OUTPUT_DIR,
    FakeConfiguration,
    MigTestCase,
    cleanpath,
    ensure_dirs_exist,
    testmain,
)
from tests.support.fixturesupp import FixtureAssertMixin
from tests.support.picklesupp import PickleAssertMixin
from tests.support.usersupp import NO_SUCH_USER_DN, OTHER_USER_DN, \
    TEST_USER_DN, UserAssertMixin

# TODO: add this client dir in usersupp and import from there instead
TEST_USER_DIR = TEST_USER_DN.replace('/', '+').replace(' ', '_')

TEST_USER_SHORT_ID = "abc123@some.org"
TEST_USER_UUID = "UniqueUserIdForTestUser"
TEST_USER_SHORT_ID = "abc123@some.org"
TEST_USER_EMAIL = TEST_USER_DN.split("/emailAddress=", 1)[-1]
TEST_USER_EXPIRE = 1776031200
OTHER_USER_EMAIL = OTHER_USER_DN.split("/emailAddress=", 1)[-1]

# NOTE: use a bogus path in output to make sure lock artifacts end up there
NO_SUCH_USER_DB = os.path.join(TEST_OUTPUT_DIR, 'no_such_user.db')

DUMMY_USER = "dummy-user"
DUMMY_STALE_USER = "dummy-stale-user"
DUMMY_PASSWORD_HASH = "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM1234uxi"
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


def _provision_uuid_test_user(configuration, client_id, client_overrides=None):
    """Helper to provision test users when UUID format is used"""
    # TODO: merge something like this version into standard _provision_test_user?
    # IMPORTANT: we need to use explicit create_user here for UUID format!
    user_dict = distinguished_name_to_user(client_id)
    # NOTE: generate unique and short id based on id to avoid test collisions
    user_dict["unique_id"] = binascii.hexlify(
        client_id.encode('utf8')).decode('ascii')
    user_dict["short_id"] = binascii.hexlify(
        user_dict["email"].encode('utf8')).decode('ascii')
    user_dict["comment"] = "This is the user account comment"
    user_dict["locality"] = ""
    user_dict["organizational_unit"] = ""
    user_dict["password"] = ""
    user_dict["password_hash"] = ""
    if client_overrides is not None:
        user_dict.update(client_overrides)

    create_user(
        user_dict,
        configuration,
        keyword_auto,
        default_renew=True,
        ask_renew=False,
    )
    return user_dict


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
        configuration.site_user_id_format = DEFAULT_USER_ID_FORMAT

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

    def test_user_creation_creates_fs_entries(self):
        user_dict = {}
        user_dict["short_id"] = TEST_USER_SHORT_ID
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

        create_user(
            user_dict, self.configuration, keyword_auto, default_renew=True
        )
        home_dir = os.path.join(self.configuration.user_home,
                                TEST_USER_DIR)
        self.assertTrue(os.path.isdir(home_dir))

        short_link = os.path.join(self.configuration.user_home,
                                  TEST_USER_SHORT_ID)
        self.assertTrue(os.path.islink(short_link))
        self.assertEqual(os.path.realpath(home_dir),
                         os.path.realpath(short_link))

        settings_dir = os.path.join(self.configuration.user_settings,
                                    TEST_USER_DIR)
        self.assertTrue(os.path.isdir(settings_dir))

        ssh_dir = os.path.join(home_dir, ssh_conf_dir)
        self.assertTrue(os.path.isdir(ssh_dir))
        davs_dir = os.path.join(home_dir, davs_conf_dir)
        self.assertTrue(os.path.isdir(davs_dir))
        ftps_dir = os.path.join(home_dir, ftps_conf_dir)
        self.assertTrue(os.path.isdir(ftps_dir))
        htaccess_path = os.path.join(home_dir, htaccess_filename)
        self.assertTrue(os.path.isfile(htaccess_path))
        # NOTE: test htaccess contents matches access for X509 ID
        req_pattern = 'require user "%s"'
        with open(htaccess_path) as test_fd:
            test_contents = test_fd.read()
            self.assertIn(req_pattern % TEST_USER_DN, test_contents)

        enc_user_dn = TEST_USER_DN.encode('utf8')
        enc_creator = 'CREATOR'.encode('utf8')
        welcome_path = os.path.join(home_dir, welcome_filename)
        self.assertTrue(os.path.isfile(welcome_path))
        settings_path = os.path.join(settings_dir, settings_filename)
        self.assertTrue(os.path.isfile(settings_path))
        pickled = self.assertPickledFile(settings_path)
        self.assertIn(enc_user_dn, pickled[enc_creator])
        profile_path = os.path.join(settings_dir, profile_filename)
        self.assertTrue(os.path.isfile(profile_path))
        pickled = self.assertPickledFile(profile_path)
        self.assertIn(enc_user_dn,
                      pickled[enc_creator])
        widgets_path = os.path.join(settings_dir, widgets_filename)
        self.assertTrue(os.path.isfile(widgets_path))
        pickled = self.assertPickledFile(widgets_path)
        self.assertIn(enc_user_dn,
                      pickled[enc_creator])
        css_path = os.path.join(home_dir, default_css_filename)
        self.assertTrue(os.path.isfile(css_path))
        with open(css_path) as test_fd:
            test_contents = test_fd.read()
            self.assertIn('No changes - use default', test_contents)

        # NOTE: check permissions on htaccess, .ssh
        htaccess_stat = os.stat(htaccess_path)
        self.assertEqual(htaccess_stat.st_mode, 0o100444)
        ssh_stat = os.stat(ssh_dir)
        self.assertEqual(ssh_stat.st_mode, 0o40755)

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
        except Exception:
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
        except Exception:
            self.assertFalse(True, "should not be reached")

        try:
            create_user(
                user_dict,
                self.configuration,
                keyword_auto,
                default_renew=True,
                ask_renew=False,
            )
        except Exception:
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
        except Exception:
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
        except Exception:
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


# TODO: consider merging the tests for UUID and X509 format
class TestMigSharedUseradm__create_user_uuid_user_id(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin
):
    """Coverage of useradm create_user function with UUID format."""

    TEST_USER_DN_GDP = "%s/GDP" % (TEST_USER_DN,)
    TEST_USER_PASSWORD_HASH = "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM2134uix"

    def before_each(self):
        configuration = self.configuration
        configuration.site_user_id_format = UUID_USER_ID_FORMAT

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
        user_dict["unique_id"] = TEST_USER_UUID
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
        user_dict["unique_id"] = TEST_USER_UUID
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

    def test_user_creation_creates_fs_entries(self):
        user_dict = {}
        user_dict["unique_id"] = TEST_USER_UUID
        user_dict["short_id"] = TEST_USER_SHORT_ID
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

        create_user(
            user_dict, self.configuration, keyword_auto, default_renew=True
        )
        home_dir = os.path.join(self.configuration.user_home, TEST_USER_UUID)
        self.assertTrue(os.path.isdir(home_dir))
        home_link = os.path.join(self.configuration.user_home,
                                 TEST_USER_DIR)
        self.assertTrue(os.path.islink(home_link))
        self.assertEqual(os.path.realpath(home_dir),
                         os.path.realpath(home_link))
        short_link = os.path.join(self.configuration.user_home,
                                  TEST_USER_SHORT_ID)
        self.assertTrue(os.path.islink(short_link))
        self.assertEqual(os.path.realpath(home_dir),
                         os.path.realpath(short_link))

        settings_dir = os.path.join(self.configuration.user_settings,
                                    TEST_USER_UUID)
        self.assertTrue(os.path.isdir(settings_dir))
        settings_link = os.path.join(self.configuration.user_settings,
                                     TEST_USER_DIR)
        self.assertTrue(os.path.islink(settings_link))
        self.assertEqual(os.path.realpath(settings_dir),
                         os.path.realpath(settings_link))

        ssh_dir = os.path.join(home_dir, ssh_conf_dir)
        self.assertTrue(os.path.isdir(ssh_dir))
        davs_dir = os.path.join(home_dir, davs_conf_dir)
        self.assertTrue(os.path.isdir(davs_dir))
        ftps_dir = os.path.join(home_dir, ftps_conf_dir)
        self.assertTrue(os.path.isdir(ftps_dir))
        htaccess_path = os.path.join(home_dir, htaccess_filename)
        self.assertTrue(os.path.isfile(htaccess_path))
        # NOTE: test htaccess contents matches access for UUID and X509 ID
        req_pattern = 'require user "%s"'
        with open(htaccess_path) as test_fd:
            test_contents = test_fd.read()
            self.assertIn(req_pattern % TEST_USER_DN, test_contents)
            # TODO: add UUID to htaccess and enable next?
            # self.assertIn(req_pattern % TEST_USER_UUID, htaccess_contents)

        enc_user_dn = TEST_USER_DN.encode('utf8')
        enc_creator = 'CREATOR'.encode('utf8')
        welcome_path = os.path.join(home_dir, welcome_filename)
        self.assertTrue(os.path.isfile(welcome_path))
        settings_path = os.path.join(settings_dir, settings_filename)
        self.assertTrue(os.path.isfile(settings_path))
        pickled = self.assertPickledFile(settings_path)
        self.assertIn(enc_user_dn, pickled[enc_creator])
        profile_path = os.path.join(settings_dir, profile_filename)
        self.assertTrue(os.path.isfile(profile_path))
        pickled = self.assertPickledFile(profile_path)
        self.assertIn(enc_user_dn, pickled[enc_creator])
        widgets_path = os.path.join(settings_dir, widgets_filename)
        self.assertTrue(os.path.isfile(widgets_path))
        pickled = self.assertPickledFile(widgets_path)
        self.assertIn(enc_user_dn, pickled[enc_creator])
        css_path = os.path.join(home_dir, default_css_filename)
        self.assertTrue(os.path.isfile(css_path))
        with open(css_path) as test_fd:
            test_contents = test_fd.read()
            self.assertIn('No changes - use default', test_contents)

        # NOTE: check permissions on htaccess, .ssh
        htaccess_stat = os.stat(htaccess_path)
        self.assertEqual(htaccess_stat.st_mode, 0o100444)
        ssh_stat = os.stat(ssh_dir)
        self.assertEqual(ssh_stat.st_mode, 0o40755)

    def test_user_creation_records_a_user_with_gdp(self):
        self.configuration.site_enable_gdp = True

        user_dict = {}
        user_dict["unique_id"] = TEST_USER_UUID
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
        user_dict["unique_id"] = TEST_USER_UUID
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
        user_dict["unique_id"] = TEST_USER_UUID
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
        user_dict["unique_id"] = TEST_USER_UUID
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
                                    self.configuration, NO_SUCH_USER_DB,
                                    False, False)
        self.assertEqual(addresses, [])
        self.assertEqual(expire, None)
        self.assertTrue(errors and 'Failed to load user DB' in errors[0])
        self.assertTrue(any('Failed to load user DB' in msg for msg in
                            log_capture.output))
        try:
            os.remove("%s.lock" % NO_SUCH_USER_DB)
        except Exception:
            pass


# TODO: consider merging the tests for UUID and X509 format
class TestMigSharedUseradm__delete_user(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin
):
    """Coverage of useradm delete_user function."""

    TEST_USER_DN_GDP = "%s/GDP" % (TEST_USER_DN,)
    TEST_USER_PASSWORD_HASH = (
        "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM2134uix"
    )

    def before_each(self):
        configuration = self.configuration
        configuration.site_user_id_format = DEFAULT_USER_ID_FORMAT

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

    def test_user_delete_completes(self):
        self._provision_test_user(self, TEST_USER_DN)

        try:
            delete_user(
                distinguished_name_to_user(TEST_USER_DN),
                self.configuration,
                keyword_auto,
                force=True,
            )
        except Exception:
            self.assertFalse(True, "should not be reached")

    def test_user_deletion_removes_fs_entries(self):
        self._provision_test_user(self, TEST_USER_DN)

        try:
            delete_user(
                distinguished_name_to_user(TEST_USER_DN),
                self.configuration,
                keyword_auto,
                force=True,
            )
        except Exception:
            self.assertFalse(True, "should not be reached")

        home_dir = os.path.join(self.configuration.user_home, TEST_USER_DN)
        self.assertFalse(os.path.isdir(home_dir))
        self.assertFalse(os.path.exists(home_dir))
        short_link = os.path.join(self.configuration.user_home,
                                  TEST_USER_SHORT_ID)
        self.assertFalse(os.path.islink(short_link))
        self.assertFalse(os.path.exists(short_link))

        settings_dir = os.path.join(self.configuration.user_settings,
                                    TEST_USER_UUID)
        self.assertFalse(os.path.isdir(settings_dir))
        self.assertFalse(os.path.exists(settings_dir))
        settings_link = os.path.join(self.configuration.user_settings,
                                     TEST_USER_DIR)
        self.assertFalse(os.path.islink(settings_link))
        self.assertFalse(os.path.exists(settings_link))

        ssh_dir = os.path.join(home_dir, ssh_conf_dir)
        self.assertFalse(os.path.isdir(ssh_dir))
        self.assertFalse(os.path.exists(ssh_dir))
        davs_dir = os.path.join(home_dir, davs_conf_dir)
        self.assertFalse(os.path.isdir(davs_dir))
        self.assertFalse(os.path.exists(davs_dir))
        ftps_dir = os.path.join(home_dir, ftps_conf_dir)
        self.assertFalse(os.path.isdir(ftps_dir))
        self.assertFalse(os.path.exists(ftps_dir))
        htaccess_path = os.path.join(home_dir, htaccess_filename)
        self.assertFalse(os.path.isfile(htaccess_path))
        self.assertFalse(os.path.exists(htaccess_path))
        welcome_path = os.path.join(home_dir, welcome_filename)
        self.assertFalse(os.path.isfile(welcome_path))
        self.assertFalse(os.path.exists(welcome_path))
        settings_path = os.path.join(settings_dir, settings_filename)
        self.assertFalse(os.path.isfile(settings_path))
        self.assertFalse(os.path.exists(settings_path))
        profile_path = os.path.join(settings_dir, profile_filename)
        self.assertFalse(os.path.isfile(profile_path))
        self.assertFalse(os.path.exists(profile_path))
        widgets_path = os.path.join(settings_dir, widgets_filename)
        self.assertFalse(os.path.isfile(widgets_path))
        self.assertFalse(os.path.exists(widgets_path))
        css_path = os.path.join(home_dir, default_css_filename)
        self.assertFalse(os.path.isfile(css_path))
        self.assertFalse(os.path.exists(css_path))


class TestMigSharedUseradm__delete_user_uuid_user_id(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin
):
    """Coverage of useradm delete_user function with UUID format."""

    TEST_USER_DN_GDP = "%s/GDP" % (TEST_USER_DN,)
    TEST_USER_PASSWORD_HASH = "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM2134uix"

    def before_each(self):
        configuration = self.configuration
        configuration.site_user_id_format = UUID_USER_ID_FORMAT

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

    def test_user_delete_completes(self):
        _provision_uuid_test_user(self.configuration, TEST_USER_DN)

        try:
            delete_user(
                distinguished_name_to_user(TEST_USER_DN),
                self.configuration,
                keyword_auto,
                force=True,
            )
        except Exception:
            self.assertFalse(True, "should not be reached")

    def test_user_deletion_removes_fs_entries(self):
        _provision_uuid_test_user(self.configuration, TEST_USER_DN)

        try:
            delete_user(
                distinguished_name_to_user(TEST_USER_DN),
                self.configuration,
                keyword_auto,
                force=True,
            )
        except Exception:
            self.assertFalse(True, "should not be reached")

        home_dir = os.path.join(self.configuration.user_home, TEST_USER_UUID)
        self.assertFalse(os.path.isdir(home_dir))
        self.assertFalse(os.path.exists(home_dir))
        home_link = os.path.join(self.configuration.user_home,
                                 TEST_USER_DIR)
        self.assertFalse(os.path.islink(home_link))
        self.assertFalse(os.path.exists(home_link))
        short_link = os.path.join(self.configuration.user_home,
                                  TEST_USER_SHORT_ID)
        self.assertFalse(os.path.islink(short_link))
        self.assertFalse(os.path.exists(short_link))

        settings_dir = os.path.join(self.configuration.user_settings,
                                    TEST_USER_UUID)
        self.assertFalse(os.path.isdir(settings_dir))
        self.assertFalse(os.path.exists(settings_dir))
        settings_link = os.path.join(self.configuration.user_settings,
                                     TEST_USER_DIR)
        self.assertFalse(os.path.islink(settings_link))
        self.assertFalse(os.path.exists(settings_link))

        ssh_dir = os.path.join(home_dir, ssh_conf_dir)
        self.assertFalse(os.path.isdir(ssh_dir))
        self.assertFalse(os.path.exists(ssh_dir))
        davs_dir = os.path.join(home_dir, davs_conf_dir)
        self.assertFalse(os.path.isdir(davs_dir))
        self.assertFalse(os.path.exists(davs_dir))
        ftps_dir = os.path.join(home_dir, ftps_conf_dir)
        self.assertFalse(os.path.isdir(ftps_dir))
        self.assertFalse(os.path.exists(ftps_dir))
        htaccess_path = os.path.join(home_dir, htaccess_filename)
        self.assertFalse(os.path.isfile(htaccess_path))
        self.assertFalse(os.path.exists(htaccess_path))
        welcome_path = os.path.join(home_dir, welcome_filename)
        self.assertFalse(os.path.isfile(welcome_path))
        self.assertFalse(os.path.exists(welcome_path))
        settings_path = os.path.join(settings_dir, settings_filename)
        self.assertFalse(os.path.isfile(settings_path))
        self.assertFalse(os.path.exists(settings_path))
        profile_path = os.path.join(settings_dir, profile_filename)
        self.assertFalse(os.path.isfile(profile_path))
        self.assertFalse(os.path.exists(profile_path))
        widgets_path = os.path.join(settings_dir, widgets_filename)
        self.assertFalse(os.path.isfile(widgets_path))
        self.assertFalse(os.path.exists(widgets_path))
        css_path = os.path.join(home_dir, default_css_filename)
        self.assertFalse(os.path.isfile(css_path))
        self.assertFalse(os.path.exists(css_path))


class TestMigSharedUseradm__edit_user(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin, UserAssertMixin
):
    """Coverage of useradm edit_user function."""

    TEST_USER_PASSWORD_HASH = (
        "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM2134uix"
    )

    def before_each(self):
        configuration = self.configuration
        configuration.site_user_id_format = DEFAULT_USER_ID_FORMAT

        _ensure_dirs_needed_for_userdb(self.configuration)

        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        ensure_dirs_exist(self.configuration.mig_system_files)
        ensure_dirs_exist(self.configuration.resource_home)

    def _provide_configuration(self):
        return "testconfig"

    def _flush_test_user(self, client_id):
        """Helper to force clean up after provisioned test users"""
        try:
            delete_user(
                {'distinguished_name': client_id},
                self.configuration,
                keyword_auto,
                force=True,
            )
        except Exception:
            pass

    def test_edit_user_email(self):
        """Test basic user email editing"""
        self._provision_test_user(self, TEST_USER_DN)
        # Extract original for later verification
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        user_dict = pickled[TEST_USER_DN]

        # Edit user attribute and verify changed in DB
        changes = {
            "email": OTHER_USER_EMAIL,
        }
        removes = []
        edit_user(
            TEST_USER_DN, changes, removes, self.configuration, keyword_auto
        )
        edited_dn = TEST_USER_DN.replace(TEST_USER_EMAIL, OTHER_USER_EMAIL)
        # Verify changes
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        self.assertIn(edited_dn, pickled)
        edited_user = pickled[edited_dn]
        for field in user_dict:
            if field == "email":
                self.assertEqual(edited_user[field], OTHER_USER_EMAIL)
            elif field == "distinguished_name":
                self.assertEqual(edited_user[field], edited_dn)
            else:
                self.assertEqual(edited_user[field], user_dict[field])

        self._flush_test_user(edited_user['distinguished_name'])

    def test_edit_user_remove_attributes(self):
        """Test removing user attributes"""
        self._provision_test_user(self, TEST_USER_DN)
        # Extract original for later verification
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        user_dict = pickled[TEST_USER_DN]

        changes = {}
        removes = ["comment"]
        edit_user(
            TEST_USER_DN, changes, removes, self.configuration, keyword_auto,
            meta_only=True
        )

        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        edited_user = pickled[TEST_USER_DN]
        for field in user_dict:
            if field == "comment":
                self.assertNotIn(field, edited_user)
            else:
                self.assertEqual(edited_user[field], user_dict[field])

        self._flush_test_user(TEST_USER_DN)

    def test_edit_user_meta_only(self):
        """Test metadata-only update (no FS changes)"""
        self._provision_test_user(self, TEST_USER_DN)
        # Extract original for later verification
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        user_dict = pickled[TEST_USER_DN]

        changes = {"comment": "meta comment"}
        removes = []
        edit_user(
            TEST_USER_DN, changes, removes, self.configuration, keyword_auto,
            meta_only=True
        )

        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        edited_user = pickled[TEST_USER_DN]
        for field in user_dict:
            if field == "comment":
                self.assertEqual(pickled[TEST_USER_DN][field], "meta comment")
            else:
                self.assertEqual(edited_user[field], user_dict[field])

        self._flush_test_user(TEST_USER_DN)

    @unittest.skip("make backend function less noisy (traceback) and enable?")
    def test_edit_user_nonexistent(self):
        """Test editing nonexistent user"""
        changes = {"email": "dummy@example.com"}
        removes = []
        with self.assertRaises(Exception):
            edit_user(
                NO_SUCH_USER_DN, changes, removes, self.configuration,
                keyword_auto
            )

    @unittest.skip("make backend function less noisy (traceback) and enable?")
    def test_edit_user_nonexistent_force(self):
        """Test editing nonexistent user with force=True"""
        changes = {"email": "dummy@example.com"}
        removes = []
        # NOTE: forced edit logs errors in update_account_X functions
        self.logger.forgive_errors()
        with self.assertRaises(Exception):
            edit_user(
                NO_SUCH_USER_DN, changes, removes, self.configuration,
                keyword_auto, force=True
            )

    @unittest.skip("make backend function less noisy (traceback) and enable?")
    def test_edit_user_dn_collision_fails(self):
        """Test that editing a user to a DN that already exists fails"""
        # NOTE: we can't use _provision_test_users here as it lacks passwords
        test_user_dict = distinguished_name_to_user(TEST_USER_DN)
        test_user_dict["comment"] = "This is the create comment"
        test_user_dict["password"] = ""
        test_user_dict["password_hash"] = self.TEST_USER_PASSWORD_HASH
        try:
            create_user(
                test_user_dict, self.configuration, keyword_auto, default_renew=True
            )
        except Exception:
            self.assertFalse(True, "should not be reached")
        other_user_dict = distinguished_name_to_user(OTHER_USER_DN)
        other_user_dict["comment"] = "This is the create comment"
        other_user_dict["password"] = ""
        other_user_dict["password_hash"] = DUMMY_PASSWORD_HASH
        try:
            create_user(
                other_user_dict, self.configuration, keyword_auto, default_renew=True
            )
        except Exception:
            self.assertFalse(True, "should not be reached")

        changes = distinguished_name_to_user(OTHER_USER_DN)
        removes = []
        with self.assertRaises(Exception):
            edit_user(
                TEST_USER_DN, changes, removes, self.configuration,
                keyword_auto
            )

        self._flush_test_user(TEST_USER_DN)
        self._flush_test_user(OTHER_USER_DN)

    def test_edit_user_renames_user(self):
        """Test editing fields that change the distinguished name"""
        self._provision_test_user(self, TEST_USER_DN)
        # Extract original for later verification
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        user_dict = pickled[TEST_USER_DN]

        changes = {"full_name": "Renamed User"}
        removes = []
        result = edit_user(
            TEST_USER_DN, changes, removes, self.configuration,
            keyword_auto
        )

        new_dn = result["distinguished_name"]
        new_dir = new_dn.replace("/", "+").replace(" ", "_")

        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        edited_user = pickled[new_dn]
        self.assertNotIn(TEST_USER_DN, pickled)
        self.assertIn(new_dn, pickled)
        for field in user_dict:
            if field == "full_name":
                self.assertEqual(edited_user[field], "Renamed User")
            elif field == "distinguished_name":
                self.assertEqual(edited_user[field], new_dn)
            else:
                self.assertEqual(edited_user[field], user_dict[field])

        old_home = os.path.join(self.configuration.user_home, TEST_USER_DIR)
        new_home = os.path.join(self.configuration.user_home, new_dir)
        self.assertFalse(os.path.exists(old_home))
        self.assertTrue(os.path.isdir(new_home))

        old_settings = os.path.join(
            self.configuration.user_settings, TEST_USER_DIR)
        new_settings = os.path.join(self.configuration.user_settings, new_dir)
        self.assertFalse(os.path.exists(old_settings))
        self.assertTrue(os.path.isdir(new_settings))

        self._flush_test_user(new_dn)


class TestMigSharedUseradm__edit_user_uuid_user_id(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin, UserAssertMixin
):
    """Coverage of useradm edit_user function with UUID format."""

    TEST_USER_PASSWORD_HASH = (
        "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM2134uix"
    )

    def before_each(self):
        configuration = self.configuration
        configuration.site_user_id_format = UUID_USER_ID_FORMAT

        _ensure_dirs_needed_for_userdb(self.configuration)

        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        ensure_dirs_exist(self.configuration.mig_system_files)
        ensure_dirs_exist(self.configuration.resource_home)

    def _provide_configuration(self):
        return "testconfig"

    def _flush_test_user(self, client_id):
        """Helper to force clean up after provisioned test users"""
        try:
            delete_user(
                {'distinguished_name': client_id},
                self.configuration,
                keyword_auto,
                force=True,
            )
        except Exception:
            pass

    def test_edit_user_email(self):
        """Test basic user email attribute editing with UUID"""
        _provision_uuid_test_user(self.configuration, TEST_USER_DN)
        # Extract original for later verification
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        user_dict = pickled[TEST_USER_DN]

        # Edit user attribute and verify changed in DB
        changes = {
            "email": OTHER_USER_EMAIL,
        }
        removes = []
        edit_user(
            TEST_USER_DN, changes, removes, self.configuration, keyword_auto
        )
        edited_dn = TEST_USER_DN.replace(TEST_USER_EMAIL, OTHER_USER_EMAIL)
        # Verify changes
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        self.assertIn(edited_dn, pickled)
        edited_user = pickled[edited_dn]
        for field in user_dict:
            if field == "email":
                self.assertEqual(edited_user[field], OTHER_USER_EMAIL)
            elif field == "distinguished_name":
                self.assertEqual(edited_user[field], edited_dn)
            else:
                self.assertEqual(edited_user[field], user_dict[field])

        self._flush_test_user(edited_dn)

    def test_edit_user_remove_attributes(self):
        """Test removing user attributes with UUID"""
        _provision_uuid_test_user(self.configuration, TEST_USER_DN)
        # Extract original for later verification
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        user_dict = pickled[TEST_USER_DN]

        changes = {}
        removes = ["comment"]
        edit_user(
            TEST_USER_DN, changes, removes, self.configuration, keyword_auto,
            meta_only=True
        )

        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        edited_user = pickled[TEST_USER_DN]
        for field in user_dict:
            if field == "comment":
                self.assertNotIn(field, edited_user)
            else:
                self.assertEqual(edited_user[field], user_dict[field])

        self._flush_test_user(TEST_USER_DN)

    def test_edit_user_meta_only(self):
        """Test metadata-only update with UUID (no FS changes)"""
        _provision_uuid_test_user(self.configuration, TEST_USER_DN)
        # Extract original for later verification
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        user_dict = pickled[TEST_USER_DN]

        changes = {"comment": "meta comment"}
        removes = []
        edit_user(
            TEST_USER_DN, changes, removes, self.configuration, keyword_auto,
            meta_only=True
        )

        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        edited_user = pickled[TEST_USER_DN]
        for field in user_dict:
            if field == "comment":
                self.assertEqual(edited_user[field], "meta comment")
            else:
                self.assertEqual(edited_user[field], user_dict[field])

        self._flush_test_user(TEST_USER_DN)

    @unittest.skip("make backend function less noisy (traceback) and enable?")
    def test_edit_user_nonexistent(self):
        """Test editing nonexistent user"""
        changes = {"email": "dummy@example.com"}
        removes = []
        with self.assertRaises(Exception):
            edit_user(
                NO_SUCH_USER_DN, changes, removes, self.configuration,
                keyword_auto
            )

    @unittest.skip("make backend function less noisy (traceback) and enable?")
    def test_edit_user_nonexistent_force(self):
        """Test editing nonexistent user with force=True and UUID"""
        changes = {"email": "dummy@example.com"}
        removes = []
        # NOTE: forced edit logs errors in update_account_X functions
        self.logger.forgive_errors()
        with self.assertRaises(Exception):
            edit_user(
                NO_SUCH_USER_DN, changes, removes, self.configuration,
                keyword_auto, force=True
            )

    @unittest.skip("make backend function less noisy (traceback) and enable?")
    def test_edit_user_dn_collision_fails(self):
        """Test that editing a user to a DN that already exists fails with UUID"""
        _provision_uuid_test_user(self.configuration, TEST_USER_DN)
        _provision_uuid_test_user(self.configuration, OTHER_USER_DN)

        changes = distinguished_name_to_user(TEST_USER_DN)
        removes = []
        with self.assertRaises(Exception):
            edit_user(
                OTHER_USER_DN, changes, removes, self.configuration,
                keyword_auto
            )

        self._flush_test_user(TEST_USER_DN)
        self._flush_test_user(OTHER_USER_DN)

    def test_edit_user_renames_user(self):
        """Test editing fields that change the distinguished name with UUID"""
        _provision_uuid_test_user(self.configuration, TEST_USER_DN)
        # Extract original for later verification
        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        user_dict = pickled[TEST_USER_DN]

        changes = {"full_name": "Renamed User"}
        removes = []
        result = edit_user(
            TEST_USER_DN, changes, removes, self.configuration,
            keyword_auto
        )

        new_dn = result["distinguished_name"]
        new_link_dir = new_dn.replace("/", "+").replace(" ", "_")

        pickled = self.assertPickledFile(
            self.expected_user_db_file,
            apply_hints=["convert_dict_bytes_to_strings_kv"],
        )
        edited_user = pickled[new_dn]
        self.assertNotIn(TEST_USER_DN, pickled)
        self.assertIn(new_dn, pickled)
        for field in user_dict:
            if field == "full_name":
                self.assertEqual(edited_user[field], "Renamed User")
            elif field == "distinguished_name":
                self.assertEqual(edited_user[field], new_dn)
            else:
                self.assertEqual(edited_user[field], user_dict[field])

        old_link = os.path.join(
            self.configuration.user_home, TEST_USER_DIR)
        new_link = os.path.join(self.configuration.user_home, new_link_dir)
        real_home = os.path.join(
            self.configuration.user_home, user_dict['unique_id'])
        self.assertFalse(os.path.exists(old_link))
        self.assertTrue(os.path.islink(new_link))
        self.assertEqual(os.path.realpath(new_link),
                         os.path.realpath(real_home))
        self.assertTrue(os.path.isdir(real_home))

        self._flush_test_user(new_dn)


class TestMigSharedUseradm___get_required_user_dir_links(MigTestCase):
    """Coverage of useradm _get_required_user_dir_links function."""

    def _provide_configuration(self):
        return "testconfig"

    def test_get_required_user_dir_links_with_links(self):
        """Test _get_required_user_dir_links with link_dir provided"""
        configuration = self.configuration
        real_dir = "real_dir"
        link_dir = "link_dir"

        dir_links = _get_required_user_dir_links(
            configuration, real_dir, link_dir)

        expected = [
            (os.path.join(configuration.user_home, real_dir),
             os.path.join(configuration.user_home, link_dir)),
            (os.path.join(configuration.user_settings, real_dir),
             os.path.join(configuration.user_settings, link_dir)),
            (os.path.join(configuration.user_cache, real_dir),
             os.path.join(configuration.user_cache, link_dir)),
            (os.path.join(configuration.mrsl_files_dir, real_dir),
             os.path.join(configuration.mrsl_files_dir, link_dir)),
            (os.path.join(configuration.resource_pending, real_dir),
             os.path.join(configuration.resource_pending, link_dir))
        ]
        self.assertEqual(dir_links, expected)

    def test_get_required_user_dir_links_without_links(self):
        """Test _get_required_user_dir_links without link_dir provided"""
        configuration = self.configuration
        real_dir = "real_dir"

        dir_links = _get_required_user_dir_links(
            configuration, real_dir, False)

        expected = [
            (os.path.join(configuration.user_home, real_dir), False),
            (os.path.join(configuration.user_settings, real_dir), False),
            (os.path.join(configuration.user_cache, real_dir), False),
            (os.path.join(configuration.mrsl_files_dir, real_dir), False),
            (os.path.join(configuration.resource_pending, real_dir), False)
        ]
        self.assertEqual(dir_links, expected)


class TestMigSharedUseradm___get_required_user_alias_links(MigTestCase):
    """Coverage of useradm _get_required_user_alias_links function."""

    def _provide_configuration(self):
        return "testconfig"

    def test_get_required_user_alias_links_with_links(self):
        """Test _get_required_user_alias_links with link_dir provided"""
        configuration = self.configuration
        real_dir = "real_dir"
        link_dir = "link_dir"

        alias_links = _get_required_user_alias_links(configuration, real_dir,
                                                     link_dir)

        expected = [(link_dir, os.path.join(configuration.mig_system_run,
                                            user_id_alias_dir, real_dir))]
        self.assertEqual(alias_links, expected)

    def test_get_required_user_alias_links_without_links(self):
        """Test _get_required_user_alias_links without link_dir provided"""
        configuration = self.configuration
        real_dir = "real_dir"

        alias_links = _get_required_user_alias_links(configuration, real_dir,
                                                     False)

        self.assertEqual(alias_links, [(False, False)])


class TestMigSharedUseradm__lookup_client_id_from_uuid(MigTestCase):
    """Coverage of useradm lookup_client_id_from_uuid function."""

    def before_each(self):
        """Create test environment for useradm tests"""
        configuration = self.configuration
        configuration.site_user_id_format = UUID_USER_ID_FORMAT

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

    def test_lookup_client_id_from_uuid_via_alias_link(self):
        """Test lookup via existing alias link in mig_system_run"""
        configuration = self.configuration
        client_id = TEST_USER_DN
        user_id = TEST_USER_UUID
        # Setup real directory for the client and alias link in mig_system_run
        real_dir = os.path.join(configuration.user_home, user_id)
        ensure_dirs_exist(real_dir)
        alias_link = os.path.join(
            configuration.mig_system_run, user_id_alias_dir, user_id)
        ensure_dirs_exist(os.path.dirname(alias_link))
        client_dir = client_id_dir(client_id)
        os.symlink(client_dir, alias_link)

        result = lookup_client_id_from_uuid(configuration, user_id)
        self.assertEqual(result, client_id)

    def test_lookup_client_id_from_uuid_via_reverse_lookup(self):
        """Test lookup via reverse lookup in user_home (and writeback)"""
        configuration = self.configuration
        client_id = TEST_USER_DN
        user_id = TEST_USER_UUID
        # Setup real directory for the client and alias link in home
        real_dir = os.path.join(configuration.user_home, user_id)
        ensure_dirs_exist(real_dir)
        # This simulates an existing X509 alias link to uuid in user_home
        client_dir = client_id_dir(client_id)
        alias_link_in_home = os.path.join(configuration.user_home, client_dir)
        os.symlink(user_id, alias_link_in_home)

        result = lookup_client_id_from_uuid(configuration, user_id)
        self.assertEqual(result, client_id)

        # Verify writeback: check if alias link was created in mig_system_run
        alias_link_in_run = os.path.join(configuration.mig_system_run,
                                         user_id_alias_dir, user_id)
        self.assertTrue(os.path.islink(alias_link_in_run))
        link_target = os.path.basename(os.path.realpath(alias_link_in_run))
        self.assertEqual(link_target, client_dir)

    def test_lookup_client_id_from_uuid_fails_with_only_short_id_link(self):
        """Test lookup via reverse lookup in user_home fails on short id link"""
        configuration = self.configuration
        client_id = TEST_USER_DN
        user_id = TEST_USER_UUID
        # Setup real directory for the client and alias link in home
        real_dir = os.path.join(configuration.user_home, user_id)
        ensure_dirs_exist(real_dir)
        # This simulates an existing short id link to uuid in user_home
        short_id_link_in_home = os.path.join(configuration.user_home,
                                             TEST_USER_EMAIL)
        os.symlink(user_id, short_id_link_in_home)

        with self.assertLogs(level='ERROR') as log_capture:
            result = lookup_client_id_from_uuid(configuration, user_id)
            self.assertNotEqual(result, client_id)
            self.assertEqual(result, user_id)
        self.assertTrue(any('found no alias' in msg
                        for msg in log_capture.output))

    def test_lookup_client_id_from_uuid_not_found(self):
        """Test lookup when no alias or reverse link exists"""
        configuration = self.configuration
        client_id = NO_SUCH_USER_DN
        # Missing user will cause log error
        with self.assertLogs(level='ERROR') as log_capture:
            result = lookup_client_id_from_uuid(configuration, client_id)
            # Verify: should return the user_id itself if not found
            self.assertEqual(result, client_id)
        self.assertTrue(any('found no alias' in msg
                        for msg in log_capture.output))


class TestMigSharedUseradm__get_any_oid_user_dn(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin, UserAssertMixin
):
    """Unit tests for get_any_oid_user_dn with default user ID format."""

    def before_each(self):
        """Prepare a minimal configuration for the tests."""
        configuration = self.configuration
        # Use Default format for these tests
        configuration.site_user_id_format = DEFAULT_USER_ID_FORMAT
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

    def _flush_test_user(self, client_id):
        """Helper to force clean up after provisioned test users"""
        try:
            delete_user(
                {'distinguished_name': client_id},
                self.configuration,
                keyword_auto,
                force=True,
            )
        except Exception:
            pass

    def test_get_any_oid_user_dn_via_alias_link(self):
        """Return the distinguished name when a valid alias link exists."""
        client_id = TEST_USER_DN
        short_id = TEST_USER_EMAIL
        self._provision_test_user(self, client_id)

        # Make sure alias link is in place
        alias_link = os.path.join(self.configuration.user_home, short_id)
        client_dir = client_id_dir(client_id)
        os.symlink(client_dir, alias_link)

        # Call the function – it should resolve the alias to the client_id.
        result = get_any_oid_user_dn(self.configuration, raw_login=short_id,
                                     user_check=True, do_lock=True
                                     )
        self.assertEqual(result, client_id)
        self._flush_test_user(TEST_USER_DN)

    def test_get_any_oid_user_dn_not_found(self):
        """When no alias or reverse link exists, return an empty string."""
        # Missing user will cause log error
        with self.assertLogs(level='ERROR') as log_capture:
            result = get_any_oid_user_dn(self.configuration,
                                         raw_login="NoSuchUser",
                                         user_check=True, do_lock=True
                                         )
            self.assertEqual(result, "")
        self.assertTrue(any('no such openid user' in msg
                        for msg in log_capture.output))

    def test_get_any_oid_user_dn_direct_dn(self):
        """Return the distinguished name when a matching cert directory exists."""
        client_id = TEST_USER_DN
        self._provision_test_user(self, client_id)

        # The function should recognise the directory and return the client_id.
        result = get_any_oid_user_dn(self.configuration,
                                     raw_login=TEST_USER_DN,
                                     user_check=True, do_lock=True
                                     )
        self.assertEqual(result, client_id)
        self._flush_test_user(TEST_USER_DN)

    def test_get_any_oid_user_dn_user_check_false(self):
        """When user_check=False the function bypasses the user‑dir lookup."""
        raw_login = TEST_USER_SHORT_ID
        result = get_any_oid_user_dn(self.configuration, raw_login=raw_login,
                                     user_check=False, do_lock=True
                                     )
        self.assertEqual(result, raw_login)

# TODO: consider merging the tests for UUID and X509 format


class TestMigSharedUseradm__get_any_oid_user_dn_uuid_user_id(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin, UserAssertMixin
):
    """Unit tests for get_any_oid_user_dn with UUID user ID format."""

    def before_each(self):
        """Prepare a minimal configuration for the tests."""
        configuration = self.configuration
        # Use UUID format for the tests – the function works with both UUID and X509.
        configuration.site_user_id_format = UUID_USER_ID_FORMAT
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

    def _flush_test_user(self, client_id):
        """Helper to force clean up after provisioned test users"""
        try:
            delete_user(
                {'distinguished_name': client_id},
                self.configuration,
                keyword_auto,
                force=True,
            )
        except Exception:
            pass

    def test_get_any_oid_user_dn_via_lookup_link(self):
        """Return the distinguished name when a valid lookup link exists."""
        client_id = TEST_USER_DN
        user_dict = _provision_uuid_test_user(self.configuration, client_id)
        user_id = user_dict['unique_id']
        short_id = user_dict['short_id']

        # Make sure direct lookup link is in place
        lookup_link = os.path.join(self.configuration.mig_system_run,
                                   user_id_alias_dir, user_id)
        self.assertTrue(os.path.islink(lookup_link))

        # Call the function – it should resolve the lookup to the client_id.
        result = get_any_oid_user_dn(self.configuration, raw_login=short_id,
                                     user_check=True, do_lock=True
                                     )
        self._flush_test_user(TEST_USER_DN)
        self.assertEqual(result, client_id)

    def test_get_any_oid_user_dn_via_fallback_id_link(self):
        """Return the distinguished name when a valid fallback ID link exists."""
        client_id = TEST_USER_DN
        user_dict = _provision_uuid_test_user(self.configuration, client_id)
        user_id = user_dict['unique_id']
        short_id = user_dict['short_id']
        client_dir = client_id_dir(client_id)

        # Blow away direct lookup link to force alias lookup
        lookup_link = os.path.join(self.configuration.mig_system_run,
                                   user_id_alias_dir, user_id)
        if os.path.islink(lookup_link):
            os.remove(lookup_link)
        self.assertFalse(os.path.islink(lookup_link))

        # Make sure short alias, DN link and id dir are all in place
        alias_link = os.path.join(self.configuration.user_home, short_id)
        self.assertTrue(os.path.islink(alias_link))
        self.assertEqual(os.path.basename(os.path.realpath(alias_link)),
                         user_id)
        dn_link = os.path.join(self.configuration.user_home, client_dir)
        self.assertTrue(os.path.islink(dn_link))
        self.assertEqual(os.path.basename(os.path.realpath(dn_link)),
                         user_id)
        user_dir = os.path.join(self.configuration.user_home, user_id)
        self.assertTrue(os.path.isdir(user_dir))

        # Call the function – it should resolve the alias to the client_id.
        result = get_any_oid_user_dn(self.configuration, raw_login=short_id,
                                     user_check=True, do_lock=True
                                     )
        self._flush_test_user(TEST_USER_DN)
        self.assertEqual(result, client_id)

    def test_get_any_oid_user_dn_not_found(self):
        """When no alias or reverse link exists, return an empty string."""
        # Missing user will cause log error
        with self.assertLogs(level='ERROR') as log_capture:
            result = get_any_oid_user_dn(self.configuration,
                                         raw_login="NoSuchUser",
                                         user_check=True, do_lock=True
                                         )
            self.assertEqual(result, "")
        self.assertTrue(any('no such openid user' in msg
                        for msg in log_capture.output))

    def test_get_any_oid_user_id_direct_dn(self):
        """Return the distinguished name when a matching id directory exists."""
        client_id = TEST_USER_DN
        user_dict = _provision_uuid_test_user(self.configuration, client_id)
        user_id = user_dict['unique_id']
        short_id = user_dict['short_id']
        client_dir = client_id_dir(client_id)

        # Make sure no lookups links get in the way and that id dir is in place
        lookup_link = os.path.join(self.configuration.mig_system_run,
                                   user_id_alias_dir, user_id)
        os.remove(lookup_link)
        self.assertFalse(os.path.islink(lookup_link))
        alias_link = os.path.join(self.configuration.user_home, short_id)
        os.remove(alias_link)
        self.assertFalse(os.path.islink(alias_link))
        reverse_link = os.path.join(self.configuration.user_home, client_dir)
        os.remove(reverse_link)
        self.assertFalse(os.path.islink(reverse_link))
        user_dir = os.path.join(self.configuration.user_home, user_id)
        self.assertTrue(os.path.isdir(user_dir))

        # The function should recognise the directory and return the client_id.
        result = get_any_oid_user_dn(self.configuration,
                                     raw_login=user_id,
                                     user_check=True, do_lock=True
                                     )
        self._flush_test_user(TEST_USER_DN)
        self.assertEqual(result, user_id)

    def test_get_any_oid_user_dn_user_check_false(self):
        """When user_check=False the function bypasses the user‑dir lookup."""
        raw_login = TEST_USER_SHORT_ID
        result = get_any_oid_user_dn(self.configuration, raw_login=raw_login,
                                     user_check=False, do_lock=True
                                     )
        self.assertEqual(result, raw_login)

class TestMigSharedUseradm__get_any_oid_user_dn(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin, UserAssertMixin
):
    """Unit tests for get_any_oid_user_dn with default user ID format."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Prepare a minimal configuration for the tests."""
        configuration = self.configuration
        # Use Default format for these tests
        configuration.site_user_id_format = DEFAULT_USER_ID_FORMAT
        _ensure_dirs_needed_for_userdb(self.configuration)
        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        ensure_dirs_exist(self.configuration.mig_system_files)

    def test_get_any_oid_user_dn_via_alias_link(self):
        """Return the distinguished name when a valid alias link exists."""
        client_id = TEST_USER_DN
        short_id = TEST_USER_EMAIL
        self._provision_test_user(self, client_id)

        # Make sure alias link is in place
        alias_link = os.path.join(self.configuration.user_home, short_id)
        client_dir = client_id_dir(client_id)
        os.symlink(client_dir, alias_link)

        # Call the function – it should resolve the alias to the client_id.
        result = get_any_oid_user_dn(self.configuration, raw_login=short_id,
                                     user_check=True, do_lock=True
                                     )
        self.assertEqual(result, client_id)

    def test_get_any_oid_user_dn_not_found(self):
        """When no alias or reverse link exists, return an empty string."""
        # Missing user will cause log error
        self.logger.forgive_errors()
        result = get_any_oid_user_dn(self.configuration,
                                     raw_login="NoSuchUser",
                                     user_check=True, do_lock=True
                                     )
        self.assertEqual(result, "")

    def test_get_any_oid_user_dn_direct_dn(self):
        """Return the distinguished name when a matching cert directory exists."""
        client_id = TEST_USER_DN
        self._provision_test_user(self, client_id)

        # The function should recognise the directory and return the client_id.
        result = get_any_oid_user_dn(self.configuration,
                                     raw_login=TEST_USER_DN,
                                     user_check=True, do_lock=True
                                     )
        self.assertEqual(result, client_id)

    def test_get_any_oid_user_dn_user_check_false(self):
        """When user_check=False the function bypasses the user‑dir lookup."""
        raw_login = TEST_USER_SHORT_ID
        result = get_any_oid_user_dn(self.configuration, raw_login=raw_login,
                                     user_check=False, do_lock=True
                                     )
        self.assertEqual(result, raw_login)

# TODO: consider merging the tests for UUID and X509 format


class TestMigSharedUseradm__get_any_oid_user_dn_uuid_user_id(
    MigTestCase, FixtureAssertMixin, PickleAssertMixin, UserAssertMixin
):
    """Unit tests for get_any_oid_user_dn with UUID user ID format."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Prepare a minimal configuration for the tests."""
        configuration = self.configuration
        # Use UUID format for the tests – the function works with both UUID and X509.
        configuration.site_user_id_format = UUID_USER_ID_FORMAT
        _ensure_dirs_needed_for_userdb(self.configuration)
        self.expected_user_db_home = os.path.normpath(
            configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        ensure_dirs_exist(self.configuration.mig_system_files)

    def test_get_any_oid_user_dn_via_alias_link(self):
        """Return the distinguished name when a valid alias link exists."""
        client_id = TEST_USER_DN
        user_dict = _provision_uuid_test_user(self.configuration, client_id)
        user_id = user_dict['unique_id']
        short_id = user_dict['short_id']

        # Make sure direct lookup link is in place
        lookup_link = os.path.join(self.configuration.mig_system_run,
                                   user_id_alias_dir, user_id)
        self.assertTrue(os.path.islink(lookup_link))

        # Call the function – it should resolve the alias to the client_id.
        result = get_any_oid_user_dn(self.configuration, raw_login=short_id,
                                     user_check=True, do_lock=True
                                     )
        self.assertEqual(result, client_id)

    def test_get_any_oid_user_dn_via_reverse_lookup(self):
        """Return the distinguished name when a reverse‑lookup symlink exists."""
        client_id = TEST_USER_DN
        user_dict = _provision_uuid_test_user(self.configuration, client_id)
        user_id = user_dict['unique_id']
        short_id = user_dict['short_id']

        # Blow away direct lookup link to force reverse lookup
        lookup_link = os.path.join(self.configuration.mig_system_run,
                                   user_id_alias_dir, user_id)
        if os.path.islink(lookup_link):
            os.remove(lookup_link)
        self.assertFalse(os.path.islink(lookup_link))

        # The function should find the client_id via the reverse lookup.
        result = get_any_oid_user_dn(self.configuration, raw_login=short_id,
                                     user_check=True, do_lock=True
                                     )
        self.assertEqual(result, client_id)

    def test_get_any_oid_user_dn_not_found(self):
        """When no alias or reverse link exists, return an empty string."""
        # Missing user will cause log error
        self.logger.forgive_errors()
        result = get_any_oid_user_dn(self.configuration,
                                     raw_login="NoSuchUser",
                                     user_check=True, do_lock=True
                                     )
        self.assertEqual(result, "")

    def test_get_any_oid_user_dn_direct_dn(self):
        """Return the distinguished name when a matching cert directory exists."""
        user_id = TEST_USER_UUID

        # Create a cert directory user_home/<user_id> that the function
        # can see.
        home_dir = os.path.join(self.configuration.user_home, user_id)
        ensure_dirs_exist(home_dir)

        # The function should recognise the directory and return the client_id.
        result = get_any_oid_user_dn(self.configuration,
                                     raw_login=TEST_USER_UUID,
                                     user_check=True, do_lock=True
                                     )
        self.assertEqual(result, user_id)

    def test_get_any_oid_user_dn_user_check_false(self):
        """When user_check=False the function bypasses the user‑dir lookup."""
        raw_login = TEST_USER_SHORT_ID
        result = get_any_oid_user_dn(self.configuration, raw_login=raw_login,
                                     user_check=False, do_lock=True
                                     )
        self.assertEqual(result, raw_login)


if __name__ == "__main__":
    testmain()
