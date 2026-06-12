#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_griddaemons - unit tests for the griddaemons helper functions
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# --- END_HEADER ---
#

"""Unit tests for the griddaemons helper functions"""

import binascii
import os
import time
import unittest

# Imports required for the unit test wrapping
from mig.shared.base import client_id_dir, distinguished_name_to_user
from mig.shared.defaults import (
    X509_USER_ID_FORMAT, UUID_USER_ID_FORMAT,
    READ_WRITE_ACCESS, READ_ONLY_ACCESS, WRITE_ONLY_ACCESS,
    keyword_auto
)
from mig.shared.useradm import (
    _ensure_dirs_needed_for_userdb, create_user  # , generate_password_hash
)

# Imports of the code under test
from mig.shared.griddaemons.login import (
    Login, get_creds_changes, get_share_changes, get_job_changes,
    refresh_share_creds, refresh_user_creds
)

# Imports required for the unit tests themselves
from tests.support import (
    ensure_dirs_exist, MigTestCase, temppath, UserAssertMixin
)
from tests.support.usersupp import (
    TEST_USER_DN
)

TEST_USER_UUID = "UniqueUserIdForTestUser"
TEST_USER_SHORT_ID = "abc123@some.org"
TEST_USER_EMAIL = TEST_USER_DN.split("/emailAddress=", 1)[-1]
TEST_RO_SHARE_ID = 'abcdef1234'
TEST_RW_SHARE_ID = 'klmnop4567'
TEST_WO_SHARE_ID = 'uvwxyz7890'

# NOTE: this is a sample valid but unused ssh public key as it must be parsable
TEST_USER_PUB_KEY = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCuJrICshi7S2KhV03qvgNVOx5ejmHsswdGbvR34wf+eN23Ghq6OZhwGye2S+J6LPVFI3p4SCqxX4URnUM8BRAsiuvbf/+GQfE2pAO0C+/g4V3hhYbYzIyrtPsP1Hl8GioxvZD5nDoLEA4TWokDC4D7SRfv+NEkFLplyVBwHtpUunXBS/zXYdQ4lgk7u8HBBCMqUGbZHfCc+6ibFVn/5WS6vVokL+fSWtxg9tUVWqsS/xtDGPH1wbJUf1Dm3D58KmdX8ca73tBoScwH8qUQwEcyM1JtWtbv1BAZFb+Qk6SEe4GPRsn3I4AAgC7xtU3HKQsiqe8Fzpick/uI5PU+vguitcV/9+AASnGVZJ9M+a63UvlFFloEYcI1LwdZ03JYPQXfXCzJSYiA+pTX4/cf10G4rlxsque4m4OcuCwLKvpTWA/Lla+UJqYhdQW+m7mSizPRoDPgh8mOta1PQob2sGSw8rhqLfApptAPZ0mkN0QY3Dv3i3ItgpYGcPNVXVdjmhU='
# NOTE: this is a sample valid but unused ssh password hash as it must be parsable
TEST_USER_PW_HASH = "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM1234uxi"


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


def _prepare_auth_files(home_path, auth_protos=None):
    """Helper to create helper auth files for on eor more auth_protos.
    If None is passed ssh, ftps and davs auth files will be made.
    """
    auth_files = []
    if auth_protos is None:
        auth_protos = ['davs', 'ftps', 'ssh']

    # Create requested auth dirs with files
    for auth in auth_protos:
        # Create a .PROTO directory with authorized_X file(s)
        dot_proto_dir = os.path.join(home_path, '.%s' % auth)
        ensure_dirs_exist(dot_proto_dir)
        if auth == 'ssh':
            authkeys_path = os.path.join(dot_proto_dir, 'authorized_keys')
            with open(authkeys_path, 'w') as creds_fd:
                creds_fd.write(TEST_USER_PUB_KEY)
            auth_files.append(authkeys_path)

        authpasswords_path = os.path.join(dot_proto_dir,
                                          'authorized_passwords')
        with open(authpasswords_path, 'w') as creds_fd:
            creds_fd.write(TEST_USER_PW_HASH)
        auth_files.append(authpasswords_path)
    return auth_files


