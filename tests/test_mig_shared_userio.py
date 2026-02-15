# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_userio - test module of same name
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
import sys
import unittest
from past.builtins import basestring, unicode

from tests.support import MigTestCase, testmain, ensure_dirs_exist

from mig.shared.userio import ACTIONS, CREATE, MODIFY, MOVE, DELETE, \
    DEFAULT_COMPRESS, get_home_location, get_trash_location, _check_access, \
    _get_compression_helpers, _build_changes_path, _fill_changes, \
    prepare_changes, commit_changes, abort_changes, delete_path, remove_path, \
    touch_path, __make_test_files, __clean_test_files, main as userio_main
from mig.shared.vgrid import vgrid_set_entities


# Constants from tests/test_mig_lib_janitor.py
DUMMY_USER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
DUMMY_CLIENT_DIR = '+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=test@example.com'
TEST_VGRID_NAME = 'testvgrid'
TEST_OWNER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test Owner/emailAddress=owner@example.org'
MODIFY_ACTION = 'modify'


class TestMigSharedUserIO_main(MigTestCase):
    """Unit tests for userio related helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    # TODO: migrate to support as _provision_vgrid or similar
    def _create_vgrid(self, vgrid_name, owners=None, members=None,
                      resources=None, settings=None, triggers=None):
        """Helper to create valid skeleton vgrid for testing"""
        for vgrid_base in (self.configuration.vgrid_home,
                           self.configuration.vgrid_files_home,
                           self.configuration.vgrid_files_writable,
                           self.configuration.vgrid_files_readonly,
                           self.configuration.vgrid_private_base,
                           self.configuration.vgrid_public_base, ):
            vgrid_path = os.path.join(vgrid_base, vgrid_name)
            ensure_dirs_exist(vgrid_path)
        # Save vgrid owners, members, resources, settings and triggers
        if owners is None:
            owners = []
        success_and_msg = vgrid_set_entities(self.configuration, vgrid_name,
                                             'owners', owners, allow_empty=True)
        self.assertEqual(success_and_msg, (True, ""))
        if members is None:
            members = []
        success_and_msg = vgrid_set_entities(self.configuration, vgrid_name,
                                             'members', members,
                                             allow_empty=True)
        self.assertEqual(success_and_msg, (True, ""))
        if resources is None:
            resources = []
        success_and_msg = vgrid_set_entities(self.configuration, vgrid_name,
                                             'resources', resources,
                                             allow_empty=True)
        self.assertEqual(success_and_msg, (True, ""))
        if settings is None:
            settings = [('vgrid_name', vgrid_name)]
        success_and_msg = vgrid_set_entities(self.configuration, vgrid_name,
                                             'settings', settings,
                                             allow_empty=True)
        self.assertEqual(success_and_msg, (True, ""))
        if triggers is None:
            triggers = []
        success_and_msg = vgrid_set_entities(self.configuration, vgrid_name,
                                             'triggers', triggers,
                                             allow_empty=True)
        self.assertEqual(success_and_msg, (True, ""))

    def before_each(self):
        """Setup test environment before each test method"""
        ensure_dirs_exist(self.configuration.user_db_home)
        ensure_dirs_exist(self.configuration.user_home)
        ensure_dirs_exist(self.configuration.freeze_home)
        ensure_dirs_exist(self.configuration.vgrid_home)
        ensure_dirs_exist(self.configuration.vgrid_files_home)
        ensure_dirs_exist(self.configuration.vgrid_files_writable)
        ensure_dirs_exist(self.configuration.vgrid_files_readonly)

    def test_constants(self):
        """Test constants are defined correctly"""
        self.assertEqual(ACTIONS, ("create", "modify", "move", "delete"))
        self.assertEqual(CREATE, "create")
        self.assertEqual(MODIFY, "modify")
        self.assertEqual(MOVE, "move")
        self.assertEqual(DELETE, "delete")
        self.assertEqual(DEFAULT_COMPRESS, 'bz2')

    def test_get_home_location_user_home(self):
        """Test get_home_location with user_home path"""
        self._provision_test_user(self, DUMMY_USER_DN)
        user_path = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, 'file.txt')
        with open(user_path, "w") as fd:
            fd.close()
        result = get_home_location(self.configuration, user_path)
        expected = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR)
        self.assertEqual(result, expected)

    def test_get_home_location_vgrid_files_home(self):
        """Test get_home_location with vgrid_files_home path"""
        self._create_vgrid(TEST_VGRID_NAME, [TEST_OWNER_DN])
        vgrid_path = os.path.join(
            self.configuration.vgrid_files_home, TEST_VGRID_NAME, 'file.txt')
        with open(vgrid_path, "w") as fd:
            fd.close()
        result = get_home_location(self.configuration, vgrid_path)
        expected = os.path.join(
            self.configuration.vgrid_files_home, TEST_VGRID_NAME)
        self.assertEqual(result, expected)

    @unittest.skip("TODO: fix read-only mount/copy of vgrid_files_writable and enable")
    def test_get_home_location_vgrid_files_writable(self):
        """Test get_home_location with vgrid_files_writable path"""
        self._create_vgrid(TEST_VGRID_NAME, [TEST_OWNER_DN])
        writable_path = os.path.join(
            self.configuration.vgrid_files_writable, TEST_VGRID_NAME, 'file.txt')
        with open(writable_path, "w") as fd:
            fd.close()
        # NOTE: mimic proper read-only support with a copy and permissions
        readonly_path = os.path.join(
            self.configuration.vgrid_files_readonly, TEST_VGRID_NAME, 'file.txt')
        with open(readonly_path, "w") as fd:
            fd.close()
        os.chmod(readonly_path, 0o400)
        os.chmod(os.path.dirname(readonly_path), 0o500)

        result = get_home_location(self.configuration, writable_path)
        expected = os.path.join(
            self.configuration.vgrid_files_writable, TEST_VGRID_NAME)
        # Allow clean up
        os.chmod(os.path.dirname(readonly_path), 0o700)
        self.assertEqual(result, expected)

    def test_get_home_location_vgrid_private_base(self):
        """Test get_home_location with vgrid_private_base path"""
        self._create_vgrid(TEST_VGRID_NAME, [TEST_OWNER_DN])
        priv_path = os.path.join(
            self.configuration.vgrid_private_base, TEST_VGRID_NAME, 'file.txt')
        with open(priv_path, "w") as fd:
            fd.close()
        result = get_home_location(self.configuration, priv_path)
        expected = os.path.join(
            self.configuration.vgrid_private_base, TEST_VGRID_NAME)
        self.assertEqual(result, expected)

    def test_get_home_location_vgrid_public_base(self):
        """Test get_home_location with vgrid_public_base path"""
        self._create_vgrid(TEST_VGRID_NAME, [TEST_OWNER_DN])
        pub_path = os.path.join(
            self.configuration.vgrid_public_base, TEST_VGRID_NAME, 'file.txt')
        with open(pub_path, "w") as fd:
            fd.close()
        result = get_home_location(self.configuration, pub_path)
        expected = os.path.join(
            self.configuration.vgrid_public_base, TEST_VGRID_NAME)
        self.assertEqual(result, expected)

    def test_get_home_location_invalid_path(self):
        """Test get_home_location with invalid path"""
        invalid_path = '/invalid/path/file.txt'
        result = get_home_location(self.configuration, invalid_path)
        self.assertIsNone(result)

    def test_get_trash_location_visible_link_false(self):
        """Test get_trash_location with visible_link=False"""
        self._provision_test_user(self, DUMMY_USER_DN)
        test_path = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, 'file.txt')
        result = get_trash_location(self.configuration, test_path)
        expected = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, '.trash')
        self.assertEqual(result, expected)

    def test_get_trash_location_visible_link_true(self):
        """Test get_trash_location with visible_link=True"""
        self._provision_test_user(self, DUMMY_USER_DN)
        test_path = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, 'file.txt')
        result = get_trash_location(self.configuration, test_path, True)
        expected = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, 'Trash')
        self.assertEqual(result, expected)

    def test_get_trash_location_vgrid_path(self):
        """Test get_trash_location with vgrid path"""
        self._create_vgrid(TEST_VGRID_NAME, [TEST_OWNER_DN])
        vgrid_path = os.path.join(
            self.configuration.vgrid_files_home, TEST_VGRID_NAME, 'file.txt')
        result = get_trash_location(self.configuration, vgrid_path)
        expected = os.path.join(
            self.configuration.vgrid_files_home, TEST_VGRID_NAME, '.trash')
        self.assertEqual(result, expected)

    def test__get_compression_helpers_none(self):
        """Test _get_compression_helpers with None"""
        open_func, ext = _get_compression_helpers(self.configuration, None)
        self.assertEqual(open_func, open)
        self.assertEqual(ext, '')

    def test__get_compression_helpers_gzip(self):
        """Test _get_compression_helpers with gzip"""
        open_func, ext = _get_compression_helpers(self.configuration, 'gzip')
        self.assertEqual(ext, '.gz')

    def test__get_compression_helpers_bz2(self):
        """Test _get_compression_helpers with bz2"""
        open_func, ext = _get_compression_helpers(self.configuration, 'bz2')
        self.assertEqual(ext, '.bz2')

    def test__get_compression_helpers_invalid(self):
        """Test _get_compression_helpers with invalid"""
        with self.assertRaises(ValueError):
            _get_compression_helpers(self.configuration, 'invalid')

    def test__build_changes_path_pending_false(self):
        """Test _build_changes_path with pending=False"""
        changeset = 'test-changeset'
        path = _build_changes_path(self.configuration, changeset)
        expected = os.path.join(
            self.configuration.events_home,
            "%s-%s.bz2" % (self.configuration.mig_server_id, changeset))
        self.assertEqual(path, expected)

    def test__build_changes_path_pending_true(self):
        """Test _build_changes_path with pending=True"""
        changeset = 'test-changeset'
        path = _build_changes_path(
            self.configuration, changeset, pending=True)
        expected = os.path.join(
            self.configuration.events_home,
            ".%s-%s-pending.bz2" % (self.configuration.mig_server_id, changeset))
        self.assertEqual(path, expected)

    def test__build_changes_path_compress_none(self):
        """Test _build_changes_path with compress=None"""
        changeset = 'test-changeset'
        path = _build_changes_path(
            self.configuration, changeset, compress=None)
        expected = os.path.join(
            self.configuration.events_home,
            "%s-%s" % (self.configuration.mig_server_id, changeset))
        self.assertEqual(path, expected)

    def test__check_access_valid_path(self):
        """Test _check_access with valid path"""
        self._provision_test_user(self, DUMMY_USER_DN)
        valid_path = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, 'valid.txt')
        try:
            _check_access(self.configuration, MODIFY_ACTION, [valid_path])
        except ValueError:
            self.fail("Unexpected ValueError for valid path")

    def test__check_access_invisible_path(self):
        """Test _check_access with invisible path"""
        self._provision_test_user(self, DUMMY_USER_DN)
        invisible_path = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, '.htaccess')
        with self.assertRaises(ValueError):
            _check_access(self.configuration, MODIFY_ACTION, [invisible_path])

    def test__check_access_symlink_path_modify_rejected(self):
        """Test _check_access with symlink path"""
        self._provision_test_user(self, DUMMY_USER_DN)
        symlink_src = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR)
        symlink_dst = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, 'link')
        os.symlink(symlink_src, symlink_dst)
        with self.assertRaises(ValueError):
            _check_access(self.configuration, MODIFY_ACTION, [symlink_dst])
        os.remove(symlink_dst)


class TestMigSharedUserIO__legacy(MigTestCase):
    """Legacy tests for safeinput module self-checks"""

    # TODO: migrate all legacy self-check functionality into the above?
    def test_existing_main(self):
        def raise_on_error_exit(exit_code):
            if exit_code != 0:
                if raise_on_error_exit.last_print is not None:
                    identifying_message = raise_on_error_exit.last_print
                else:
                    identifying_message = 'unknown'
                raise AssertionError(
                    'failure in unittest/testcore: %s' % (identifying_message,))
        raise_on_error_exit.last_print = None

        def record_last_print(value):
            raise_on_error_exit.last_print = value

        userio_main(_exit=raise_on_error_exit, _print=record_last_print)


if __name__ == '__main__':
    testmain()
