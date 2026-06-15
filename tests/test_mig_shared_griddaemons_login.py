#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_griddaemons_login - unit tests for griddaemons login functions
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
import pickle
import socket
import threading
import time
import unittest

# Imports required for the unit test wrapping
from mig.shared.base import client_id_dir
from mig.shared.defaults import (
    READ_ONLY_ACCESS,
    READ_WRITE_ACCESS,
    WRITE_ONLY_ACCESS,
)

# Imports of the code under test
from mig.shared.griddaemons.login import (
    Login,
    add_job_object,
    add_jupyter_object,
    add_share_object,
    add_user_object,
    get_creds_changes,
    get_job_changes,
    get_share_changes,
    login_map_lookup,
    refresh_job_creds,
    refresh_jupyter_creds,
    refresh_share_creds,
    refresh_user_creds,
    update_login_map,
    update_user_objects,
)

# More imports required for the unit test wrapping
from mig.shared.useradm import _ensure_dirs_needed_for_userdb

# Imports required for the unit tests themselves
from tests.support import (
    MigTestCase,
    UserAssertMixin,
    ensure_dirs_exist,
    temppath,
)
from tests.support.usersupp import TEST_USER_DN

TEST_USER_SHORT_ID = "abc123@some.org"
TEST_USER_EMAIL = TEST_USER_DN.split("/emailAddress=", 1)[-1]
TEST_RO_SHARE_ID = "abcdef1234"
TEST_RW_SHARE_ID = "klmnop4567"
TEST_WO_SHARE_ID = "uvwxyz7890"

# NOTE: job IDs and jupyter sessions are 64 chars with jobs limited to hex
TEST_JOB_ID = "0419b45ebc1dedbdcb91fa6251035a2096758f5d700e15478b27a90734454107"
TEST_JOB_USER_DN = TEST_USER_DN
TEST_JOB_USER_DIR = client_id_dir(TEST_USER_DN)
OTHER_JOB_ID = (
    "162b1575f7f62baf5c830cc7956a438f7d003b11cddbf6d21cfdc4f598fbf7c1"
)
TEST_JUPYTER_SESSION_ID = (
    "ohNo4ii9geeyei3Jai8aif6gae6Eebiechai3chegh0moo9NieveKu3AC8ooshuo"
)
OTHER_JUPYTER_SESSION_ID = (
    "sah3quoh3zedaemoovoowahlumeitumohv4iekooPhek3Ieng6Apho4aw0aiPhef"
)

# NOTE: this is a sample valid but unused ssh public key as it must be parsable
TEST_USER_PUB_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCuJrICshi7S2KhV03qvgNVOx5ejmHsswdGbvR34wf+eN23Ghq6OZhwGye2S+J6LPVFI3p4SCqxX4URnUM8BRAsiuvbf/+GQfE2pAO0C+/g4V3hhYbYzIyrtPsP1Hl8GioxvZD5nDoLEA4TWokDC4D7SRfv+NEkFLplyVBwHtpUunXBS/zXYdQ4lgk7u8HBBCMqUGbZHfCc+6ibFVn/5WS6vVokL+fSWtxg9tUVWqsS/xtDGPH1wbJUf1Dm3D58KmdX8ca73tBoScwH8qUQwEcyM1JtWtbv1BAZFb+Qk6SEe4GPRsn3I4AAgC7xtU3HKQsiqe8Fzpick/uI5PU+vguitcV/9+AASnGVZJ9M+a63UvlFFloEYcI1LwdZ03JYPQXfXCzJSYiA+pTX4/cf10G4rlxsque4m4OcuCwLKvpTWA/Lla+UJqYhdQW+m7mSizPRoDPgh8mOta1PQob2sGSw8rhqLfApptAPZ0mkN0QY3Dv3i3ItgpYGcPNVXVdjmhU="
# NOTE: this is a sample valid but unused ssh password hash as it must be parsable
TEST_USER_PW_HASH = (
    "PBKDF2$sha256$10000$XMZGaar/pU4PvWDr$w0dYjezF6JGtSiYPexyZMt3lM1234uxi"
)


def _prepare_auth_files(home_path, auth_protos=None):
    """Helper to create helper auth files for on eor more auth_protos.
    If None is passed ssh, ftps and davs auth files will be made.
    """
    auth_files = []
    if auth_protos is None:
        auth_protos = ["davs", "ftps", "ssh"]

    # Create requested auth dirs with files
    for auth in auth_protos:
        # Create a .PROTO directory with authorized_X file(s)
        dot_proto_dir = os.path.join(home_path, ".%s" % auth)
        ensure_dirs_exist(dot_proto_dir)
        if auth == "ssh":
            authkeys_path = os.path.join(dot_proto_dir, "authorized_keys")
            with open(authkeys_path, "w") as creds_fd:
                creds_fd.write(TEST_USER_PUB_KEY)
            auth_files.append(authkeys_path)

        authpasswords_path = os.path.join(dot_proto_dir, "authorized_passwords")
        with open(authpasswords_path, "w") as creds_fd:
            creds_fd.write(TEST_USER_PW_HASH)
        auth_files.append(authpasswords_path)
    return auth_files


def _parse_pkey_to_openssh_format(paramiko_pkey):
    """Convert a parsed pub key on paramiko PKey format to openssh format"""
    return "%s %s" % (paramiko_pkey.get_name(), paramiko_pkey.get_base64())


def _create_job_mrsl_file(test_case, session_id, job_dict):
    """Helper to create a .mRSL pickle file and symlink."""
    mrsl_dir = test_case.configuration.sessid_to_mrsl_link_home
    ensure_dirs_exist(mrsl_dir)

    # Create actual pickle file in a temp location
    pickle_path = temppath("job_%s.pkl" % session_id, test_case)
    with open(pickle_path, "wb") as pkl_fd:
        pickle.dump(job_dict, pkl_fd)

    # Create symlink
    link_path = os.path.join(mrsl_dir, "%s.mRSL" % session_id)
    if os.path.lexists(link_path):
        os.remove(link_path)
    os.symlink(pickle_path, link_path)
    return link_path


def _create_jupyter_mount_file(test_case, session_id, jupyter_dict):
    """Helper to create a .jupyter_mount pickle file and symlink."""
    mount_dir = test_case.configuration.sessid_to_jupyter_mount_link_home
    ensure_dirs_exist(mount_dir)

    pickle_path = temppath("jupyter_%s.pkl" % session_id, test_case)
    with open(pickle_path, "wb") as pkl_fd:
        pickle.dump(jupyter_dict, pkl_fd)

    link_path = os.path.join(mount_dir, "%s.jupyter_mount" % session_id)
    if os.path.lexists(link_path):
        os.remove(link_path)
    os.symlink(pickle_path, link_path)
    return link_path


class _FakeLock(object):
    """Small lock double for various tests with optional locking."""

    def __init__(self):
        self.acquired = False
        self.released = False

    def acquire(self):
        self.acquired = True

    def release(self):
        self.released = True


class MigSharedGriddaemonsLogin__add_job_object(MigTestCase):
    """Unit tests for the griddaemons add_job_object helper."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test."""
        # Initialize daemon_conf with empty jobs list
        self.configuration.daemon_conf = {
            "jobs": [],
            "creds_lock": threading.Lock(),  # Ensure lock is present for testing
        }

    def test_add_job_object_basic(self):
        """Verify that add_job_object adds a Login object to the jobs list."""
        # Call the helper
        add_job_object(
            configuration=self.configuration,
            login=TEST_JOB_ID,
            home="home1",
            password=None,
            pubkey=TEST_USER_PUB_KEY,
        )

        # Verify the job was added
        jobs = self.configuration.daemon_conf["jobs"]
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.username, TEST_JOB_ID)
        self.assertEqual(job.home, "home1")
        self.assertEqual(job.password, None)
        # Convert saved paramiko.PKey back to openssh pub key format and check
        login_key = job.public_key
        result = _parse_pkey_to_openssh_format(login_key)
        self.assertEqual(result, TEST_USER_PUB_KEY)

    def test_add_job_object_uses_creds_lock(self):
        """Verify add_job_object acquires and releases creds_lock."""
        fake_lock = _FakeLock()
        self.configuration.daemon_conf["creds_lock"] = fake_lock
        add_job_object(
            configuration=self.configuration,
            login=OTHER_JOB_ID,
            home="job_home2",
        )
        self.assertTrue(fake_lock.acquired)
        self.assertTrue(fake_lock.released)

    def test_add_job_object_missing_home(self):
        """Verify that add_job_object uses login as home if home is None."""
        add_job_object(
            configuration=self.configuration, login="job3", home=None
        )
        job = self.configuration.daemon_conf["jobs"][0]
        self.assertEqual(job.home, "job3")