class MigSharedGriddaemonsLogin__get_creds_changes(MigTestCase):
    """Unit tests for griddaemons login get_creds_changes function"""

    def _provide_configuration(self):
        """Return a test configuration instance"""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        _ensure_dirs_needed_for_userdb(self.configuration)
        ensure_dirs_exist(self.configuration.sharelink_home)

        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf['time_stamp'] = 0
        self.configuration.daemon_conf['users'] = []
        self.configuration.daemon_conf['allow_publickey'] = True
        self.configuration.daemon_conf['allow_password'] = True
        # TODO: enable and test unsafe digest auth, too?
        # self.configuration.daemon_conf['allow_digest'] = True
        self.configuration.daemon_conf['allow_digest'] = False

        self.test_user_home = self._provision_test_user(self, TEST_USER_DN)
        auth_files = _prepare_auth_files(self.test_user_home, ['ssh'])
        self.auth_keys_path, self.auth_passwords_path = auth_files
        self.auth_digests_path = None

    def test_get_creds_changes_detects_new_files(self):
        """Verify that new credential files are detected as changes"""
        daemon_conf = self.configuration.daemon_conf

        # Create a dummy user with a last_update in the past
        past_timestamp = time.time() - 3600
        dummy_user = Login(
            configuration=self.configuration,
            username=TEST_USER_SHORT_ID,
            home=self.test_user_home,
            password=TEST_USER_PW_HASH,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None
        )
        dummy_user.last_update = past_timestamp
        daemon_conf['users'].append(dummy_user)

        changed_paths = get_creds_changes(
            daemon_conf,
            'user',
            self.auth_keys_path,
            self.auth_passwords_path,
            self.auth_digests_path
        )

        self.assertIn(self.auth_keys_path, changed_paths)
        self.assertIn(self.auth_passwords_path, changed_paths)
        # self.assertIn(self.auth_digests_path, changed_paths)

    def test_get_creds_changes_no_changes(self):
        """Verify that unchanged credential files return an empty list"""
        daemon_conf = self.configuration.daemon_conf

        # Set the file modification times to now
        current_time = time.time()

        # Create a dummy user with last_update matching the file mtime
        dummy_user = Login(
            configuration=self.configuration,
            username=TEST_USER_SHORT_ID,
            home=self.test_user_home,
            password=TEST_USER_PW_HASH,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None
        )
        dummy_user.last_update = current_time
        daemon_conf['users'].append(dummy_user)

        changed_paths = get_creds_changes(
            daemon_conf,
            TEST_USER_SHORT_ID,
            self.auth_keys_path,
            self.auth_passwords_path,
            self.auth_digests_path
        )

        self.assertEqual(len(changed_paths), 0)


