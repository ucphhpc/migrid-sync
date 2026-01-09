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
import fcntl
import http.cookies
import os
import pickle
import time
import unittest
from unittest.mock import patch

from tests.support import MigTestCase, testmain, ensure_dirs_exist

import mig.shared.auth as auth
from mig.shared.base import client_id_dir
from mig.shared.defaults import twofactor_key_bytes, twofactor_cookie_ttl

TEST_USER_DN = \
    '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
GDP_USER_DN = '%s/GDP=projectx' % TEST_USER_DN
TEST_CLIENT_PREFIX = \
    '2e1c3d78bddf637ed6b83067c15ac9b9893545ff6a549519178cb4a252ed38b5'
DEFAULT_INTERVAL = 30


class MigSharedAuth__twofactor(MigTestCase):
    """Unit tests for two-factor authentication in auth module"""

    def _provide_configuration(self):
        return 'testconfig'

    def _mimic_cookie_init(self, session_key):
        """Mimic twofactor session cookie setup"""
        cookie = http.cookies.SimpleCookie()
        session_start = time.time()
        cookie['2FA_Auth'] = session_key
        cookie['2FA_Auth']['path'] = '/'
        # NOTE: SimpleCookie translates expires ttl to actual date from now
        cookie['2FA_Auth']['expires'] = twofactor_cookie_ttl
        cookie['2FA_Auth']['secure'] = True
        cookie['2FA_Auth']['httponly'] = True
        environ = {'HTTP_COOKIE': cookie}
        return environ

    def before_each(self):
        """Setup test environment before each test method"""
        ensure_dirs_exist(self.configuration.user_cache)
        ensure_dirs_exist(self.configuration.user_pending)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.mrsl_files_dir)
        ensure_dirs_exist(self.configuration.resource_pending)
        ensure_dirs_exist(self.configuration.twofactor_home)
        self.configuration.site_enable_gdp = False  # Disable GDP by default

    def test_twofactor_available(self):
        """Test pyotp availability detection"""
        # Positive case (assuming pyotp is installed)
        self.assertTrue(auth.twofactor_available(self.configuration))

        # Simulate missing pyotp
        original_pyotp = auth.pyotp
        auth.pyotp = None
        self.assertFalse(auth.twofactor_available(self.configuration))
        auth.pyotp = original_pyotp

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

    def test_save_twofactor_session(self):
        """Test save twofactor session"""
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

    def test_list_twofactor_session(self):
        """Test list saved twofactor session"""
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

    def test_load_twofactor_session(self):
        """Test load saved twofactor session"""
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

        # Validate session details
        session_data = auth.load_twofactor_session(self.configuration,
                                                   session_key)
        self.assertEqual(session_data['client_id'], TEST_USER_DN,
                         'session should match client_id'
                         )
        self.assertEqual(session_data['session_end'], session_start +
                         twofactor_cookie_ttl,
                         'session should have correct TTL')

    def test_twofactor_session_lifecycle(self):
        """Test full twofactor session lifecycle as an integration test"""
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
        environ = self._mimic_cookie_init(session_key)

        # Expire session
        expire_result = auth.expire_twofactor_session(self.configuration,
                                                      TEST_USER_DN, environ)
        self.assertTrue(expire_result, 'session should expire successfully')
        sessions_after = auth.list_twofactor_sessions(self.configuration,
                                                      TEST_USER_DN)
        self.assertNotIn(session_key, sessions_after,
                         'session should be removed')

    def test_load_twofactor_key_missing(self):
        """Test handling of missing twofactor key"""
        self._provision_test_user(self, TEST_USER_DN)
        result = auth.load_twofactor_key(TEST_USER_DN, self.configuration,
                                         allow_missing=True)
        self.assertIsNone(result, 'should return None for missing key')

    def test_generate_session_prefix(self):
        """Test session prefix generation"""
        prefix = auth.generate_session_prefix(self.configuration, TEST_USER_DN)
        self.assertEqual(prefix, TEST_CLIENT_PREFIX)

    def test_gdp_client_id_transformation(self):
        """Test GDP client ID normalization"""
        self.configuration.site_enable_gdp = True
        from mig.shared.gdp.all import get_base_client_id
        base_dn = get_base_client_id(self.configuration, GDP_USER_DN,
                                     expand_oid_alias=False)

        # With GDP enabled, ID should be transformed to base project
        session_key = auth.generate_session_key(self.configuration,
                                                GDP_USER_DN)
        base_prefix = auth.generate_session_prefix(self.configuration, base_dn)
        self.assertTrue(session_key.startswith(base_prefix))

    def test_client_twofactor_session_parsing(self):
        """Test cookie parsing for session ID extraction"""
        cookie = http.cookies.SimpleCookie()
        cookie['2FA_Auth'] = 'test_session_id'
        environ = {'HTTP_COOKIE': cookie.output(header='')}

        session_id = auth.client_twofactor_session(self.configuration,
                                                   TEST_USER_DN, environ)
        self.assertEqual(session_id, 'test_session_id',
                         'should extract session ID from cookies')

    def test_multiple_active_sessions(self):
        """Test handling of multiple concurrent sessions"""
        client_dir = self._provision_test_user(self, TEST_USER_DN)

        # Create 3 sessions from different addresses
        sessions = []
        for addr in ['192.168.0.1', '10.0.0.1', '172.16.0.1']:
            session_key = auth.generate_session_key(self.configuration,
                                                    TEST_USER_DN)
            auth.save_twofactor_session(
                self.configuration, TEST_USER_DN, session_key,
                addr, 'TestAgent', time.time()
            )
            sessions.append(session_key)

        # List all sessions
        all_sessions = auth.list_twofactor_sessions(self.configuration,
                                                    TEST_USER_DN)
        self.assertEqual(len(all_sessions), 3,
                         'should list all active sessions')

        # Filter by address
        filtered = auth.list_twofactor_sessions(
            self.configuration, TEST_USER_DN, user_addr='10.0.0.1')
        self.assertEqual(len(filtered), 1,
                         'should filter sessions by address')

    def test_expired_session_cleanup(self):
        """Test automatic exclusion of expired sessions"""
        client_dir = self._provision_test_user(self, TEST_USER_DN)
        valid_key = auth.generate_session_key(self.configuration,
                                              TEST_USER_DN)
        expired_key = auth.generate_session_key(self.configuration,
                                                TEST_USER_DN)

        # Create valid session (expires future)
        auth.save_twofactor_session(
            self.configuration, TEST_USER_DN, valid_key,
            '127.0.0.1', 'TestAgent', time.time()
        )

        # Create expired session
        auth.save_twofactor_session(
            self.configuration, TEST_USER_DN, expired_key,
            '127.0.0.1', 'TestAgent', time.time() - twofactor_cookie_ttl - 100
        )

        # Only valid session should appear in active listings
        active = auth.active_twofactor_session(
            self.configuration, TEST_USER_DN, '127.0.0.1')
        self.assertEqual(active['session_key'], valid_key,
                         'should only return active sessions')

    def test_custom_token_interval(self):
        """Test token verification with custom interval"""
        self._provision_test_user(self, TEST_USER_DN)

        # Save custom interval
        client_dir = client_id_dir(TEST_USER_DN)
        interval_path = os.path.join(self.configuration.user_settings,
                                     client_dir, 'twofactor_interval')
        with open(interval_path, 'w') as fh:
            fh.write('60')  # 1 minute interval

        # Generate key with custom interval
        b32_key = auth.reset_twofactor_key(
            TEST_USER_DN, self.configuration, interval=60)

        totp = auth.get_totp(TEST_USER_DN, b32_key, self.configuration)
        valid_token = totp.now()

        # Verify works with custom interval
        result = auth.verify_twofactor_token(
            self.configuration, TEST_USER_DN, b32_key, valid_token)
        self.assertTrue(result, 'should accept token with custom interval')

    def test_strict_address_session_handling(self):
        """Test full session handling with strict source address enforcement"""
        self.configuration.site_twofactor_strict_address = True
        session_key = auth.generate_session_key(self.configuration,
                                                TEST_USER_DN)
        user_addr = '192.168.1.100'

        auth.save_twofactor_session(
            self.configuration, TEST_USER_DN, session_key,
            user_addr, 'TestAgent', time.time()
        )

        # Should have address-linked file
        addr_file = os.path.join(self.configuration.twofactor_home,
                                 "%s_%s" % (user_addr, session_key))
        self.assertTrue(os.path.exists(addr_file),
                        'should create address-linked session file')

        # Mimic cookie init
        environ = self._mimic_cookie_init(session_key)

        # Expire should remove both files
        auth.expire_twofactor_session(self.configuration, TEST_USER_DN,
                                      environ, user_addr=user_addr)
        self.assertFalse(os.path.exists(addr_file),
                         'should remove address-linked session file')
        self.assertFalse(os.path.exists(
            os.path.join(self.configuration.twofactor_home, session_key)
        ), 'should remove main session file')

    def test_check_twofactor_active_missing_session(self):
        """Test session check when session cookie is missing"""
        self._provision_test_user(self, TEST_USER_DN)
        # Empty environment
        result = auth.check_twofactor_active(self.configuration,
                                             TEST_USER_DN, '127.0.0.1', {})
        self.assertFalse(result, 'should reject missing session')

        # Invalid cookie
        cookie = http.cookies.SimpleCookie()
        cookie['invalid'] = 'value'
        environ = {'HTTP_COOKIE': cookie.output(header='')}
        result = auth.check_twofactor_active(self.configuration,
                                             TEST_USER_DN, '127.0.0.1', environ)
        self.assertFalse(result, 'should reject invalid session cookie')

    def test_session_prefix_hashing_consistency(self):
        """Test session prefix hash consistency across calls"""
        client_id = '/C=US/O=Example/CN=Test User'
        prefix1 = auth.generate_session_prefix(self.configuration, client_id)
        prefix2 = auth.generate_session_prefix(self.configuration, client_id)
        self.assertEqual(prefix1, prefix2,
                         'session prefix should be consistent for same client_id')

        # Verify prefix changes with different client_id
        prefix3 = auth.generate_session_prefix(
            self.configuration, TEST_USER_DN)
        self.assertNotEqual(prefix1, prefix3,
                            'prefix should change with client_id')

    def test_malformed_session_file_handling(self):
        """Test graceful handling of corrupted session files"""
        session_key = auth.generate_session_key(self.configuration,
                                                TEST_USER_DN)
        session_path = os.path.join(self.configuration.twofactor_home,
                                    session_key)

        # Create malformed pickle file
        with open(session_path, 'wb') as fh:
            fh.write(b'invalid pickle content')

        # Attempt to load should return empty dict
        session_data = auth.load_twofactor_session(self.configuration,
                                                   session_key)
        self.assertEqual(session_data.get('client_id', ''), 'UNKNOWN',
                         'should handle malformed session files gracefully')
        self.assertEqual(session_data.get('user_addr', ''), 'UNKNOWN',
                         'should handle malformed session files gracefully')

    @unittest.skipIf(os.getuid() == 0, "Permissions don't work for priv users")
    def test_session_file_access_restriction(self):
        """Test session file permissions to be not globally readable"""
        orig_umask = os.umask(0o000)
        session_key = auth.generate_session_key(self.configuration,
                                                TEST_USER_DN)
        user_addr = '192.168.1.1'

        auth.save_twofactor_session(self.configuration, TEST_USER_DN,
                                    session_key, user_addr, 'TestAgent',
                                    time.time())

        os.umask(orig_umask)
        session_path = os.path.join(self.configuration.twofactor_home,
                                    session_key)
        mode = os.stat(session_path).st_mode
        expected = 0o660
        self.assertEqual(mode & 0o777, expected,
                         'session files should have restrictive permissions')

    def test_gdp_oid_alias_handling(self):
        """Test GDP client ID with OID alias expansion"""
        self.configuration.site_enable_gdp = True
        self.configuration.user_openid_alias = 'email'

        # Generate session key should resolve to base GDP ID
        session_key = auth.generate_session_key(self.configuration,
                                                TEST_USER_DN)
        base_prefix = auth.generate_session_prefix(self.configuration,
                                                   GDP_USER_DN)
        self.assertTrue(session_key.startswith(base_prefix),
                        'should resolve OID alias to base GDP ID')

    def test_token_window_boundaries(self):
        """Test token validation at window boundaries"""
        self._provision_test_user(self, TEST_USER_DN)
        b32_key, _, _ = auth.get_twofactor_secrets(self.configuration,
                                                   TEST_USER_DN)

        # Create TOTP with small test window
        with patch.object(auth, 'valid_otp_window', 1):
            totp = auth.get_totp(TEST_USER_DN, b32_key, self.configuration)

            # Generate token slightly outside window
            test_time = datetime.datetime.fromtimestamp(
                int(time.time() - DEFAULT_INTERVAL * 3))
            boundary_token = totp.generate_otp(totp.timecode(test_time))

            # Verify should accept within window but reject outside
            is_valid = auth.verify_twofactor_token(self.configuration, TEST_USER_DN,
                                                   b32_key, boundary_token)
            self.assertFalse(is_valid, 'should reject tokens outside window')

            # Generate valid boundary token
            test_time = datetime.datetime.fromtimestamp(
                int(time.time() - DEFAULT_INTERVAL * 1))

            valid_boundary = totp.generate_otp(totp.timecode(test_time))
            is_valid = auth.verify_twofactor_token(self.configuration, TEST_USER_DN,
                                                   b32_key, valid_boundary)
            self.assertTrue(is_valid, 'should accept tokens within window')

    def test_nested_session_directories(self):
        """Test session listing with nested directories"""
        session_key = auth.generate_session_key(
            self.configuration, TEST_USER_DN)

        # Create session in subdirectory
        nested_path = os.path.join(self.configuration.twofactor_home, 'subdir')
        ensure_dirs_exist(nested_path)
        session_path = os.path.join(nested_path, session_key)

        with open(session_path, 'wb') as fh:
            pickle.dump({'client_id': TEST_USER_DN}, fh)

        # Should ignore nested structure
        sessions = auth.list_twofactor_sessions(
            self.configuration, TEST_USER_DN)
        self.assertEqual(len(sessions), 0,
                         'should ignore sessions in subdirectories')

    @unittest.skip("TODO: enable once tested function handles errors")
    def test_failed_file_operations(self):
        """Test graceful handling of file operation failures"""
        client_dir = self._provision_test_user(self, TEST_USER_DN)

        # Make directory read-only
        user_settings_path = os.path.join(self.configuration.user_settings,
                                          client_dir)
        os.chmod(user_settings_path, 0o555)

        # Attempt key generation should fail
        with self.assertRaises(Exception) as cm:
            auth.get_twofactor_secrets(self.configuration, TEST_USER_DN)
        self.assertIn('failed to reset 2FA key', str(cm.exception))

    @unittest.skip("TODO: implement locking and enable")
    def test_session_lock_conflicts(self):
        """Test concurrent session file access"""
        session_key = auth.generate_session_key(self.configuration,
                                                TEST_USER_DN)
        session_path = os.path.join(self.configuration.twofactor_home,
                                    session_key)

        # Create test session
        auth.save_twofactor_session(self.configuration, TEST_USER_DN,
                                    session_key, '127.0.0.1', 'TestAgent',
                                    time.time())

        # Lock session file
        with open(session_path, 'rb') as fh:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Attempt loading should handle locked file
            session_data = auth.load_twofactor_session(
                self.configuration, session_key)
            self.assertEqual(session_data, {},
                             'should return empty data for locked files')

    def test_custom_interval_fallback(self):
        """Test default interval fallback when given custom interval fails"""
        self._provision_test_user(self, TEST_USER_DN)

        # Save invalid interval
        client_dir = client_id_dir(TEST_USER_DN)
        interval_path = os.path.join(self.configuration.user_settings,
                                     client_dir, 'twofactor_interval')
        with open(interval_path, 'w') as fh:
            fh.write('invalid-number')

        b32_key, _, _ = auth.get_twofactor_secrets(
            self.configuration, TEST_USER_DN)
        totp = auth.get_totp(TEST_USER_DN, b32_key, self.configuration)
        token = totp.now()

        # Verification should fallback to default interval
        result = auth.verify_twofactor_token(
            self.configuration, TEST_USER_DN, b32_key, token)
        self.assertTrue(result, 'should fallback to default interval on error')


if __name__ == '__main__':
    testmain()