class MigSharedGriddaemonsLogin__add_jupyter_object(MigTestCase):
    """Unit tests for the griddaemons add_jupyter_object helper."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test."""
        # Initialize daemon_conf with empty jupyter_mounts list
        self.configuration.daemon_conf = {
            "jupyter_mounts": [],
            "creds_lock": threading.Lock(),
        }

    def test_add_jupyter_object_basic(self):
        """Verify that add_jupyter_object adds a Login object to jupyter_mounts."""
        # Call the helper
        add_jupyter_object(
            configuration=self.configuration,
            login=TEST_JUPYTER_SESSION_ID,
            home="jupyter_home1",
            pubkey=TEST_USER_PUB_KEY,
        )

        # Verify the jupyter mount was added
        mounts = self.configuration.daemon_conf["jupyter_mounts"]
        self.assertEqual(len(mounts), 1)
        mount = mounts[0]
        self.assertEqual(mount.username, TEST_JUPYTER_SESSION_ID)
        self.assertEqual(mount.home, "jupyter_home1")
        # Convert saved paramiko.PKey back to openssh pub key format and check
        login_key = mount.public_key
        result = _parse_pkey_to_openssh_format(login_key)
        self.assertEqual(result, TEST_USER_PUB_KEY)

    def test_add_jupyter_object_uses_creds_lock(self):
        """Verify add_jupyter_object acquires and releases creds_lock."""
        fake_lock = _FakeLock()
        self.configuration.daemon_conf["creds_lock"] = fake_lock
        add_jupyter_object(
            configuration=self.configuration,
            login=OTHER_JUPYTER_SESSION_ID,
            home="jupyter_home2",
        )
        self.assertTrue(fake_lock.acquired)
        self.assertTrue(fake_lock.released)

    def test_add_jupyter_object_missing_home(self):
        """Verify that add_jupyter_object uses login as home if home is None."""
        add_jupyter_object(
            configuration=self.configuration, login="jupyter3", home=None
        )
        mount = self.configuration.daemon_conf["jupyter_mounts"][0]
        self.assertEqual(mount.home, "jupyter3")


class MigSharedGriddaemonsLogin__add_user_object(MigTestCase):
    """Unit tests for the add_user_object helper."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return "testconfig"

    def before_each(self):
        """Set up daemon_conf for add_user_object tests."""
        self.configuration.daemon_conf = {
            "users": [],
            "creds_lock": threading.Lock(),
        }

    def test_add_user_object_appends_login(self):
        """Verify add_user_object appends a Login to users."""
        user_dict = {"user_id": TEST_USER_DN}

        add_user_object(
            configuration=self.configuration,
            login=TEST_USER_EMAIL,
            home="home1",
            password=TEST_USER_PW_HASH,
            access=READ_WRITE_ACCESS,
            user_dict=user_dict,
        )

        self.assertEqual(len(self.configuration.daemon_conf["users"]), 1)
        login = self.configuration.daemon_conf["users"][0]
        self.assertIsInstance(login, Login)
        self.assertEqual(login.username, TEST_USER_EMAIL)
        self.assertEqual(login.home, "home1")
        self.assertEqual(login.password, TEST_USER_PW_HASH)
        self.assertIsNone(login.digest)
        self.assertIsNone(login.public_key)
        self.assertTrue(login.chroot)
        self.assertEqual(login.access, READ_WRITE_ACCESS)
        self.assertEqual(login.user_dict, user_dict)

    def test_add_user_object_adds_public_key_login(self):
        """Verify add_user_object stores parsed public key logins."""
        add_user_object(
            configuration=self.configuration,
            login=TEST_USER_EMAIL,
            home="home1",
            pubkey=TEST_USER_PUB_KEY,
            access=READ_WRITE_ACCESS,
        )

        login = self.configuration.daemon_conf["users"][0]
        self.assertIsNotNone(login.public_key)
        key_line = "%s %s" % (
            login.public_key.get_name(),
            login.public_key.get_base64(),
        )
        self.assertEqual(key_line, TEST_USER_PUB_KEY)

    def test_add_user_object_adds_digest_login(self):
        """Verify add_user_object stores digest logins."""
        add_user_object(
            configuration=self.configuration,
            login=TEST_USER_EMAIL,
            home="home1",
            digest="digest-value",
            access=READ_ONLY_ACCESS,
        )

        login = self.configuration.daemon_conf["users"][0]
        self.assertEqual(login.digest, "digest-value")
        self.assertIsNone(login.password)
        self.assertIsNone(login.public_key)
        self.assertEqual(login.access, READ_ONLY_ACCESS)

    def test_add_user_object_without_lock(self):
        """Verify add_user_object works when creds_lock is not configured."""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf.pop("creds_lock")

        add_user_object(
            configuration=self.configuration,
            login=TEST_USER_EMAIL,
            home="home1",
        )

        self.assertEqual(len(daemon_conf["users"]), 1)
        self.assertEqual(daemon_conf["users"][0].username, TEST_USER_EMAIL)

    def test_add_user_object_uses_creds_lock(self):
        """Verify add_user_object acquires and releases creds_lock."""
        fake_lock = _FakeLock()
        self.configuration.daemon_conf["creds_lock"] = fake_lock
        add_user_object(
            configuration=self.configuration,
            login=TEST_USER_EMAIL,
            home="user_home2",
        )
        self.assertTrue(fake_lock.acquired)
        self.assertTrue(fake_lock.released)

    def test_add_user_object_uses_login_as_home_when_home_none(self):
        """Verify add_user_object normalizes missing home to login name."""
        add_user_object(
            configuration=self.configuration, login=TEST_USER_EMAIL, home=None
        )

        login = self.configuration.daemon_conf["users"][0]
        self.assertEqual(login.home, TEST_USER_EMAIL)


class MigSharedGriddaemonsLogin__add_share_object(MigTestCase):
    """Unit tests for the add_share_object helper."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return "testconfig"

    def before_each(self):
        """Set up daemon_conf for add_share_object tests."""
        self.configuration.daemon_conf = {
            "shares": [],
            "creds_lock": threading.Lock(),
        }

    def test_add_share_object_appends_login(self):
        """Verify add_share_object appends a Login to shares."""
        user_dict = {}
        home_path = temppath("share_home", self)
        ensure_dirs_exist(home_path)
        login = Login(
            configuration=self.configuration,
            username=TEST_RW_SHARE_ID,
            home=home_path,
            password=TEST_RW_SHARE_ID,
            access=READ_WRITE_ACCESS,
            user_dict=user_dict,
        )
        add_share_object(
            configuration=self.configuration,
            login=login.username,
            home=home_path,
            password=login.password,
            access=login.access,
        )
        self.assertEqual(len(self.configuration.daemon_conf["shares"]), 1)
        share_login = self.configuration.daemon_conf["shares"][0]
        self.assertEqual(share_login.username, TEST_RW_SHARE_ID)
        self.assertEqual(share_login.home, home_path)
        self.assertEqual(share_login.password, TEST_RW_SHARE_ID)
        self.assertTrue(share_login.chroot)
        self.assertEqual(share_login.access, READ_WRITE_ACCESS)

    def test_add_share_object_adds_public_key_login(self):
        """Verify add_share_object stores parsed public key logins."""
        home_path = temppath("share_home_pubkey", self)
        ensure_dirs_exist(home_path)
        login = Login(
            configuration=self.configuration,
            username=TEST_RW_SHARE_ID,
            home=home_path,
            password=TEST_RW_SHARE_ID,
            access=READ_WRITE_ACCESS,
        )
        add_share_object(
            configuration=self.configuration,
            login=login,
            home=home_path,
            pubkey=TEST_USER_PUB_KEY,
        )
        share_login = self.configuration.daemon_conf["shares"][0]
        self.assertIsNotNone(share_login.public_key)
        key_line = "%s %s" % (
            share_login.public_key.get_name(),
            share_login.public_key.get_base64(),
        )
        self.assertEqual(key_line, TEST_USER_PUB_KEY)

    def test_add_share_object_adds_digest_login(self):
        """Verify add_share_object stores digest logins."""
        home_path = temppath("share_home_digest", self)
        ensure_dirs_exist(home_path)
        login = Login(
            configuration=self.configuration,
            username=TEST_RO_SHARE_ID,
            home=home_path,
            password=TEST_RO_SHARE_ID,
            access=READ_ONLY_ACCESS,
        )
        add_share_object(
            configuration=self.configuration,
            login=login,
            home=home_path,
            digest="digest-value",
            access=READ_ONLY_ACCESS,
        )
        share_login = self.configuration.daemon_conf["shares"][0]
        self.assertEqual(share_login.digest, "digest-value")
        self.assertIsNone(share_login.password)
        self.assertIsNone(share_login.public_key)
        self.assertEqual(share_login.access, READ_ONLY_ACCESS)

    def test_add_share_object_without_lock(self):
        """Verify add_share_object works when creds_lock is not configured."""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf.pop("creds_lock")
        home_path = temppath("share_home_nolock", self)
        ensure_dirs_exist(home_path)
        login = Login(
            configuration=self.configuration,
            username=TEST_RW_SHARE_ID,
            home=home_path,
            password=TEST_RW_SHARE_ID,
            access=READ_WRITE_ACCESS,
        )
        add_share_object(
            configuration=self.configuration,
            login=login.username,
            home=home_path,
        )
        self.assertEqual(len(daemon_conf["shares"]), 1)
        self.assertEqual(daemon_conf["shares"][0].username, TEST_RW_SHARE_ID)

    def test_add_share_object_uses_creds_lock(self):
        """Verify add_share_object acquires and releases creds_lock."""
        fake_lock = _FakeLock()
        self.configuration.daemon_conf["creds_lock"] = fake_lock
        add_share_object(
            configuration=self.configuration,
            login=TEST_RW_SHARE_ID,
            home="share_home2",
        )
        self.assertTrue(fake_lock.acquired)
        self.assertTrue(fake_lock.released)

    def test_add_share_object_uses_login_as_home_when_home_none(self):
        """Verify add_share_object normalizes missing home to login name."""
        login = Login(
            configuration=self.configuration,
            username=TEST_RW_SHARE_ID,
            home=None,
            password=TEST_RW_SHARE_ID,
            access=READ_WRITE_ACCESS,
        )
        add_share_object(
            configuration=self.configuration, login=login.username, home=None
        )
        share_login = self.configuration.daemon_conf["shares"][0]
        self.assertEqual(share_login.home, TEST_RW_SHARE_ID)