class MigSharedGriddaemonsLogin__get_share_changes(MigTestCase):
    """Unit tests for griddaemons login get_share_changes helper function"""

    def _provide_configuration(self):
        """Return a test configuration instance"""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        _ensure_dirs_needed_for_userdb(self.configuration)
        self.ro_share_home = os.path.join(self.configuration.sharelink_home,
                                          'read-only')
        self.rw_share_home = os.path.join(self.configuration.sharelink_home,
                                          'read-write')
        self.wo_share_home = os.path.join(self.configuration.sharelink_home,
                                          'write-only')
        ensure_dirs_exist(self.ro_share_home)
        ensure_dirs_exist(self.rw_share_home)
        ensure_dirs_exist(self.wo_share_home)

        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf['time_stamp'] = 0
        self.configuration.daemon_conf['shares'] = []

        # TODO: enable and test unsafe digest auth, too?
        # self.configuration.daemon_conf['allow_digest'] = True
        self.configuration.daemon_conf['allow_digest'] = False

        self.auth_keys_path = temppath('authorized_keys', self)
        self.auth_passwords_path = temppath('authorized_passwords', self)
        # self.auth_digests_path = temppath('authhorized_digests', self)
        self.auth_digests_path = None

        # Create sample credential files
        with open(self.auth_keys_path, 'w') as creds_fd:
            creds_fd.write(TEST_USER_PUB_KEY)
        with open(self.auth_passwords_path, 'w') as creds_fd:
            creds_fd.write(TEST_USER_PW_HASH)
        # with open(self.auth_digests_path, 'w') as creds_fd:
        #    creds_fd.write(TEST_USER_DIGEST)

    def test_get_share_changes_detects_updates(self):
        """Verify that share link and key file changes are detected"""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf['allow_publickey'] = True

        user_shared_dir = os.path.join(self.configuration.user_home,
                                       'TestUser', 'shared', 'data')
        ensure_dirs_exist(user_shared_dir)
        user_shared_keys = os.path.join(user_shared_dir, '.ssh',
                                        'authorized_keys')
        share_link_path = os.path.join(self.ro_share_home, TEST_RO_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        # Create a dummy share with a last_update in the past
        past_timestamp = time.time() - 3600
        dummy_share = Login(
            configuration=self.configuration,
            username=TEST_RO_SHARE_ID,
            home='share_home',
            password=TEST_USER_PW_HASH,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None
        )
        dummy_share.last_update = past_timestamp
        daemon_conf['shares'].append(dummy_share)

        changed_paths = get_share_changes(
            daemon_conf,
            TEST_RO_SHARE_ID,
            share_link_path,
            user_shared_keys
        )

        self.assertIn(share_link_path, changed_paths)
        self.assertIn(user_shared_keys, changed_paths)

    def test_get_share_changes_new_share(self):
        """Verify that a new share link is detected as a change"""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf['allow_publickey'] = True

        user_shared_dir = os.path.join(self.configuration.user_home,
                                       'TestUser', 'shared', 'data')
        ensure_dirs_exist(user_shared_dir)
        share_link_path = os.path.join(self.ro_share_home, TEST_RO_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        changed_paths = get_share_changes(
            daemon_conf,
            TEST_RO_SHARE_ID,
            share_link_path,
            self.auth_keys_path
        )

        self.assertIn(share_link_path, changed_paths)
        self.assertIn(self.auth_keys_path, changed_paths)

    def test_get_share_changes_no_changes(self):
        """Verify that unchanged share files return an empty list"""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf['allow_publickey'] = True

        user_shared_dir = os.path.join(self.configuration.user_home,
                                       'TestUser', 'shared', 'data')
        ensure_dirs_exist(user_shared_dir)
        user_shared_keys = os.path.join(user_shared_dir, '.ssh',
                                        'authorized_keys')
        ensure_dirs_exist(user_shared_keys)
        share_link_path = os.path.join(self.ro_share_home, TEST_RO_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        # Create a dummy share with last_update matching file mtime
        current_time = time.time()
        dummy_share = Login(
            configuration=self.configuration,
            username=TEST_RO_SHARE_ID,
            home='share_home',
            password=TEST_USER_PW_HASH,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None
        )
        dummy_share.last_update = current_time
        daemon_conf['shares'].append(dummy_share)

        changed_paths = get_share_changes(
            daemon_conf,
            TEST_RO_SHARE_ID,
            share_link_path,
            user_shared_keys
        )

        self.assertEqual(len(changed_paths), 0)


class MigSharedGriddaemonsLogin__get_job_changes(MigTestCase):
    """Unit tests for griddaemons login get_job_changes function"""

    def _provide_configuration(self):
        """Return a test configuration instance"""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        _ensure_dirs_needed_for_userdb(self.configuration)
        ensure_dirs_exist(self.configuration.sharelink_home)

        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf['time_stamp'] = 0
        self.configuration.daemon_conf['jobs'] = []

        # TODO: enable and test unsafe digest auth, too?
        # self.configuration.daemon_conf['allow_digest'] = True
        self.configuration.daemon_conf['allow_digest'] = False

        self.auth_keys_path = temppath('authorized_keys', self)
        self.auth_passwords_path = temppath('authorized_passwords', self)
        # self.auth_digests_path = temppath('authhorized_digests', self)
        self.auth_digests_path = None

        # Create sample credential files
        with open(self.auth_keys_path, 'w') as creds_fd:
            creds_fd.write(TEST_USER_PUB_KEY)
        with open(self.auth_passwords_path, 'w') as creds_fd:
            creds_fd.write(TEST_USER_PW_HASH)
        # with open(self.auth_digests_path, 'w') as creds_fd:
        #    creds_fd.write(TEST_USER_DIGEST)

    def test_get_job_changes_new_job(self):
        """Verify that a new job mrsl file is detected as a change"""
        daemon_conf = self.configuration.daemon_conf

        mrsl_path = temppath('test_job.mRSL', self)
        with open(mrsl_path, 'w') as mrsl_fd:
            mrsl_fd.write('test content')

        changed_paths = get_job_changes(
            daemon_conf,
            'test_session_id',
            mrsl_path
        )

        self.assertIn(mrsl_path, changed_paths)

    def test_get_job_changes_no_changes(self):
        """Verify that unchanged job mrsl file returns an empty list"""
        daemon_conf = self.configuration.daemon_conf

        mrsl_path = temppath('test_job.mRSL', self)
        with open(mrsl_path, 'w') as mrsl_fd:
            mrsl_fd.write('test content')

        # Create a dummy job with last_update matching file mtime
        current_time = time.time()
        dummy_job = Login(
            configuration=self.configuration,
            username='test_session_id',
            home='job_home',
            password=None,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None
        )
        dummy_job.last_update = current_time
        daemon_conf['jobs'].append(dummy_job)

        changed_paths = get_job_changes(
            daemon_conf,
            'test_session_id',
            mrsl_path
        )

        self.assertEqual(len(changed_paths), 0)

    def test_get_job_changes_missing_file(self):
        """Verify that missing mrsl file is detected for existing job"""
        daemon_conf = self.configuration.daemon_conf

        # Create a dummy job
        dummy_job = Login(
            configuration=self.configuration,
            username='test_session_id',
            home='job_home',
            password=None,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None
        )
        daemon_conf['jobs'].append(dummy_job)

        mrsl_path = temppath('missing_job.mRSL', self)

        changed_paths = get_job_changes(
            daemon_conf,
            'test_session_id',
            mrsl_path
        )

        self.assertIn(mrsl_path, changed_paths)


class MigSharedGriddaemonsLogin__refresh_share_creds(MigTestCase):
    """Unit tests for the griddaemons login refresh_share_creds helper."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test."""
        # The base class already creates the required directory layout.
        # Ensure the share‑link home exists – it is used by refresh_share_creds.
        self.ro_share_home = os.path.join(self.configuration.sharelink_home,
                                          'read-only')
        self.rw_share_home = os.path.join(self.configuration.sharelink_home,
                                          'read-write')
        self.wo_share_home = os.path.join(self.configuration.sharelink_home,
                                          'write-only')
        ensure_dirs_exist(self.ro_share_home)
        ensure_dirs_exist(self.rw_share_home)
        ensure_dirs_exist(self.wo_share_home)

        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf['time_stamp'] = 0
        self.configuration.daemon_conf['shares'] = []
        self.configuration.daemon_conf['allow_publickey'] = True
        self.configuration.daemon_conf['allow_password'] = True
        self.configuration.daemon_conf['allow_digest'] = False

        # Paths that the function will look at
        self.auth_keys_path = temppath('authorized_keys', self)
        self.auth_passwords_path = temppath('authorized_passwords', self)
        self.auth_digests_path = None

        # Create dummy credential files
        with open(self.auth_keys_path, 'w') as creds_fd:
            creds_fd.write(TEST_USER_PUB_KEY)
        with open(self.auth_passwords_path, 'w') as creds_fd:
            creds_fd.write(TEST_USER_PW_HASH)

    def test_refresh_share_creds_adds_new_share(self):
        """A new share link should be added to daemon_conf['shares']."""
        # Build a share link that points to a temporary user directory
        rel_share_home = os.path.join('TestUser', 'shared', 'data')
        user_shared_dir = os.path.join(self.configuration.user_home,
                                       rel_share_home)
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        # Call the function under test
        # NOTE: only sftp access is supported for now
        (updated_conf, changed_shares) = refresh_share_creds(
            configuration=self.configuration,
            protocol='sftp',
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS, )
        )

        # The share should now be present in the changed list
        self.assertIn(TEST_RW_SHARE_ID, changed_shares)

        # Verify that a Login object was added to shares
        share_login = [
            obj for obj in updated_conf['shares']
            if obj.username == TEST_RW_SHARE_ID
        ]
        self.assertEqual(len(share_login), 1)

        # The added object should contain the expected home directory
        self.assertEqual(share_login[0].username, TEST_RW_SHARE_ID)
        self.assertEqual(share_login[0].home, rel_share_home)
        # TODO: check password hash, too?
        # share_pw_hash = generate_password_hash(self.configuration,
        #                                       TEST_RW_SHARE_ID)
        # self.assertEqual(share_login[0].password, share_pw_hash)

    def test_refresh_share_creds_adds_new_share_with_key(self):
        """A new share link with key should be added twice to daemon_conf['shares']."""
        # Build a share link that points to a temporary user directory
        rel_share_home = os.path.join('TestUser', 'shared', 'data')
        user_shared_dir = os.path.join(self.configuration.user_home,
                                       rel_share_home)
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        _prepare_auth_files(user_shared_dir, ['ssh'])

        # Call the function under test
        # NOTE: only sftp access is supported for now
        (updated_conf, changed_shares) = refresh_share_creds(
            configuration=self.configuration,
            protocol='sftp',
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS, )
        )

        # The share should now be present twice in the changed list
        self.assertIn(TEST_RW_SHARE_ID, changed_shares)

        # Verify that a Login object was added to shares
        share_login = [
            obj for obj in updated_conf['shares']
            if obj.username == TEST_RW_SHARE_ID
        ]
        self.assertEqual(len(share_login), 2)

        # The added objects should contain the expected home directory
        self.assertEqual(share_login[0].username, TEST_RW_SHARE_ID)
        self.assertEqual(share_login[0].home, rel_share_home)
        self.assertEqual(share_login[1].username, TEST_RW_SHARE_ID)
        self.assertEqual(share_login[1].home, rel_share_home)
        # TODO: check password hash, too?
        # share_pw_hash = generate_password_hash(self.configuration,
        #                                       TEST_RW_SHARE_ID)
        # self.assertEqual(share_login[0].password, share_pw_hash)
        # Convert saved paramiko.PKey back to openssh pub key format and check
        login_key = share_login[1].public_key
        result = "%s %s" % (login_key.get_name(), login_key.get_base64())
        self.assertEqual(result, TEST_USER_PUB_KEY)

    def test_refresh_share_creds_no_changes(self):
        """When the share link and its key file have not changed, the function
        should return an empty changed_shares list."""
        daemon_conf = self.configuration.daemon_conf

        # Create a share link that already exists
        rel_share_home = os.path.join('TestUser', 'shared', 'data')
        user_shared_dir = os.path.join(self.configuration.user_home,
                                       rel_share_home)
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        # Populate shares with a dummy entry whose last_update matches
        # the current file mtime – this simulates “no changes”.
        current_time = time.time()
        dummy_share = Login(
            configuration=self.configuration,
            username=TEST_RW_SHARE_ID,
            home=rel_share_home,
            password=TEST_RW_SHARE_ID,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None)
        dummy_share.last_update = current_time
        daemon_conf['shares'].append(dummy_share)

        # Run the function
        (updated_conf, changed_shares) = refresh_share_creds(
            configuration=self.configuration,
            protocol='sftp',
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS, )
        )

        # No changes should be reported
        self.assertEqual(len(changed_shares), 0)

        # The dummy entry should still be the only one present
        self.assertEqual(len(updated_conf['shares']), 1)

    def test_refresh_share_creds_adds_readonly_share(self):
        """Test that a read‑only share is added correctly"""
        rel_share_home = os.path.join('TestUser', 'shared', 'data')
        user_shared_dir = os.path.join(self.configuration.user_home,
                                       rel_share_home)
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(self.configuration.sharelink_home,
                                       'read-only', TEST_RO_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        (updated_conf, changed_shares) = refresh_share_creds(
            configuration=self.configuration,
            protocol='sftp',
            username=TEST_RO_SHARE_ID,
            share_modes=(READ_ONLY_ACCESS, )
        )

        self.assertIn(TEST_RO_SHARE_ID, changed_shares)
        share_login = [obj for obj in updated_conf['shares']
                       if obj.username == TEST_RO_SHARE_ID]
        self.assertEqual(len(share_login), 1)
        self.assertEqual(share_login[0].home, rel_share_home)

    def test_refresh_share_creds_adds_writeonly_share(self):
        """Test that a write‑only share is added correctly"""
        rel_share_home = os.path.join('TestUser', 'shared', 'data')
        user_shared_dir = os.path.join(self.configuration.user_home,
                                       rel_share_home)
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(self.wo_share_home, TEST_WO_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        (updated_conf, changed_shares) = refresh_share_creds(
            configuration=self.configuration,
            protocol='sftp',
            username=TEST_WO_SHARE_ID,
            share_modes=(WRITE_ONLY_ACCESS, )
        )

        self.assertIn(TEST_WO_SHARE_ID, changed_shares)
        share_login = [obj for obj in updated_conf['shares']
                       if obj.username == TEST_WO_SHARE_ID]
        self.assertEqual(len(share_login), 1)
        self.assertEqual(share_login[0].home, rel_share_home)

    def test_refresh_share_creds_no_change_on_unchanged_link(self):
        """Test that an unchanged share link does not trigger a change"""
        rel_share_home = os.path.join('TestUser', 'shared', 'data')
        user_shared_dir = os.path.join(
            self.configuration.user_home, rel_share_home)
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        # Populate shares with a dummy entry whose last_update matches
        # the current file mtime – this simulates “no changes”.
        current_time = time.time()
        dummy_share = Login(
            configuration=self.configuration,
            username=TEST_RW_SHARE_ID,
            home=rel_share_home,
            password=TEST_RW_SHARE_ID,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None)
        dummy_share.last_update = current_time
        self.configuration.daemon_conf['shares'].append(dummy_share)

        (updated_conf, changed_shares) = refresh_share_creds(
            configuration=self.configuration,
            protocol='sftp',
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS, )
        )

        self.assertEqual(len(changed_shares), 0)
        self.assertEqual(len(updated_conf['shares']), 1)

    def test_refresh_share_creds_detects_missing_link(self):
        """Test that a missing share link is reported as a change"""
        # No symlink created - share link is missing
        missing_share_id = 'missing123'

        (updated_conf, changed_shares) = refresh_share_creds(
            configuration=self.configuration,
            protocol='sftp',
            username=missing_share_id,
            share_modes=(READ_WRITE_ACCESS, )
        )

        # The function should still return an empty list because the link
        # does not exist; no share is added.
        self.assertEqual(len(changed_shares), 0)
        self.assertEqual(len(updated_conf['shares']), 0)

    def test_refresh_share_creds_ignores_dead_link(self):
        """Test that a dead share link is ignored"""
        # Create a symlink that points nowhere
        invalid_target = os.path.join(self.configuration.user_home, 'deadbeef')
        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(invalid_target, share_link_path)

        (updated_conf, changed_shares) = refresh_share_creds(
            configuration=self.configuration,
            protocol='sftp',
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS, )
        )

        # No share should be added because the link is invalid
        self.assertEqual(len(changed_shares), 0)
        self.assertEqual(len(updated_conf['shares']), 0)

    def test_refresh_share_creds_ignores_invalid_link(self):
        """Test that an invalid (out of bounds) share link is ignored"""
        # Create a symlink that points outside a user_home directory
        invalid_target = self.configuration.certs_path
        ensure_dirs_exist(invalid_target)
        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(invalid_target, share_link_path)

        (updated_conf, changed_shares) = refresh_share_creds(
            configuration=self.configuration,
            protocol='sftp',
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS, )
        )

        # No share should be added because the link is invalid but change
        # is still reported as modified.
        self.assertEqual(len(changed_shares), 1)
        self.assertEqual(changed_shares[0], TEST_RW_SHARE_ID)
        self.assertEqual(len(updated_conf['shares']), 0)


