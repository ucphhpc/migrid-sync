# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_auth - unit tests for authentication helpers
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

"""Unit tests for authentication functionality in mig/shared/auth.py"""

import datetime
import http.cookies
import os
import pickle
import time
import unittest

from tests.support import MigTestCase, testmain, ensure_dirs_exist

import mig.shared.auth as auth
from mig.shared.base import client_id_dir
from mig.shared.defaults import twofactor_key_bytes, twofactor_cookie_ttl

TEST_USER_DN = \
    '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'


class MigSharedAuth__twofactor(MigTestCase):
    """Unit tests for two-factor authentication in auth module"""

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        """Setup test environment before each test method"""
        ensure_dirs_exist(self.configuration.user_cache)
        ensure_dirs_exist(self.configuration.user_pending)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.mrsl_files_dir)
        ensure_dirs_exist(self.configuration.resource_pending)
        ensure_dirs_exist(self.configuration.twofactor_home)

    def test_get_twofactor_secrets_generates_valid_key(self):
        """Test get_twofactor_secrets generates and stores valid key"""
        self._provision_test_user(self, TEST_USER_DN)

        # Exercise functionality
        b32_key, interval, otp_uri = auth.get_twofactor_secrets(
            self.configuration, TEST_USER_DN)

        # Verify results
        self.assertIsNotNone(b32_key)
        self.assertEqual(
            len(b32_key), twofactor_key_bytes,
            'generated key length should match configured bytes'
        )
        self.assertIn(
            'otpauth://', otp_uri,
            'OTP URI should use standard provisioning format'
        )
        self.assertIn(
            self.configuration.short_title, otp_uri,
            'OTP URI should include site title as issuer'
        )

    def test_verify_twofactor_token_valid(self):
        """Test valid token verification"""
        self._provision_test_user(self, TEST_USER_DN)
        b32_key, _, _ = auth.get_twofactor_secrets(
            self.configuration, TEST_USER_DN)

        # Generate current valid token
        totp = auth.get_totp(TEST_USER_DN, b32_key, self.configuration)
        valid_token = totp.now()

        # Verify token
        result = auth.verify_twofactor_token(self.configuration, TEST_USER_DN,
                                             b32_key, valid_token)

        self.assertTrue(result, 'valid token should be accepted')

    def test_verify_twofactor_token_invalid(self):
        """Test invalid token rejection"""
        self._provision_test_user(self, TEST_USER_DN)
        b32_key, _, _ = auth.get_twofactor_secrets(
            self.configuration, TEST_USER_DN)
        invalid_token = '000000'

        result = auth.verify_twofactor_token(self.configuration, TEST_USER_DN,
                                             b32_key, invalid_token)

        self.assertFalse(result, 'invalid token should be rejected')

    def test_reset_twofactor_key(self):
        """Test twofactor key reset changes stored key"""
        self._provision_test_user(self, TEST_USER_DN)
        original_key, _, _ = auth.get_twofactor_secrets(self.configuration,
                                                        TEST_USER_DN)

        # Reset key
        new_key_b32 = auth.reset_twofactor_key(TEST_USER_DN,
                                               self.configuration)
        new_key = new_key_b32.decode('utf8')

        # Verify change
        self.assertNotEqual(original_key, new_key, 'new key should differ')
        self.assertEqual(len(new_key), twofactor_key_bytes,
                         'new key should have correct length')

        # Verify persistence
        reloaded_key = auth.load_twofactor_key(TEST_USER_DN,
                                               self.configuration)
        #
        self.assertEqual(new_key, reloaded_key, 'key should persist')

    def test_twofactor_session_lifecycle(self):
        """Test full twofactor session lifecycle"""
        client_dir = self._provision_test_user(self, TEST_USER_DN)
        user_addr = '127.0.0.1'
        user_agent = 'TestAgent'
        session_start = time.time()
        session_cookie = ''

        # Generate session
        session_key = auth.generate_session_key(self.configuration,
                                                TEST_USER_DN)
        save_result = auth.save_twofactor_session(self.configuration,
                                                  TEST_USER_DN, session_key,
                                                  user_addr, user_agent,
                                                  session_start)
        self.assertTrue(save_result, 'session should save successfully')

        # Verify session exists
        sessions = auth.list_twofactor_sessions(self.configuration,
                                                TEST_USER_DN)
        self.assertIn(session_key, sessions, 'new session should be listed')

        # Validate session details
        session_data = auth.load_twofactor_session(self.configuration,
                                                   session_key)
        self.assertEqual(session_data['client_id'], TEST_USER_DN,
                         'session should match client_id'
                         )
        self.assertEqual(session_data['session_end'], session_start +
                         twofactor_cookie_ttl,
                         'session should have correct TTL')

        # Mimic cookie init
        cookie = http.cookies.SimpleCookie()
        session_start = time.time()
        cookie['2FA_Auth'] = session_key
        cookie['2FA_Auth']['path'] = '/'
        # NOTE: SimpleCookie translates expires ttl to actual date from now
        cookie['2FA_Auth']['expires'] = twofactor_cookie_ttl
        cookie['2FA_Auth']['secure'] = True
        cookie['2FA_Auth']['httponly'] = True

        environ = {'HTTP_COOKIE': cookie}
        # Expire session
        expire_result = auth.expire_twofactor_session(self.configuration,
                                                      TEST_USER_DN, environ)
        self.assertTrue(expire_result, 'session should expire successfully')
        sessions_after = auth.list_twofactor_sessions(self.configuration,
                                                      TEST_USER_DN)
        self.assertNotIn(session_key, sessions_after,
                         'session should be removed')


if __name__ == '__main__':
    testmain()