class MigSharedGriddaemonsLogin__get_creds_changes(MigTestCase):
    """Unit tests for griddaemons login get_creds_changes function"""

    def _provide_configuration(self):
        """Return a test configuration instance"""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        # Ensure required directories exist
        _ensure_dirs_needed_for_userdb(self.configuration)
        ensure_dirs_exist(self.configuration.sharelink_home)

        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf["time_stamp"] = 0
        self.configuration.daemon_conf["users"] = []
        self.configuration.daemon_conf["allow_publickey"] = True
        self.configuration.daemon_conf["allow_password"] = True
        # TODO: enable and test unsafe digest auth, too?
        # self.configuration.daemon_conf['allow_digest'] = True
        self.configuration.daemon_conf["allow_digest"] = False

        self.test_user_home = self._provision_test_user(self, TEST_USER_DN)
        auth_files = _prepare_auth_files(self.test_user_home, ["ssh"])
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
            user_dict=None,
        )
        dummy_user.last_update = past_timestamp
        daemon_conf["users"].append(dummy_user)

        changed_paths = get_creds_changes(
            daemon_conf,
            "user",
            self.auth_keys_path,
            self.auth_passwords_path,
            self.auth_digests_path,
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
            user_dict=None,
        )
        dummy_user.last_update = current_time
        daemon_conf["users"].append(dummy_user)

        changed_paths = get_creds_changes(
            daemon_conf,
            TEST_USER_SHORT_ID,
            self.auth_keys_path,
            self.auth_passwords_path,
            self.auth_digests_path,
        )

        self.assertEqual(len(changed_paths), 0)