class MigSharedGriddaemonsLogin__refresh_user_creds(MigTestCase, UserAssertMixin):
    """Unit tests for the griddaemons login refresh_user_creds helper."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test."""
        # Force X509 user id format
        self.configuration.site_user_id_format = X509_USER_ID_FORMAT
        # Ensure required directories exist
        _ensure_dirs_needed_for_userdb(self.configuration)
        self.expected_user_db_home = os.path.normpath(
            self.configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        self.test_user_home = self._provision_test_user(self, TEST_USER_DN)
        self.test_user_dir = os.path.basename(self.test_user_home)
        # Make sure alias link is provisioned as well
        alias_link_path = os.path.join(self.configuration.user_home,
                                       TEST_USER_EMAIL)
        if not os.path.islink(alias_link_path):
            os.symlink(self.test_user_home, alias_link_path)

        ALIAS_FIELD = 'email'
        self.configuration.user_sftp_alias = ALIAS_FIELD
        self.configuration.user_ftps_alias = ALIAS_FIELD
        self.configuration.user_davs_alias = ALIAS_FIELD

        # Common daemon configuration
        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf['time_stamp'] = 0
        self.configuration.daemon_conf['users'] = []
        self.configuration.daemon_conf['root_dir'] = self.configuration.user_home
        self.configuration.daemon_conf['db_path'] = self.expected_user_db_file
        self.configuration.daemon_conf['allow_publickey'] = True
        self.configuration.daemon_conf['allow_password'] = True
        self.configuration.daemon_conf['allow_digest'] = False
        self.configuration.daemon_conf['user_alias'] = ALIAS_FIELD

    def test_refresh_user_creds_ssh_protocol(self):
        """Test refreshing user credentials for SSH protocol."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ['ssh'])

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='ssh',
            username=username
        )

        # The user should be in the changed list
        self.assertIn(username, changed_users)

        # Verify that Login objects were added to users
        user_logins = [obj for obj in updated_conf['users']
                       if obj.username == TEST_USER_DN or
                       obj.username == username]
        # We expect at least one login (the main username) and possibly aliases
        self.assertGreaterEqual(len(user_logins), 1)

        # Check that at least one login has the correct home directory
        home_found = any(login.home == self.test_user_dir for login in
                         user_logins)
        self.assertTrue(home_found)

    def test_refresh_user_creds_davs_protocol(self):
        """Test refreshing user credentials for DAVS protocol."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ['davs'])

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='davs',
            username=username
        )

        # The user should be in the changed list
        self.assertIn(username, changed_users)

        # Verify that Login objects were added to users
        user_logins = [obj for obj in updated_conf['users']
                       if obj.username == username]
        self.assertEqual(len(user_logins), 1)
        self.assertEqual(user_logins[0].home, self.test_user_dir)

    def test_refresh_user_creds_ftps_protocol(self):
        """Test refreshing user credentials for FTPS protocol."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ['ftps'])

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='ftps',
            username=username
        )

        # The user should be in the changed list
        self.assertIn(username, changed_users)

        # Verify that Login objects were added to users
        user_logins = [obj for obj in updated_conf['users']
                       if obj.username == username]
        self.assertEqual(len(user_logins), 1)
        self.assertEqual(user_logins[0].home, self.test_user_dir)

    def test_refresh_user_creds_https_protocol(self):
        """Test refreshing user credentials for HTTPS protocol (uses user DB)."""
        username = TEST_USER_EMAIL

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='https',
            username=username
        )

        # The user alias should be in the changed list
        self.assertIn(TEST_USER_EMAIL, changed_users)

        # Verify that Login objects were added to users for the username and its aliases
        user_logins = [obj for obj in updated_conf['users']
                       if obj.username == TEST_USER_DN or
                       obj.username == username]
        # We expect at least the main username and possibly aliases
        self.assertGreaterEqual(len(user_logins), 1)

        # Check that at least one login has the correct home directory
        home_found = any(login.home == self.test_user_dir for login in
                         user_logins)
        self.assertTrue(home_found)

    def test_refresh_user_creds_no_changes(self):
        """Test that no changes are reported when credentials are unchanged."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ['ssh'])

        # Pre-populate the users list with a Login object that has
        # last_update set to the current time (simulating no changes)
        current_time = time.time()
        dummy_user = Login(
            configuration=self.configuration,
            username=username,
            home=self.test_user_home,
            password=TEST_USER_PW_HASH,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None)
        dummy_user.last_update = current_time
        self.configuration.daemon_conf['users'].append(dummy_user)

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='ssh',
            username=username
        )

        # No changes should be reported
        self.assertEqual(len(changed_users), 0)
        # The user list should still contain only our dummy user
        self.assertEqual(len(updated_conf['users']), 1)
        self.assertEqual(updated_conf['users'][0].username, username)

    def test_refresh_user_creds_missing_user(self):
        """Test that a missing user is skipped."""
        username = 'nosuchuser'

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='ssh',
            username=username
        )

        # No changes should be reported because the home directory is missing
        self.assertEqual(len(changed_users), 0)
        self.assertEqual(len(updated_conf['users']), 0)

    def test_refresh_user_creds_invalid_protocol(self):
        """Test that an invalid protocol returns early without changes."""
        username = TEST_USER_EMAIL

        # Call the function under test with an invalid protocol
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='invalid',
            username=username
        )

        # No changes should be reported
        self.assertEqual(len(changed_users), 0)
        self.assertEqual(len(updated_conf['users']), 0)

