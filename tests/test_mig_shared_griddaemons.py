#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_griddaemons - unit tests for the griddaemons login helpers
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

"""Unit tests for the griddaemons login helper functions"""

import os
import time
import unittest

# Imports required for the unit test wrapping
from mig.shared.useradm import (
    _ensure_dirs_needed_for_userdb,
)

# Imports of the code under test
from mig.shared.griddaemons.login import (
    Login, get_creds_changes, get_share_changes
)

# Imports required for the unit tests themselves
from tests.support import (
    ensure_dirs_exist,
    MigTestCase, temppath
)

TEST_USER_SHORT_ID = "abc123@some.org"

# NOTE: this is a sample valid but unused ssh public key as it must be parsable
TEST_USER_PUB_KEY = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCuJrICshi7S2KhV03qvgNVOx5ejmHsswdGbvR34wf+eN23Ghq6OZhwGye2S+J6LPVFI3p4SCqxX4URnUM8BRAsiuvbf/+GQfE2pAO0C+/g4V3hhYbYzIyrtPsP1Hl8GioxvZD5nDoLEA4TWokDC4D7SRfv+NEkFLplyVBwHtpUunXBS/zXYdQ4lgk7u8HBBCMqUGbZHfCc+6ibFVn/5WS6vVokL+fSWtxg9tUVWqsS/xtDGPH1wbJUf1Dm3D58KmdX8ca73tBoScwH8qUQwEcyM1JtWtbv1BAZFb+Qk6SEe4GPRsn3I4AAgC7xtU3HKQsiqe8Fzpick/uI5PU+vguitcV/9+AASnGVZJ9M+a63UvlFFloEYcI1LwdZ03JYPQXfXCzJSYiA+pTX4/cf10G4rlxsque4m4OcuCwLKvpTWA/Lla+UJqYhdQW+m7mSizPRoDPgh8mOta1PQob2sGSw8rhqLfApptAPZ0mkN0QY3Dv3i3ItgpYGcPNVXVdjmhU='
# NOTE: this is a sample valid but unused ssh password hash as it must be parsable
TEST_USER_PW_HASH = "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM1234uxi"


class MigSharedGriddaemonsLogin(MigTestCase):
    """Unit tests for griddaemons login helper functions"""

    def _provide_configuration(self):
        """Return a test configuration instance"""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        _ensure_dirs_needed_for_userdb(self.configuration)
        ensure_dirs_exist(self.configuration.sharelink_home)

        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf['users'] = []
        self.configuration.daemon_conf['shares'] = []
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

    def test_get_creds_changes_detects_new_files(self):
        """Verify that new credential files are detected as changes"""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf['allow_publickey'] = True
        daemon_conf['allow_password'] = True

        # Create a dummy user with a last_update in the past
        past_timestamp = time.time() - 3600
        dummy_user = Login(
            configuration=self.configuration,
            username='dummy',
            home='dummy_home',
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
        daemon_conf['allow_publickey'] = True
        daemon_conf['allow_password'] = True

        # Set the file modification times to a time in the past
        current_time = time.time()
        past_timestamp = time.time() - 3600
        # os.utime(self.auth_keys_path, (past_timestamp, past_timestamp))
        # os.utime(self.auth_passwords_path, (past_timestamp, past_timestamp))
        # os.utime(self.auth_digests_path, (past_timestamp, past_timestamp))

        # Create a dummy user with last_update matching the file mtime
        dummy_user = Login(
            configuration=self.configuration,
            username=TEST_USER_SHORT_ID,
            home='dummy_home',
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

    def test_get_share_changes_detects_updates(self):
        """Verify that share link and key file changes are detected"""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf['allow_publickey'] = True

        share_id = 'Abcdef1234'
        user_shared_dir = os.path.join(self.configuration.user_home,
                                       'TestUser', 'shared', 'data')
        ensure_dirs_exist(user_shared_dir)
        user_shared_keys = os.path.join(user_shared_dir, '.ssh',
                                        'authorized_keys')
        share_link_path = os.path.join(self.configuration.sharelink_home,
                                       share_id)
        os.symlink(user_shared_dir, share_link_path)

        # Create a dummy share with a last_update in the past
        past_timestamp = time.time() - 3600
        dummy_share = Login(
            configuration=self.configuration,
            username=share_id,
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
            share_id,
            share_link_path,
            self.auth_keys_path
        )

        self.assertIn(share_link_path, changed_paths)


if __name__ == '__main__':
    unittest.main()