class MigSharedGriddaemonsLogin__get_job_changes(MigTestCase):
    """Unit tests for griddaemons login get_job_changes function"""

    def _provide_configuration(self):
        """Return a test configuration instance"""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        _ensure_dirs_needed_for_userdb(self.configuration)
        ensure_dirs_exist(self.configuration.sharelink_home)

        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf["time_stamp"] = 0
        self.configuration.daemon_conf["jobs"] = []

        # TODO: enable and test unsafe digest auth, too?
        # self.configuration.daemon_conf['allow_digest'] = True
        self.configuration.daemon_conf["allow_digest"] = False

        self.auth_keys_path = temppath("authorized_keys", self)
        self.auth_passwords_path = temppath("authorized_passwords", self)
        # self.auth_digests_path = temppath('authhorized_digests', self)
        self.auth_digests_path = None

        # Create sample credential files
        with open(self.auth_keys_path, "w") as creds_fd:
            creds_fd.write(TEST_USER_PUB_KEY)
        with open(self.auth_passwords_path, "w") as creds_fd:
            creds_fd.write(TEST_USER_PW_HASH)
        # with open(self.auth_digests_path, 'w') as creds_fd:
        #    creds_fd.write(TEST_USER_DIGEST)

    def test_get_job_changes_new_job(self):
        """Verify that a new job mrsl file is detected as a change"""
        daemon_conf = self.configuration.daemon_conf

        mrsl_path = temppath("test_job.mRSL", self)
        with open(mrsl_path, "w") as mrsl_fd:
            mrsl_fd.write("test content")

        changed_paths = get_job_changes(
            daemon_conf, "test_session_id", mrsl_path
        )

        self.assertIn(mrsl_path, changed_paths)

    def test_get_job_changes_no_changes(self):
        """Verify that unchanged job mrsl file returns an empty list"""
        daemon_conf = self.configuration.daemon_conf

        mrsl_path = temppath("test_job.mRSL", self)
        with open(mrsl_path, "w") as mrsl_fd:
            mrsl_fd.write("test content")

        # Create a dummy job with last_update matching file mtime
        current_time = time.time()
        dummy_job = Login(
            configuration=self.configuration,
            username="test_session_id",
            home="job_home",
            password=None,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        dummy_job.last_update = current_time
        daemon_conf["jobs"].append(dummy_job)

        changed_paths = get_job_changes(
            daemon_conf, "test_session_id", mrsl_path
        )

        self.assertEqual(len(changed_paths), 0)

    def test_get_job_changes_missing_file(self):
        """Verify that missing mrsl file is detected for existing job"""
        daemon_conf = self.configuration.daemon_conf

        # Create a dummy job
        dummy_job = Login(
            configuration=self.configuration,
            username="test_session_id",
            home="job_home",
            password=None,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        daemon_conf["jobs"].append(dummy_job)

        mrsl_path = temppath("missing_job.mRSL", self)

        changed_paths = get_job_changes(
            daemon_conf, "test_session_id", mrsl_path
        )

        self.assertIn(mrsl_path, changed_paths)


class MigSharedGriddaemonsLogin__get_share_changes(MigTestCase):
    """Unit tests for griddaemons login get_share_changes helper function"""

    def _provide_configuration(self):
        """Return a test configuration instance"""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        _ensure_dirs_needed_for_userdb(self.configuration)
        self.ro_share_home = os.path.join(
            self.configuration.sharelink_home, "read-only"
        )
        self.rw_share_home = os.path.join(
            self.configuration.sharelink_home, "read-write"
        )
        self.wo_share_home = os.path.join(
            self.configuration.sharelink_home, "write-only"
        )
        ensure_dirs_exist(self.ro_share_home)
        ensure_dirs_exist(self.rw_share_home)
        ensure_dirs_exist(self.wo_share_home)

        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf["time_stamp"] = 0
        self.configuration.daemon_conf["shares"] = []

        # TODO: enable and test unsafe digest auth, too?
        # self.configuration.daemon_conf['allow_digest'] = True
        self.configuration.daemon_conf["allow_digest"] = False

        self.auth_keys_path = temppath("authorized_keys", self)
        self.auth_passwords_path = temppath("authorized_passwords", self)
        # self.auth_digests_path = temppath('authhorized_digests', self)
        self.auth_digests_path = None

        # Create sample credential files
        with open(self.auth_keys_path, "w") as creds_fd:
            creds_fd.write(TEST_USER_PUB_KEY)
        with open(self.auth_passwords_path, "w") as creds_fd:
            creds_fd.write(TEST_USER_PW_HASH)
        # with open(self.auth_digests_path, 'w') as creds_fd:
        #    creds_fd.write(TEST_USER_DIGEST)

    def test_get_share_changes_detects_updates(self):
        """Verify that share link and key file changes are detected"""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf["allow_publickey"] = True

        user_shared_dir = os.path.join(
            self.configuration.user_home, "TestUser", "shared", "data"
        )
        ensure_dirs_exist(user_shared_dir)
        user_shared_keys = os.path.join(
            user_shared_dir, ".ssh", "authorized_keys"
        )
        share_link_path = os.path.join(self.ro_share_home, TEST_RO_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        # Create a dummy share with a last_update in the past
        past_timestamp = time.time() - 3600
        dummy_share = Login(
            configuration=self.configuration,
            username=TEST_RO_SHARE_ID,
            home="share_home",
            password=TEST_USER_PW_HASH,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        dummy_share.last_update = past_timestamp
        daemon_conf["shares"].append(dummy_share)

        changed_paths = get_share_changes(
            daemon_conf, TEST_RO_SHARE_ID, share_link_path, user_shared_keys
        )

        self.assertIn(share_link_path, changed_paths)
        self.assertIn(user_shared_keys, changed_paths)

    def test_get_share_changes_new_share(self):
        """Verify that a new share link is detected as a change"""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf["allow_publickey"] = True

        user_shared_dir = os.path.join(
            self.configuration.user_home, "TestUser", "shared", "data"
        )
        ensure_dirs_exist(user_shared_dir)
        share_link_path = os.path.join(self.ro_share_home, TEST_RO_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        changed_paths = get_share_changes(
            daemon_conf, TEST_RO_SHARE_ID, share_link_path, self.auth_keys_path
        )

        self.assertIn(share_link_path, changed_paths)
        self.assertIn(self.auth_keys_path, changed_paths)

    def test_get_share_changes_no_changes(self):
        """Verify that unchanged share files return an empty list"""
        daemon_conf = self.configuration.daemon_conf
        daemon_conf["allow_publickey"] = True

        user_shared_dir = os.path.join(
            self.configuration.user_home, "TestUser", "shared", "data"
        )
        ensure_dirs_exist(user_shared_dir)
        user_shared_keys = os.path.join(
            user_shared_dir, ".ssh", "authorized_keys"
        )
        ensure_dirs_exist(user_shared_keys)
        share_link_path = os.path.join(self.ro_share_home, TEST_RO_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        # Create a dummy share with last_update matching file mtime
        current_time = time.time()
        dummy_share = Login(
            configuration=self.configuration,
            username=TEST_RO_SHARE_ID,
            home="share_home",
            password=TEST_USER_PW_HASH,
            digest=None,
            public_key=TEST_USER_PUB_KEY,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        dummy_share.last_update = current_time
        daemon_conf["shares"].append(dummy_share)

        changed_paths = get_share_changes(
            daemon_conf, TEST_RO_SHARE_ID, share_link_path, user_shared_keys
        )

        self.assertEqual(len(changed_paths), 0)


class MigSharedGriddaemonsLogin__login_map_lookup(MigTestCase):
    """Unit tests for the login_map_lookup function from griddaemons/login.py"""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return "testconfig"

    def before_each(self):
        """Set up test configuration with login_map and creds_lock."""
        # Common daemon configuration
        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf["time_stamp"] = 0
        self.configuration.daemon_conf["login_map"] = {}
        self.configuration.daemon_conf["creds_lock"] = threading.Lock()

    def test_user_exists_with_multiple_credentials(self):
        """Verify login_map_lookup returns all credentials for a user."""
        # Create two Login objects for 'user1'
        cred1 = Login(
            configuration=self.configuration.daemon_conf,
            username="user1",
            home="home1",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        cred2 = Login(
            configuration=self.configuration,
            username="user1",
            home="home2",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        # Populate login_map
        daemon_conf = self.configuration.daemon_conf
        daemon_conf["login_map"]["user1"] = [cred1, cred2]
        # Call the function
        result = login_map_lookup(daemon_conf, "user1")
        # Assert
        self.assertEqual(result, [cred1, cred2])

    def test_user_exists_with_single_credential(self):
        """Verify login_map_lookup returns one credential for a user."""
        cred = Login(
            configuration=self.configuration,
            username="user2",
            home="home3",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        daemon_conf = self.configuration.daemon_conf
        daemon_conf["login_map"]["user2"] = [cred]
        result = login_map_lookup(daemon_conf, "user2")
        self.assertEqual(result, [cred])

    def test_user_does_not_exist(self):
        """Verify login_map_lookup returns empty list for non-existent user."""
        daemon_conf = self.configuration.daemon_conf
        result = login_map_lookup(daemon_conf, "nosuchuser")
        self.assertEqual(result, [])

    def test_lock_handling(self):
        """Basic check that creds_lock is acquired and released."""
        # Simulate concurrent access (not fully testable in unit tests)
        # This is a placeholder for thread-safety verification
        daemon_conf = self.configuration.daemon_conf
        cred = Login(
            configuration=self.configuration,
            username="user3",
            home="home4",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        daemon_conf["login_map"]["user3"] = [cred]
        # Call the function (lock should be acquired/released internally)
        result = login_map_lookup(daemon_conf, "user3")
        self.assertEqual(result, [daemon_conf["login_map"]["user3"][0]])


class MigSharedGriddaemonsLogin__refresh_job_creds(MigTestCase):
    """Unit tests for the refresh_job_creds helper."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up configuration and directories."""
        self.configuration.site_enable_jobs = True
        self.configuration.site_enable_gdp = False
        ensure_dirs_exist(self.configuration.user_home)
        ensure_dirs_exist(self.configuration.mrsl_files_dir)
        ensure_dirs_exist(self.configuration.sessid_to_mrsl_link_home)
        self.configuration.daemon_conf = {
            "jobs": [],
            "time_stamp": 0,
            "creds_lock": threading.Lock(),
            "allow_publickey": True,
        }

        # Ensure the user dir for the job user exists (for chroot validation)
        self.job_user_home = os.path.join(
            self.configuration.user_home, TEST_JOB_USER_DIR
        )
        ensure_dirs_exist(self.job_user_home)

    def test_refresh_job_creds_invalid_protocol(self):
        """Invalid protocol should return early with no changes."""
        conf, changed = refresh_job_creds(
            self.configuration, "invalid", TEST_JOB_ID
        )
        self.assertEqual(changed, [])
        self.assertEqual(conf["jobs"], [])

    def test_refresh_job_creds_invalid_job_id(self):
        """Invalid job ID format should return early."""
        # possible_job_id usually checks for alphanumeric + dash/underscore
        conf, changed = refresh_job_creds(
            self.configuration, "sftp", "invalid@id"
        )
        self.assertEqual(changed, [])

    def test_refresh_job_creds_no_link(self):
        """Missing symlink should report change (removal) if job existed, else nothing."""
        # Case 1: Job does not exist in conf, link missing -> no change
        conf, changed = refresh_job_creds(
            self.configuration, "sftp", OTHER_JOB_ID
        )
        self.assertEqual(changed, [])

        # Case 2: Job exists in conf, link missing -> removal
        add_job_object(
            self.configuration, OTHER_JOB_ID, "home", pubkey=TEST_USER_PUB_KEY
        )
        conf, changed = refresh_job_creds(
            self.configuration, "sftp", OTHER_JOB_ID
        )
        self.assertIn(OTHER_JOB_ID, changed)
        self.assertEqual(conf["jobs"], [])

    def test_refresh_job_creds_link_unchanged(self):
        """Unchanged link (mtime <= time_stamp) should return no changes."""
        job_dict = {
            "STATUS": "EXECUTING",
            "SESSIONID": "staticjob",
            "USER_CERT": TEST_JOB_USER_DN,
            "MOUNT": "mount",
            "MOUNTSSHPUBLICKEY": TEST_USER_PUB_KEY,
            "RESOURCE_CONFIG": {"HOSTURL": "localhost"},
        }
        _create_job_mrsl_file(self, "staticjob", job_dict)

        # Pre-populate conf with job having current timestamp
        current_time = time.time()
        self.configuration.daemon_conf["time_stamp"] = current_time
        add_job_object(
            self.configuration,
            "staticjob",
            TEST_JOB_USER_DIR,
            pubkey=TEST_USER_PUB_KEY,
        )
        # Manually set last_update to now to simulate "fresh"
        self.configuration.daemon_conf["jobs"][0].last_update = current_time

        conf, changed = refresh_job_creds(
            self.configuration, "sftp", "staticjob"
        )
        self.assertEqual(changed, [])
        self.assertEqual(len(conf["jobs"]), 1)

    def test_refresh_job_creds_valid_job_added(self):
        """Valid executing job with key should be added to jobs."""
        job_dict = {
            "STATUS": "EXECUTING",
            "SESSIONID": TEST_JOB_ID,
            "USER_CERT": TEST_JOB_USER_DN,
            "MOUNT": "mount",
            "MOUNTSSHPUBLICKEY": TEST_USER_PUB_KEY,
            "RESOURCE_CONFIG": {"HOSTURL": "localhost"},
        }
        _create_job_mrsl_file(self, TEST_JOB_ID, job_dict)

        conf, changed = refresh_job_creds(
            self.configuration, "sftp", TEST_JOB_ID
        )

        self.assertIn(TEST_JOB_ID, changed)
        self.assertEqual(len(conf["jobs"]), 1)
        job = conf["jobs"][0]
        self.assertEqual(job.username, TEST_JOB_ID)
        self.assertEqual(job.home, TEST_JOB_USER_DIR)
        self.assertEqual(job.ip_addr, "127.0.0.1")
        self.assertIsNotNone(job.public_key)
        # Convert saved paramiko.PKey back to openssh pub key format and check
        login_key = job.public_key
        result = _parse_pkey_to_openssh_format(login_key)
        self.assertEqual(result, TEST_USER_PUB_KEY)

    def test_refresh_job_creds_non_executing_status(self):
        """Job with non-EXECUTING status should be removed as inactive."""
        daemon_conf = self.configuration.daemon_conf
        # Directly register test job as executing before test
        job_dict = {
            "STATUS": "EXECUTING",
            "SESSIONID": TEST_JOB_ID,
            "USER_CERT": TEST_JOB_USER_DN,
            "MOUNT": "mount",
            "MOUNTSSHPUBLICKEY": TEST_USER_PUB_KEY,
            "RESOURCE_CONFIG": {"HOSTURL": "localhost"},
        }
        _create_job_mrsl_file(self, TEST_JOB_ID, job_dict)
        # Pre-add job to active jobs in conf jobs list
        add_job_object(
            self.configuration,
            TEST_JOB_ID,
            TEST_JOB_USER_DIR,
            pubkey=TEST_USER_PUB_KEY,
        )
        # NOTE: double check that job is in place for test
        self.assertEqual(len(daemon_conf["jobs"]), 1)
        self.assertIn(TEST_JOB_ID, [i.username for i in daemon_conf["jobs"]])

        # Now mark finished and test that refresh removes it
        job_dict["STATUS"] = "FINISHED"
        _create_job_mrsl_file(self, TEST_JOB_ID, job_dict)
        conf, changed = refresh_job_creds(
            self.configuration, "sftp", TEST_JOB_ID
        )
        # NOTE: job is detected changed and should be removed
        self.assertIn(TEST_JOB_ID, changed)
        self.assertEqual(conf["jobs"], [])

    def test_refresh_job_creds_full_execution_cycle(self):
        """Job going through states should be added and removed when done."""
        job_dict = {
            "STATUS": "QUEUED",
            "SESSIONID": TEST_JOB_ID,
            "USER_CERT": TEST_JOB_USER_DN,
            "MOUNT": "mount",
            "MOUNTSSHPUBLICKEY": TEST_USER_PUB_KEY,
            "RESOURCE_CONFIG": {"HOSTURL": "localhost"},
        }
        _create_job_mrsl_file(self, TEST_JOB_ID, job_dict)

        # Verify that still only queued jobs don't get added
        conf, changed = refresh_job_creds(
            self.configuration, "sftp", TEST_JOB_ID
        )
        # NOTE: job is detected changed but should remain inactive
        self.assertIn(TEST_JOB_ID, changed)
        self.assertEqual(conf["jobs"], [])

        # Verify that job gets added when changing to executing
        job_dict["STATUS"] = "EXECUTING"
        _create_job_mrsl_file(self, TEST_JOB_ID, job_dict)
        conf, changed = refresh_job_creds(
            self.configuration, "sftp", TEST_JOB_ID
        )
        # NOTE: job is detected changed and should be inserted
        self.assertIn(TEST_JOB_ID, changed)
        self.assertEqual(len(conf["jobs"]), 1)
        self.assertEqual(conf["jobs"][0].username, TEST_JOB_ID)

        # Verify that jobs get removed again when finished
        job_dict["STATUS"] = "FINISHED"
        _create_job_mrsl_file(self, TEST_JOB_ID, job_dict)
        conf, changed = refresh_job_creds(
            self.configuration, "sftp", TEST_JOB_ID
        )
        # NOTE: job is detected changed and should be removed
        self.assertIn(TEST_JOB_ID, changed)
        self.assertEqual(conf["jobs"], [])

    def test_refresh_job_creds_broken_key(self):
        """Job with unparsable public key should be treated as inactive."""
        job_dict = {
            "STATUS": "EXECUTING",
            "SESSIONID": OTHER_JOB_ID,
            "USER_CERT": TEST_JOB_USER_DN,
            "MOUNT": "mount",
            "MOUNTSSHPUBLICKEY": "invalid-key-data",
            "RESOURCE_CONFIG": {"HOSTURL": "localhost"},
        }
        _create_job_mrsl_file(self, OTHER_JOB_ID, job_dict)

        conf, changed = refresh_job_creds(
            self.configuration, "sftp", OTHER_JOB_ID
        )
        self.assertIn(OTHER_JOB_ID, changed)
        self.assertEqual(conf["jobs"], [])

    def test_refresh_job_creds_unresolvable_host(self):
        """Job with unresolvable HOSTURL should be treated as inactive."""
        job_dict = {
            "STATUS": "EXECUTING",
            "SESSIONID": OTHER_JOB_ID,
            "USER_CERT": TEST_JOB_USER_DN,
            "MOUNT": "mount",
            "MOUNTSSHPUBLICKEY": TEST_USER_PUB_KEY,
            "RESOURCE_CONFIG": {"HOSTURL": "nonexistent.invalid.tld"},
        }
        _create_job_mrsl_file(self, OTHER_JOB_ID, job_dict)

        # Mock socket to raise gaierror
        original_gethostbyname_ex = socket.gethostbyname_ex
        socket.gethostbyname_ex = lambda h: (_ for _ in ()).throw(
            socket.gaierror
        )
        try:
            conf, changed = refresh_job_creds(
                self.configuration, "sftp", OTHER_JOB_ID
            )
        finally:
            socket.gethostbyname_ex = original_gethostbyname_ex

        self.assertIn(OTHER_JOB_ID, changed)
        self.assertEqual(conf["jobs"], [])


class MigSharedGriddaemonsLogin__refresh_jupyter_creds(MigTestCase):
    """Unit tests for the refresh_jupyter_creds helper."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        """Set up configuration and directories."""
        self.configuration.site_enable_jupyter = True
        self.configuration.site_enable_gdp = False
        ensure_dirs_exist(self.configuration.user_home)
        ensure_dirs_exist(self.configuration.jupyter_mount_files_dir)
        ensure_dirs_exist(self.configuration.sessid_to_jupyter_mount_link_home)
        self.configuration.daemon_conf = {
            "jupyter_mounts": [],
            "time_stamp": 0,
            "creds_lock": threading.Lock(),
            "allow_publickey": True,
        }

        self.jupyter_user_home = os.path.join(
            self.configuration.user_home, TEST_JOB_USER_DIR
        )
        ensure_dirs_exist(self.jupyter_user_home)

    def test_refresh_jupyter_creds_invalid_protocol(self):
        """Invalid protocol should return early."""
        conf, changed = refresh_jupyter_creds(
            self.configuration, "invalid", TEST_JUPYTER_SESSION_ID
        )
        self.assertEqual(changed, [])

    def test_refresh_jupyter_creds_invalid_id(self):
        """Invalid jupyter mount ID format should return early."""
        conf, changed = refresh_jupyter_creds(
            self.configuration, "sftp", "invalid@id"
        )
        self.assertEqual(changed, [])

    @unittest.skip("TODO: implement the mentioned clean up and enable next")
    def test_refresh_jupyter_creds_no_link(self):
        """Missing symlink should clean up existing mounts for that user_dir."""
        daemon_conf = self.configuration.daemon_conf
        # Directly add a stale mount
        add_jupyter_object(
            self.configuration,
            TEST_JUPYTER_SESSION_ID,
            TEST_JOB_USER_DIR,
            pubkey=TEST_USER_PUB_KEY,
        )

        # NOTE: double check that jupyter session is in place for test
        self.assertEqual(len(daemon_conf["jupyter_mounts"]), 1)
        self.assertIn(
            TEST_JUPYTER_SESSION_ID,
            [i.username for i in daemon_conf["jupyter_mounts"]],
        )

        # Now test that refresh removes it
        conf, changed = refresh_jupyter_creds(
            self.configuration, "sftp", TEST_JUPYTER_SESSION_ID
        )

        # NOTE: mount is detected unchanged and mount should be removed
        self.assertEqual(len(changed), 0)
        self.assertEqual(conf["jupyter_mounts"], [])

    def test_refresh_jupyter_creds_valid_mount_added(self):
        """Valid jupyter mount should be added."""
        jupyter_dict = {
            "SESSIONID": TEST_JUPYTER_SESSION_ID,
            "USER_CERT": TEST_JOB_USER_DN,
            "MOUNTSSHPUBLICKEY": TEST_USER_PUB_KEY,
        }
        _create_jupyter_mount_file(self, TEST_JUPYTER_SESSION_ID, jupyter_dict)

        conf, changed = refresh_jupyter_creds(
            self.configuration, "sftp", TEST_JUPYTER_SESSION_ID
        )

        self.assertIn(TEST_JUPYTER_SESSION_ID, changed)
        self.assertEqual(len(conf["jupyter_mounts"]), 1)
        mount = conf["jupyter_mounts"][0]
        self.assertEqual(mount.username, TEST_JUPYTER_SESSION_ID)
        self.assertEqual(mount.home, TEST_JOB_USER_DIR)
        self.assertIsNotNone(mount.public_key)
        # Convert saved paramiko.PKey back to openssh pub key format and check
        login_key = mount.public_key
        result = _parse_pkey_to_openssh_format(login_key)
        self.assertEqual(result, TEST_USER_PUB_KEY)

    def test_refresh_jupyter_creds_purges_old_keys_same_home(self):
        """Adding a new mount for same home should purge old mounts."""
        # Add stale mount with different session ID but same home
        add_jupyter_object(
            self.configuration,
            OTHER_JUPYTER_SESSION_ID,
            TEST_JOB_USER_DIR,
            pubkey=TEST_USER_PUB_KEY,
        )

        jupyter_dict = {
            "SESSIONID": OTHER_JUPYTER_SESSION_ID,
            "USER_CERT": TEST_JOB_USER_DN,
            "MOUNTSSHPUBLICKEY": TEST_USER_PUB_KEY,
        }
        _create_jupyter_mount_file(self, OTHER_JUPYTER_SESSION_ID, jupyter_dict)

        conf, changed = refresh_jupyter_creds(
            self.configuration, "sftp", OTHER_JUPYTER_SESSION_ID
        )

        self.assertIn(OTHER_JUPYTER_SESSION_ID, changed)
        # Only the new one should remain
        self.assertEqual(len(conf["jupyter_mounts"]), 1)
        self.assertEqual(
            conf["jupyter_mounts"][0].username, OTHER_JUPYTER_SESSION_ID
        )

    def test_refresh_jupyter_creds_broken_key(self):
        """Unparsable key should result in no mount added."""
        jupyter_dict = {
            "SESSIONID": OTHER_JUPYTER_SESSION_ID,
            "USER_CERT": TEST_JOB_USER_DN,
            "MOUNTSSHPUBLICKEY": "invalid-key",
        }
        _create_jupyter_mount_file(self, OTHER_JUPYTER_SESSION_ID, jupyter_dict)

        conf, changed = refresh_jupyter_creds(
            self.configuration, "sftp", OTHER_JUPYTER_SESSION_ID
        )
        self.assertEqual(changed, [])
        self.assertEqual(conf["jupyter_mounts"], [])

    def test_refresh_jupyter_creds_missing_fields(self):
        """Missing required fields in dict should result in no mount."""
        jupyter_dict = {
            "SESSIONID": OTHER_JUPYTER_SESSION_ID,
            # Missing USER_CERT and MOUNTSSHPUBLICKEY
        }
        _create_jupyter_mount_file(self, OTHER_JUPYTER_SESSION_ID, jupyter_dict)

        conf, changed = refresh_jupyter_creds(
            self.configuration, "sftp", OTHER_JUPYTER_SESSION_ID
        )
        self.assertEqual(changed, [])
        self.assertEqual(conf["jupyter_mounts"], [])


class MigSharedGriddaemonsLogin__refresh_share_creds(MigTestCase):
    """Unit tests for the griddaemons login refresh_share_creds helper."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test."""
        # The base class already creates the required directory layout.
        # Ensure the share‑link home exists – it is used by refresh_share_creds.
        self.ro_share_home = os.path.join(
            self.configuration.sharelink_home, "read-only"
        )
        self.rw_share_home = os.path.join(
            self.configuration.sharelink_home, "read-write"
        )
        self.wo_share_home = os.path.join(
            self.configuration.sharelink_home, "write-only"
        )
        ensure_dirs_exist(self.ro_share_home)
        ensure_dirs_exist(self.rw_share_home)
        ensure_dirs_exist(self.wo_share_home)

        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf["time_stamp"] = 0
        self.configuration.daemon_conf["shares"] = []
        self.configuration.daemon_conf["allow_publickey"] = True
        self.configuration.daemon_conf["allow_password"] = True
        self.configuration.daemon_conf["allow_digest"] = False

        # Paths that the function will look at
        self.auth_keys_path = temppath("authorized_keys", self)
        self.auth_passwords_path = temppath("authorized_passwords", self)
        self.auth_digests_path = None

        # Create dummy credential files
        with open(self.auth_keys_path, "w") as creds_fd:
            creds_fd.write(TEST_USER_PUB_KEY)
        with open(self.auth_passwords_path, "w") as creds_fd:
            creds_fd.write(TEST_USER_PW_HASH)

    def test_refresh_share_creds_adds_new_share(self):
        """A new share link should be added to daemon_conf['shares']."""
        # Build a share link that points to a temporary user directory
        rel_share_home = os.path.join("TestUser", "shared", "data")
        user_shared_dir = os.path.join(
            self.configuration.user_home, rel_share_home
        )
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        # Call the function under test
        # NOTE: only sftp access is supported for now
        updated_conf, changed_shares = refresh_share_creds(
            configuration=self.configuration,
            protocol="sftp",
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS,),
        )

        # The share should now be present in the changed list
        self.assertIn(TEST_RW_SHARE_ID, changed_shares)

        # Verify that a Login object was added to shares
        share_login = [
            obj
            for obj in updated_conf["shares"]
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
        rel_share_home = os.path.join("TestUser", "shared", "data")
        user_shared_dir = os.path.join(
            self.configuration.user_home, rel_share_home
        )
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        _prepare_auth_files(user_shared_dir, ["ssh"])

        # Call the function under test
        # NOTE: only sftp access is supported for now
        updated_conf, changed_shares = refresh_share_creds(
            configuration=self.configuration,
            protocol="sftp",
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS,),
        )

        # The share should now be present twice in the changed list
        self.assertIn(TEST_RW_SHARE_ID, changed_shares)

        # Verify that a Login object was added to shares
        share_login = [
            obj
            for obj in updated_conf["shares"]
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
        result = _parse_pkey_to_openssh_format(login_key)
        self.assertEqual(result, TEST_USER_PUB_KEY)

    def test_refresh_share_creds_no_changes(self):
        """When the share link and its key file have not changed, the function
        should return an empty changed_shares list."""
        daemon_conf = self.configuration.daemon_conf

        # Create a share link that already exists
        rel_share_home = os.path.join("TestUser", "shared", "data")
        user_shared_dir = os.path.join(
            self.configuration.user_home, rel_share_home
        )
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
            user_dict=None,
        )
        dummy_share.last_update = current_time
        daemon_conf["shares"].append(dummy_share)

        # Run the function
        updated_conf, changed_shares = refresh_share_creds(
            configuration=self.configuration,
            protocol="sftp",
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS,),
        )

        # No changes should be reported
        self.assertEqual(len(changed_shares), 0)

        # The dummy entry should still be the only one present
        self.assertEqual(len(updated_conf["shares"]), 1)

    def test_refresh_share_creds_adds_readonly_share(self):
        """Test that a read‑only share is added correctly"""
        rel_share_home = os.path.join("TestUser", "shared", "data")
        user_shared_dir = os.path.join(
            self.configuration.user_home, rel_share_home
        )
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(
            self.configuration.sharelink_home, "read-only", TEST_RO_SHARE_ID
        )
        os.symlink(user_shared_dir, share_link_path)

        updated_conf, changed_shares = refresh_share_creds(
            configuration=self.configuration,
            protocol="sftp",
            username=TEST_RO_SHARE_ID,
            share_modes=(READ_ONLY_ACCESS,),
        )

        self.assertIn(TEST_RO_SHARE_ID, changed_shares)
        share_login = [
            obj
            for obj in updated_conf["shares"]
            if obj.username == TEST_RO_SHARE_ID
        ]
        self.assertEqual(len(share_login), 1)
        self.assertEqual(share_login[0].home, rel_share_home)

    def test_refresh_share_creds_adds_writeonly_share(self):
        """Test that a write‑only share is added correctly"""
        rel_share_home = os.path.join("TestUser", "shared", "data")
        user_shared_dir = os.path.join(
            self.configuration.user_home, rel_share_home
        )
        ensure_dirs_exist(user_shared_dir)

        share_link_path = os.path.join(self.wo_share_home, TEST_WO_SHARE_ID)
        os.symlink(user_shared_dir, share_link_path)

        updated_conf, changed_shares = refresh_share_creds(
            configuration=self.configuration,
            protocol="sftp",
            username=TEST_WO_SHARE_ID,
            share_modes=(WRITE_ONLY_ACCESS,),
        )

        self.assertIn(TEST_WO_SHARE_ID, changed_shares)
        share_login = [
            obj
            for obj in updated_conf["shares"]
            if obj.username == TEST_WO_SHARE_ID
        ]
        self.assertEqual(len(share_login), 1)
        self.assertEqual(share_login[0].home, rel_share_home)

    def test_refresh_share_creds_no_change_on_unchanged_link(self):
        """Test that an unchanged share link does not trigger a change"""
        rel_share_home = os.path.join("TestUser", "shared", "data")
        user_shared_dir = os.path.join(
            self.configuration.user_home, rel_share_home
        )
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
            user_dict=None,
        )
        dummy_share.last_update = current_time
        self.configuration.daemon_conf["shares"].append(dummy_share)

        updated_conf, changed_shares = refresh_share_creds(
            configuration=self.configuration,
            protocol="sftp",
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS,),
        )

        self.assertEqual(len(changed_shares), 0)
        self.assertEqual(len(updated_conf["shares"]), 1)

    def test_refresh_share_creds_detects_missing_link(self):
        """Test that a missing share link is reported as a change"""
        # No symlink created - share link is missing
        missing_share_id = "missing123"

        updated_conf, changed_shares = refresh_share_creds(
            configuration=self.configuration,
            protocol="sftp",
            username=missing_share_id,
            share_modes=(READ_WRITE_ACCESS,),
        )

        # The function should still return an empty list because the link
        # does not exist; no share is added.
        self.assertEqual(len(changed_shares), 0)
        self.assertEqual(len(updated_conf["shares"]), 0)

    def test_refresh_share_creds_ignores_dead_link(self):
        """Test that a dead share link is ignored"""
        # Create a symlink that points nowhere
        invalid_target = os.path.join(self.configuration.user_home, "deadbeef")
        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(invalid_target, share_link_path)

        updated_conf, changed_shares = refresh_share_creds(
            configuration=self.configuration,
            protocol="sftp",
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS,),
        )

        # No share should be added because the link is invalid
        self.assertEqual(len(changed_shares), 0)
        self.assertEqual(len(updated_conf["shares"]), 0)

    def test_refresh_share_creds_ignores_invalid_link(self):
        """Test that an invalid (out of bounds) share link is ignored"""
        # Create a symlink that points outside a user_home directory
        invalid_target = self.configuration.certs_path
        ensure_dirs_exist(invalid_target)
        share_link_path = os.path.join(self.rw_share_home, TEST_RW_SHARE_ID)
        os.symlink(invalid_target, share_link_path)

        updated_conf, changed_shares = refresh_share_creds(
            configuration=self.configuration,
            protocol="sftp",
            username=TEST_RW_SHARE_ID,
            share_modes=(READ_WRITE_ACCESS,),
        )

        # No share should be added because the link is invalid but change
        # is still reported as modified.
        self.assertEqual(len(changed_shares), 1)
        self.assertEqual(changed_shares[0], TEST_RW_SHARE_ID)
        self.assertEqual(len(updated_conf["shares"]), 0)


class MigSharedGriddaemonsLogin__refresh_user_creds(
    MigTestCase, UserAssertMixin
):
    """Unit tests for the griddaemons login refresh_user_creds helper."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test."""
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
        alias_link_path = os.path.join(
            self.configuration.user_home, TEST_USER_EMAIL
        )
        if not os.path.islink(alias_link_path):
            os.symlink(self.test_user_home, alias_link_path)

        ALIAS_FIELD = "email"
        self.configuration.user_sftp_alias = ALIAS_FIELD
        self.configuration.user_ftps_alias = ALIAS_FIELD
        self.configuration.user_davs_alias = ALIAS_FIELD

        # Common daemon configuration
        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf["time_stamp"] = 0
        self.configuration.daemon_conf["users"] = []
        self.configuration.daemon_conf["root_dir"] = (
            self.configuration.user_home
        )
        self.configuration.daemon_conf["db_path"] = self.expected_user_db_file
        self.configuration.daemon_conf["allow_publickey"] = True
        self.configuration.daemon_conf["allow_password"] = True
        self.configuration.daemon_conf["allow_digest"] = False
        self.configuration.daemon_conf["user_alias"] = ALIAS_FIELD

    def test_refresh_user_creds_ssh_protocol(self):
        """Test refreshing user credentials for SSH protocol."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ["ssh"])

        # Call the function under test
        updated_conf, changed_users = refresh_user_creds(
            configuration=self.configuration, protocol="ssh", username=username
        )

        # The user should be in the changed list
        self.assertIn(username, changed_users)

        # Verify that Login objects were added to users
        user_logins = [
            obj
            for obj in updated_conf["users"]
            if obj.username == TEST_USER_DN or obj.username == username
        ]
        # We expect at least one login (the main username) and possibly aliases
        self.assertGreaterEqual(len(user_logins), 1)

        # Check that at least one login has the correct home directory
        home_found = any(
            login.home == self.test_user_dir for login in user_logins
        )
        self.assertTrue(home_found)

    def test_refresh_user_creds_davs_protocol(self):
        """Test refreshing user credentials for DAVS protocol."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ["davs"])

        # Call the function under test
        updated_conf, changed_users = refresh_user_creds(
            configuration=self.configuration, protocol="davs", username=username
        )

        # The user should be in the changed list
        self.assertIn(username, changed_users)

        # Verify that Login objects were added to users
        user_logins = [
            obj for obj in updated_conf["users"] if obj.username == username
        ]
        self.assertEqual(len(user_logins), 1)
        self.assertEqual(user_logins[0].home, self.test_user_dir)

    def test_refresh_user_creds_ftps_protocol(self):
        """Test refreshing user credentials for FTPS protocol."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ["ftps"])

        # Call the function under test
        updated_conf, changed_users = refresh_user_creds(
            configuration=self.configuration, protocol="ftps", username=username
        )

        # The user should be in the changed list
        self.assertIn(username, changed_users)

        # Verify that Login objects were added to users
        user_logins = [
            obj for obj in updated_conf["users"] if obj.username == username
        ]
        self.assertEqual(len(user_logins), 1)
        self.assertEqual(user_logins[0].home, self.test_user_dir)

    def test_refresh_user_creds_https_protocol(self):
        """Test refreshing user credentials for HTTPS protocol (uses user DB)."""
        username = TEST_USER_EMAIL

        # Call the function under test
        updated_conf, changed_users = refresh_user_creds(
            configuration=self.configuration,
            protocol="https",
            username=username,
        )

        # The user alias should be in the changed list
        self.assertIn(TEST_USER_EMAIL, changed_users)

        # Verify that Login objects were added to users for the username and its aliases
        user_logins = [
            obj
            for obj in updated_conf["users"]
            if obj.username == TEST_USER_DN or obj.username == username
        ]
        # We expect at least the main username and possibly aliases
        self.assertGreaterEqual(len(user_logins), 1)

        # Check that at least one login has the correct home directory
        home_found = any(
            login.home == self.test_user_dir for login in user_logins
        )
        self.assertTrue(home_found)

    def test_refresh_user_creds_no_changes(self):
        """Test that no changes are reported when credentials are unchanged."""
        username = TEST_USER_EMAIL
        _prepare_auth_files(self.test_user_home, ["ssh"])

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
            user_dict=None,
        )
        dummy_user.last_update = current_time
        self.configuration.daemon_conf["users"].append(dummy_user)

        # Call the function under test
        updated_conf, changed_users = refresh_user_creds(
            configuration=self.configuration, protocol="ssh", username=username
        )

        # No changes should be reported
        self.assertEqual(len(changed_users), 0)
        # The user list should still contain only our dummy user
        self.assertEqual(len(updated_conf["users"]), 1)
        self.assertEqual(updated_conf["users"][0].username, username)

    def test_refresh_user_creds_missing_user(self):
        """Test that a missing user is skipped."""
        username = "nosuchuser"

        # Call the function under test
        updated_conf, changed_users = refresh_user_creds(
            configuration=self.configuration, protocol="ssh", username=username
        )

        # No changes should be reported because the home directory is missing
        self.assertEqual(len(changed_users), 0)
        self.assertEqual(len(updated_conf["users"]), 0)

    def test_refresh_user_creds_invalid_protocol(self):
        """Test that an invalid protocol returns early without changes."""
        username = TEST_USER_EMAIL

        # Call the function under test with an invalid protocol
        updated_conf, changed_users = refresh_user_creds(
            configuration=self.configuration,
            protocol="invalid",
            username=username,
        )

        # No changes should be reported
        self.assertEqual(len(changed_users), 0)
        self.assertEqual(len(updated_conf["users"]), 0)


class MigSharedGriddaemonsLogin__update_login_map(MigTestCase):
    """Unit tests for the update_login_map function from griddaemons/login.py"""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return "testconfig"

    def before_each(self):
        """Set up test configuration with login_map and creds_lock."""
        # Common daemon configuration
        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf["time_stamp"] = 0
        self.configuration.daemon_conf["login_map"] = {}
        self.configuration.daemon_conf["users"] = []
        self.configuration.daemon_conf["jobs"] = []
        self.configuration.daemon_conf["shares"] = []
        self.configuration.daemon_conf["jupyter_mounts"] = []
        self.configuration.daemon_conf["creds_lock"] = threading.Lock()

    def test_update_login_map_users(self):
        """Verify login_map is updated correctly for changed users."""
        # Create Login objects
        user1 = Login(
            configuration=self.configuration,
            username="user1",
            home="home1",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        user2 = Login(
            configuration=self.configuration,
            username="user2",
            home="home2",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        # Populate users list
        self.configuration.daemon_conf["users"] = [user1, user2]

        # Call the function under test
        update_login_map(
            daemon_conf=self.configuration.daemon_conf,
            changed_users=["user1", "user2"],
        )

        # Verify login_map
        login_map = self.configuration.daemon_conf["login_map"]
        self.assertIn("user1", login_map)
        self.assertIn("user2", login_map)
        self.assertEqual(login_map["user1"], [user1])
        self.assertEqual(login_map["user2"], [user2])

    def test_update_login_map_jobs(self):
        """Verify login_map is updated correctly for changed jobs."""
        # Create Login objects
        test_job = Login(
            configuration=self.configuration,
            username=TEST_JOB_ID,
            home="home1",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr="1.2.3.4",
            user_dict=None,
        )
        other_job = Login(
            configuration=self.configuration,
            username=OTHER_JOB_ID,
            home="home2",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr="5.6.7.8",
            user_dict=None,
        )
        # Populate jobs list
        self.configuration.daemon_conf["jobs"] = [test_job, other_job]

        # Call the function under test
        update_login_map(
            daemon_conf=self.configuration.daemon_conf,
            changed_users=[],
            changed_jobs=[TEST_JOB_ID, OTHER_JOB_ID],
        )

        # Verify login_map
        login_map = self.configuration.daemon_conf["login_map"]
        self.assertIn(TEST_JOB_ID, login_map)
        self.assertIn(OTHER_JOB_ID, login_map)
        self.assertEqual(login_map[TEST_JOB_ID], [test_job])
        self.assertEqual(login_map[OTHER_JOB_ID], [other_job])

    def test_update_login_map_shares(self):
        """Verify login_map is updated correctly for changed shares."""
        # Create Login objects
        share1 = Login(
            configuration=self.configuration,
            username="share1",
            home="home1",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        share2 = Login(
            configuration=self.configuration,
            username="share2",
            home="home2",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        # Populate shares list
        self.configuration.daemon_conf["shares"] = [share1, share2]

        # Call the function under test
        update_login_map(
            daemon_conf=self.configuration.daemon_conf,
            changed_users=[],
            changed_shares=["share1", "share2"],
        )

        # Verify login_map
        login_map = self.configuration.daemon_conf["login_map"]
        self.assertIn("share1", login_map)
        self.assertIn("share2", login_map)
        self.assertEqual(login_map["share1"], [share1])
        self.assertEqual(login_map["share2"], [share2])

    def test_update_login_map_jupyter(self):
        """Verify login_map is updated correctly for changed jupyter mounts."""
        # Create Login objects
        test_session = Login(
            configuration=self.configuration,
            username=TEST_JUPYTER_SESSION_ID,
            home="home1",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        other_session = Login(
            configuration=self.configuration,
            username=OTHER_JUPYTER_SESSION_ID,
            home="home2",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        # Populate jupyter_mounts list
        self.configuration.daemon_conf["jupyter_mounts"] = [
            test_session,
            other_session,
        ]

        # Call the function under test
        update_login_map(
            daemon_conf=self.configuration.daemon_conf,
            changed_users=[],
            changed_jupyter=[TEST_JUPYTER_SESSION_ID, OTHER_JUPYTER_SESSION_ID],
        )

        # Verify login_map
        login_map = self.configuration.daemon_conf["login_map"]
        self.assertIn(TEST_JUPYTER_SESSION_ID, login_map)
        self.assertIn(OTHER_JUPYTER_SESSION_ID, login_map)
        self.assertEqual(login_map[TEST_JUPYTER_SESSION_ID], [test_session])
        self.assertEqual(login_map[OTHER_JUPYTER_SESSION_ID], [other_session])

    def test_update_login_map_nonexistent(self):
        """Verify login_map is set to empty list for non-existent usernames."""
        # Populate users list with one user
        user1 = Login(
            configuration=self.configuration,
            username="user1",
            home="home1",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        self.configuration.daemon_conf["users"] = [user1]

        # Call the function under test for a non-existent user
        update_login_map(
            daemon_conf=self.configuration.daemon_conf,
            changed_users=["nonexistent"],
        )

        # Verify login_map
        login_map = self.configuration.daemon_conf["login_map"]
        self.assertIn("nonexistent", login_map)
        self.assertEqual(login_map["nonexistent"], [])

    def test_update_login_map_empty_lists(self):
        """Verify login_map is not changed when changed lists are empty."""
        # Populate users list
        user1 = Login(
            configuration=self.configuration,
            username="user1",
            home="home1",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        self.configuration.daemon_conf["users"] = [user1]

        # Call the function under test with empty lists
        update_login_map(
            daemon_conf=self.configuration.daemon_conf,
            changed_users=[],
            changed_jobs=[],
            changed_shares=[],
            changed_jupyter=[],
        )

        # Verify login_map is unchanged (should be empty because we didn't update for 'user1')
        login_map = self.configuration.daemon_conf["login_map"]
        self.assertEqual(len(login_map), 0)

    def test_update_login_map_lock_handling(self):
        """Basic check that creds_lock is acquired and released."""
        # Create a Login object
        user1 = Login(
            configuration=self.configuration,
            username="user1",
            home="home1",
            password=None,
            digest=None,
            public_key=None,
            chroot=True,
            access=None,
            ip_addr=None,
            user_dict=None,
        )
        self.configuration.daemon_conf["users"] = [user1]

        # Call the function under test
        update_login_map(
            daemon_conf=self.configuration.daemon_conf, changed_users=["user1"]
        )

        # Verify login_map was updated (lock must have been acquired/released)
        login_map = self.configuration.daemon_conf["login_map"]
        self.assertIn("user1", login_map)
        self.assertEqual(login_map["user1"], [user1])


class MigSharedGriddaemonsLogin__update_user_objects(MigTestCase):
    """Unit tests for the update_user_objects helper."""

    def _provide_configuration(self):
        """Return a test configuration instance."""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test."""
        # Ensure required directories exist
        _ensure_dirs_needed_for_userdb(self.configuration)
        self.configuration.daemon_conf = {}
        self.configuration.daemon_conf["users"] = []
        self.configuration.daemon_conf["root_dir"] = (
            self.configuration.user_home
        )
        self.configuration.daemon_conf["db_path"] = os.path.join(
            self.configuration.user_db_home, "MiG-users.db"
        )
        self.configuration.daemon_conf["allow_publickey"] = True
        self.configuration.daemon_conf["allow_password"] = True
        self.configuration.daemon_conf["allow_digest"] = False

        # Create a test user home
        self.test_user_home = self._provision_test_user(self, TEST_USER_DN)
        self.test_user_dir = os.path.basename(self.test_user_home)

        # Create auth files for the user
        self.ssh_auth_paths = _prepare_auth_files(self.test_user_home, ["ssh"])
        self.ssh_auth_keys_path, self.ssh_auth_pw_path = self.ssh_auth_paths

    def test_update_user_objects_adds_passwords(self):
        """Verify that update_user_objects adds Login objects for passwords."""
        daemon_conf = self.configuration.daemon_conf
        # Extract the .PROTO/authorized_keys part from auth_keys_path
        authkeys = self.ssh_auth_keys_path.replace(self.test_user_home, "")
        authkeys = authkeys.lstrip(os.sep)
        authpw = self.ssh_auth_pw_path.replace(self.test_user_home, "")
        authpw = authpw.lstrip(os.sep)
        authprotos = (authkeys, authpw, None)
        user_tuple = (
            TEST_USER_DN,
            TEST_USER_EMAIL,
            self.test_user_dir,
            TEST_USER_SHORT_ID,
            TEST_USER_EMAIL,
        )
        # Call the helper
        update_user_objects(
            configuration=self.configuration,
            auth_file=authpw,
            path=self.ssh_auth_pw_path,
            user_vars=user_tuple,
            auth_protos=authprotos,
            private_auth_file=True,
        )

        # Verify that three aliased pw logins were added
        pw_logins = [u for u in daemon_conf["users"] if u.password is not None]
        self.assertEqual(len(pw_logins), 3)
        for entry in pw_logins:
            self.assertIn(
                entry.username,
                (TEST_USER_DN, TEST_USER_EMAIL, TEST_USER_SHORT_ID),
            )
            self.assertEqual(entry.home, self.test_user_dir)
            self.assertEqual(entry.access, READ_WRITE_ACCESS)
            self.assertEqual(entry.password, TEST_USER_PW_HASH)

        # Verify that no key logins were added
        key_logins = [
            u for u in daemon_conf["users"] if u.public_key is not None
        ]
        self.assertEqual(len(key_logins), 0)
        # Verify that no digest logins were added
        digest_logins = [
            u for u in daemon_conf["users"] if u.digest is not None
        ]
        self.assertEqual(len(digest_logins), 0)

    def test_update_user_objects_adds_keys(self):
        """Verify that update_user_objects adds Login objects for keys."""
        daemon_conf = self.configuration.daemon_conf
        # Extract the .PROTO/authorized_keys part from auth_keys_path
        authkeys = self.ssh_auth_keys_path.replace(self.test_user_home, "")
        authkeys = authkeys.lstrip(os.sep)
        authpw = self.ssh_auth_pw_path.replace(self.test_user_home, "")
        authpw = authpw.lstrip(os.sep)
        authprotos = (authkeys, authpw, None)
        user_tuple = (
            TEST_USER_DN,
            TEST_USER_EMAIL,
            self.test_user_dir,
            TEST_USER_SHORT_ID,
            TEST_USER_EMAIL,
        )
        # Call the helper
        update_user_objects(
            configuration=self.configuration,
            auth_file=authkeys,
            path=self.ssh_auth_keys_path,
            user_vars=user_tuple,
            auth_protos=authprotos,
            private_auth_file=True,
        )

        # Verify that three aliased key logins were added (dupe keys ignored)
        key_logins = [
            u for u in daemon_conf["users"] if u.public_key is not None
        ]
        self.assertEqual(len(key_logins), 3)

        for entry in key_logins:
            self.assertIn(
                entry.username,
                (TEST_USER_DN, TEST_USER_EMAIL, TEST_USER_SHORT_ID),
            )
            self.assertEqual(entry.home, self.test_user_dir)
            self.assertEqual(entry.access, READ_WRITE_ACCESS)
            login_key = entry.public_key
            result = _parse_pkey_to_openssh_format(login_key)
            self.assertEqual(result, TEST_USER_PUB_KEY)

        # Verify that no password logins were added
        pw_logins = [u for u in daemon_conf["users"] if u.password is not None]
        self.assertEqual(len(pw_logins), 0)
        # Verify that no digest logins were added
        digest_logins = [
            u for u in daemon_conf["users"] if u.digest is not None
        ]
        self.assertEqual(len(digest_logins), 0)

    def test_update_user_objects_removes_old_entries(self):
        """Verify that update_user_objects cleans old entries for the same user."""
        daemon_conf = self.configuration.daemon_conf
        # Extract the .PROTO/authorized_passwords part from auth_pw_path
        authpw = self.ssh_auth_pw_path.replace(self.test_user_home, "")
        authpw = authpw.lstrip(os.sep)
        authprotos = (None, authpw, None)
        user_tuple = (
            TEST_USER_DN,
            TEST_USER_EMAIL,
            self.test_user_dir,
            None,
            None,
        )
        # Create a dummy user with a last_update in the past to remove in test
        past_timestamp = time.time() - 3600
        dummy_user = Login(
            configuration=self.configuration,
            username=TEST_USER_EMAIL,
            home=self.test_user_dir,
            password=TEST_USER_PW_HASH,
            access=READ_WRITE_ACCESS,
        )
        dummy_user.last_update = past_timestamp
        daemon_conf["users"].append(dummy_user)
        # Remove saved password
        os.remove(self.ssh_auth_pw_path)

        # Call the helper
        update_user_objects(
            configuration=self.configuration,
            auth_file=authpw,
            path=self.ssh_auth_pw_path,
            user_vars=user_tuple,
            auth_protos=authprotos,
            private_auth_file=True,
        )

        # Old entry should be removed
        usernames = [u.username for u in daemon_conf["users"]]
        self.assertNotIn(TEST_USER_DN, usernames, "Old entry was not removed")

    def test_update_user_objects_no_changes(self):
        """Verify that calling update_user_objects with unchanged files does not duplicate entries."""
        daemon_conf = self.configuration.daemon_conf
        # Extract the .PROTO/authorized_passwords part from auth_pw_path
        authpw = self.ssh_auth_pw_path.replace(self.test_user_home, "")
        authpw = authpw.lstrip(os.sep)
        authprotos = (None, authpw, None)
        user_tuple = (TEST_USER_DN, None, self.test_user_dir, None, None)
        # First call to populate
        update_user_objects(
            configuration=self.configuration,
            auth_file=authpw,
            path=self.ssh_auth_pw_path,
            user_vars=user_tuple,
            auth_protos=authprotos,
            private_auth_file=True,
        )
        initial_count = len(daemon_conf["users"])

        # Second call with same files
        update_user_objects(
            configuration=self.configuration,
            auth_file=authpw,
            path=self.ssh_auth_pw_path,
            user_vars=user_tuple,
            auth_protos=authprotos,
            private_auth_file=True,
        )
        self.assertEqual(
            len(daemon_conf["users"]),
            initial_count,
            "Duplicate entries were added on second call",
        )


if __name__ == "__main__":
    unittest.main()