# TODO: merge X509 and UUID versions?


class MigSharedGriddaemonsLogin__refresh_user_creds_uuid_user_id(MigTestCase, UserAssertMixin):
    """Unit tests for the griddaemons login refresh_user_creds helper with UUID users."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test."""
        # Force UUID user id format
        self.configuration.site_user_id_format = UUID_USER_ID_FORMAT
        # Ensure required directories exist
        ensure_dirs_exist(self.configuration.mig_system_files)
        _ensure_dirs_needed_for_userdb(self.configuration)
        self.expected_user_db_home = os.path.normpath(
            self.configuration.user_db_home
        )
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, "MiG-users.db"
        )
        # NOTE: we need to set a password_hash for https test to work with
        overrides = {}
        overrides["password_hash"] = TEST_USER_PW_HASH

        user_dict = _provision_uuid_test_user(self.configuration, TEST_USER_DN,
                                              overrides)
        self.test_user_id = user_id = user_dict['unique_id']
        client_dir = client_id_dir(TEST_USER_DN)
        self.test_user_home = os.path.join(self.configuration.user_home,
                                           user_id)
        self.test_user_dir = os.path.basename(self.test_user_home)
        self.test_user_home_x509 = os.path.join(self.configuration.user_home,
                                                client_dir)
        self.test_user_dir_x509 = os.path.basename(self.test_user_home_x509)
        # Make sure X509 and alias links are provisioned as well
        if not os.path.islink(self.test_user_home_x509):
            os.symlink(self.test_user_home, self.test_user_home_x509)
        alias_link_path = os.path.join(self.configuration.user_home,
                                       TEST_USER_EMAIL)
        if not os.path.islink(alias_link_path):
            os.symlink(self.test_user_home_x509, alias_link_path)

        ALIAS_FIELD = 'email'
        self.configuration.user_sftp_alias = ALIAS_FIELD
        self.configuration.user_ftps_alias = ALIAS_FIELD
        self.configuration.user_davs_alias = ALIAS_FIELD

        # Common daemon configuration
        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf['time_stamp'] = 0
        self.configuration.daemon_conf['users'] = []
        self.configuration.daemon_conf['root_dir'] = self.configuration.user_home
        self.configuration.daemon_conf['db_path'] = self.expected_user_db_file
        self.configuration.daemon_conf['allow_publickey'] = True
        self.configuration.daemon_conf['allow_password'] = True
        self.configuration.daemon_conf['allow_digest'] = False
        self.configuration.daemon_conf['user_alias'] = ALIAS_FIELD

    def test_refresh_user_creds_ssh_protocol(self):
        """Test refreshing user credentials for SSH protocol."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ['ssh'])

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='ssh',
            username=username
        )

        # The user should be in the changed list
        self.assertIn(username, changed_users)

        # Verify that Login objects were added to users
        user_logins = [obj for obj in updated_conf['users']
                       if obj.username == TEST_USER_DN or
                       obj.username == username]
        # We expect at least one login (the main username) and possibly aliases
        self.assertGreaterEqual(len(user_logins), 1)

        # Check that at least one login has the correct home directory
        # TODO: is this X509 dir what we want here or the UUID one?
        home_found = any(login.home == self.test_user_dir_x509 for login in
                         user_logins)
        self.assertTrue(home_found)

    def test_refresh_user_creds_davs_protocol(self):
        """Test refreshing user credentials for DAVS protocol."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ['davs'])

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='davs',
            username=username
        )

        # The user should be in the changed list
        self.assertIn(username, changed_users)

        # Verify that Login objects were added to users
        user_logins = [obj for obj in updated_conf['users']
                       if obj.username == username]
        self.assertEqual(len(user_logins), 1)
        # TODO: is this X509 dir what we want here or the UUID one?
        self.assertEqual(user_logins[0].home, self.test_user_dir_x509)

    def test_refresh_user_creds_ftps_protocol(self):
        """Test refreshing user credentials for FTPS protocol."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ['ftps'])

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='ftps',
            username=username
        )

        # The user should be in the changed list
        self.assertIn(username, changed_users)

        # Verify that Login objects were added to users
        user_logins = [obj for obj in updated_conf['users']
                       if obj.username == username]
        self.assertEqual(len(user_logins), 1)
        # TODO: is this X509 dir what we want here or the UUID one?
        self.assertEqual(user_logins[0].home, self.test_user_dir_x509)

    def test_refresh_user_creds_https_protocol(self):
        """Test refreshing user credentials for HTTPS protocol (uses user DB)."""
        username = TEST_USER_EMAIL

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='https',
            username=username
        )

        # The user alias should be in the changed list
        self.assertIn(TEST_USER_EMAIL, changed_users)

        # Verify that Login objects were added to users for the username and its aliases
        user_logins = [obj for obj in updated_conf['users']
                       if obj.username == TEST_USER_DN or
                       obj.username == username]
        # We expect at least the main username and possibly aliases
        self.assertGreaterEqual(len(user_logins), 1)

        # Check that at least one login has the correct home directory
        # TODO: is this X509 dir what we want here or the UUID one?
        home_found = any(login.home == self.test_user_dir_x509 for login in
                         user_logins)
        self.assertTrue(home_found)

    def test_refresh_user_creds_no_changes(self):
        """Test that no changes are reported when credentials are unchanged."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ['ssh'])

        # Pre-populate the users list with a Login object that has
        # last_update set to the current time (simulating no changes)
        current_time = time.time()
        dummy_user = Login(
            configuration=self.configuration,
            username=username,
            home=self.test_user_home,
            password=TEST_USER_PW_HASH,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None)
        dummy_user.last_update = current_time
        self.configuration.daemon_conf['users'].append(dummy_user)

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='ssh',
            username=username
        )

        # No changes should be reported
        self.assertEqual(len(changed_users), 0)
        # The user list should still contain only our dummy user
        self.assertEqual(len(updated_conf['users']), 1)
        self.assertEqual(updated_conf['users'][0].username, username)

    def test_refresh_user_creds_missing_user(self):
        """Test that a missing user is skipped."""
        username = 'nosuchuser'

        # Call the function under test
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='ssh',
            username=username
        )

        # No changes should be reported because the home directory is missing
        self.assertEqual(len(changed_users), 0)
        self.assertEqual(len(updated_conf['users']), 0)

    def test_refresh_user_creds_invalid_protocol(self):
        """Test that an invalid protocol returns early without changes."""
        username = TEST_USER_EMAIL

        # Call the function under test with an invalid protocol
        (updated_conf, changed_users) = refresh_user_creds(
            configuration=self.configuration,
            protocol='invalid',
            username=username
        )

        # No changes should be reported
        self.assertEqual(len(changed_users), 0)
        self.assertEqual(len(updated_conf['users']), 0)


if __name__ == '__main__':
    unittest.main()
