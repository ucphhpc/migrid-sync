# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_pwcrypto - unit test of the corresponding mig shared module
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

import base64
import os
import sys

from tests.support import MigTestCase, FakeConfiguration, \
    cleanpath, temppath, testmain

from mig.shared.defaults import POLICY_NONE, POLICY_WEAK, POLICY_MEDIUM, \
    POLICY_HIGH, POLICY_MODERN, POLICY_CUSTOM, PASSWORD_POLICIES
from mig.shared.pwcrypto import *


DUMMY_USER = "dummy-user"
DUMMY_ID = "dummy-id"
DUMMY_WEAK_PW = 'foobar'
DUMMY_MEDIUM_PW = 'QZFnCp7h'
DUMMY_HIGH_PW = 'QZFnp7I-GZ'
DUMMY_MODERN_PW = 'QZFnCp7hmI1G'
DUMMY_WEAK_PW_MD5 = "3858f62230ac3c915f300c664312c63f"
DUMMY_WEAK_PW_SHA256 = \
    "c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2"
DUMMY_WEAK_PW_PBKDF2 = \
    "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$epib2rEg/HYTQZFnCp7hmIGZ6rzHnViy"
DUMMY_HOME_DIR = 'dummy_user_home'
DUMMY_SETTINGS_DIR = 'dummy_user_settings'
# TODO: adjust password reset token helpers to handle configured services
#       it currently silently fails if not in migoid(c) or migcert
# DUMMY_SERVICE = 'dummy-svc'
DUMMY_SERVICE = 'migoid'
DUMMY_REALM = 'dummy-realm'
DUMMY_SALT = base64.b16encode(os.urandom(16))


class MigSharedPwCrypto(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def before_each(self):
        test_user_home = temppath(DUMMY_HOME_DIR, self, ensure_dir=True)
        test_user_settings = cleanpath(
            DUMMY_SETTINGS_DIR, self, ensure_dir=True)
        # make two requisite root folders for the dummy user
        os.mkdir(os.path.join(test_user_home, DUMMY_USER))
        os.mkdir(os.path.join(test_user_settings, DUMMY_USER))
        # now create a configuration
        self.dummy_conf = FakeConfiguration(
            user_home=test_user_home, user_settings=test_user_settings,
            site_password_policy="%s:12" % POLICY_MODERN,
            site_password_legacy_policy=POLICY_MEDIUM,
            site_password_cracklib=False,
            site_crypto_salt=DUMMY_SALT,
            site_password_salt=DUMMY_SALT,
            site_digest_salt=DUMMY_SALT,
            site_login_methods=[DUMMY_SERVICE],
        )

    def test_best_crypt_salt(self):
        """Test selection of best salt based on salt availability in
        configuration. Disable best choice in turn and check fallback.
        """
        expected = DUMMY_SALT
        actual = best_crypt_salt(self.dummy_conf)
        self.assertEqual(actual, expected, "best crypt salt not found")
        self.dummy_conf.site_crypto_salt = ''
        actual = best_crypt_salt(self.dummy_conf)
        self.assertEqual(actual, expected, "2nd best crypt salt not found")
        self.dummy_conf.site_password_salt = ''
        actual = best_crypt_salt(self.dummy_conf)
        self.assertEqual(actual, expected, "3rd best crypt salt not found")
        self.dummy_conf.site_digest_salt = ''
        actual = None
        try:
            actual = best_crypt_salt(self.dummy_conf)
        except Exception as exc:
            pass
        self.assertTrue(actual is None, "best crypt salt failed to err")

    def test_valid_login_password(self):
        """Test valid login password checker which assures password strength"""
        allow_weak = valid_login_password(self.dummy_conf, DUMMY_WEAK_PW)
        self.assertFalse(allow_weak, "allowed login with weak pw")
        allow_medium = valid_login_password(self.dummy_conf, DUMMY_MEDIUM_PW)
        self.assertTrue(allow_medium, "refused login with medium pw")
        allow_modern = valid_login_password(self.dummy_conf, DUMMY_MODERN_PW)
        self.assertTrue(allow_modern, "refused login with modern pw")

    def test_make_simple_hash_fixed_seed(self):
        """Test basic hashing of a fixed string to be constant"""
        expected = DUMMY_WEAK_PW_MD5
        actual = make_simple_hash(DUMMY_WEAK_PW)
        self.assertEqual(actual, expected, "mismatch simple hash string")

    def test_make_simple_hash_constant_string(self):
        """Test basic hashing of a fixed string to be constant for a particular
        random seed. I.e. the value may differ across interpreter invocations
        but remains constant in same interpreter.
        """
        first = make_simple_hash(DUMMY_WEAK_PW)
        second = make_simple_hash(DUMMY_WEAK_PW)
        self.assertEqual(first, second, "simple hashing is not constant")

    def test_make_safe_hash_fixed_seed(self):
        """Test basic hashing of a fixed string to be constant"""
        expected = DUMMY_WEAK_PW_SHA256
        actual = make_safe_hash(DUMMY_WEAK_PW)
        self.assertEqual(actual, expected, "mismatch safe hash string")

    def test_make_safe_hash_constant_string(self):
        """Test basic hashing of a fixed string to be constant for a particular
        random seed. I.e. the value may differ across interpreter invocations
        but remains constant in same interpreter.
        """
        first = make_safe_hash(DUMMY_WEAK_PW)
        second = make_safe_hash(DUMMY_WEAK_PW)
        self.assertEqual(first, second, "safe hashing is not constant")

    def test_make_hash_fixed_seed(self):
        """Test basic hashing of a fixed string to be constant for a fixed
        random seed.
        """
        expected = DUMMY_WEAK_PW_PBKDF2
        actual = make_hash(DUMMY_WEAK_PW, _urandom=lambda vlen: b'0' * vlen)
        self.assertEqual(actual, expected, "mismatch hashing string")

    def test_make_hash_constant_string(self):
        """Test basic hashing of a fixed string to be constant for a particular
        random seed. I.e. the value may differ across interpreter invocations
        but remains constant in same interpreter.
        """
        first = make_hash(DUMMY_WEAK_PW,
                          _urandom=lambda vlen: DUMMY_SALT[:vlen])
        second = make_hash(DUMMY_WEAK_PW,
                           _urandom=lambda vlen: DUMMY_SALT[:vlen])
        self.assertEqual(first, second, "same seed hashing is not constant")

    def test_check_hash_reject_weak(self):
        """Test basic hash checking of a constant weak complexity password"""
        expected = make_hash(DUMMY_WEAK_PW)
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_WEAK_PW, expected, strict_policy=True)
        self.assertFalse(result, "check hash should fail on weak pw")

    def test_check_hash_reject_medium_without_legacy(self):
        """Test basic hash checking of a constant medium complexity password
        without legacy password support.
        """
        expected = make_hash(DUMMY_MEDIUM_PW)
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_MEDIUM_PW, expected, strict_policy=True,
                            allow_legacy=False)
        self.assertFalse(result, "check hash strict should fail on medium pw")

    def test_check_hash_accept_medium_with_legacy(self):
        """Test basic hash checking of a constant medium complexity password
        with legacy password support.
        """
        expected = make_hash(DUMMY_MEDIUM_PW)
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_MEDIUM_PW, expected, strict_policy=True,
                            allow_legacy=True)
        self.assertTrue(result, "check hash with legacy must accept medium pw")

    def test_check_hash_accept_high(self):
        """Test basic hash checking of a constant high complexity password
        without legacy password support.
        """
        expected = make_hash(DUMMY_HIGH_PW)
        self.dummy_conf.site_password_policy = POLICY_HIGH
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_HIGH_PW, expected, strict_policy=True,
                            allow_legacy=False)
        self.assertTrue(result, "check hash must accept high complexity pw")

    def test_check_hash_accept_modern(self):
        """Test basic hash checking of a constant modern complexity password
        without legacy password support.
        """
        expected = make_hash(DUMMY_MODERN_PW)
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_MODERN_PW, expected, strict_policy=True,
                            allow_legacy=False)
        self.assertTrue(result, "check hash must accept modern complexity pw")

    def test_check_hash_fixed(self):
        """Test basic hash checking of a fixed string"""
        expected = make_hash(DUMMY_MEDIUM_PW)
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_MEDIUM_PW, expected, strict_policy=True)
        self.assertFalse(result, "check hash should reject medium pw")
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_MEDIUM_PW, expected, strict_policy=False,
                            allow_legacy=True)
        self.assertTrue(result, "check hash failed medium pw when not strict")
        expected = make_hash(DUMMY_MODERN_PW)
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_MODERN_PW, expected, strict_policy=True)
        self.assertTrue(result, "check hash failed modern pw")

    def test_check_hash_random(self):
        """Test basic hash checking of a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = make_hash(random_pw)
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            random_pw, expected)
        self.assertTrue(result, "mismatch in random hash check")

    def test_make_hash_variation(self):
        """Test how hashing of a fixed string varies depending on random seed.
        I.e. the value likely remains constant in same interpreter but differs
        across interpreter invocations.
        """
        first = make_hash(DUMMY_MODERN_PW,
                          _urandom=lambda vlen: DUMMY_SALT[:vlen])
        second = make_hash(DUMMY_MODERN_PW,
                           _urandom=lambda vlen: DUMMY_SALT[::-1][:vlen])
        self.assertNotEqual(first, second, "varying seed hashing is constant")

    def test_check_hash_despite_variation(self):
        """Test that check_hash works independently of random seed variation.
        I.e. the hash value differs across interpreter invocations but testing
        the same password against each succeeds.
        """
        first = make_hash(DUMMY_MODERN_PW,
                          _urandom=lambda vlen: DUMMY_SALT[:vlen])
        second = make_hash(DUMMY_MODERN_PW,
                           _urandom=lambda vlen: DUMMY_SALT[::-1][:vlen])
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_MODERN_PW, first)
        self.assertTrue(result, "mismatch in 1st random password hash check")
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            DUMMY_MODERN_PW, second)
        self.assertTrue(result, "mismatch in 2nd random password hash check")

    def test_check_digest(self):
        """Test basic digest checking of a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = make_digest(DUMMY_REALM, DUMMY_USER,
                               DUMMY_MODERN_PW, DUMMY_SALT)
        result = check_digest(self.dummy_conf, DUMMY_SERVICE, DUMMY_REALM,
                              DUMMY_USER, DUMMY_MODERN_PW, expected,
                              DUMMY_SALT)
        self.assertTrue(result, "mismatch in digest check")

    def test_check_scramble(self):
        """Test basic scramble checking of a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = make_scramble(DUMMY_MODERN_PW, DUMMY_SALT)
        result = check_scramble(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                                DUMMY_MODERN_PW, expected, DUMMY_SALT)
        self.assertTrue(result, "mismatch in scramble check")

    def test_fernet_encrypt_decrypt(self):
        """Test basic fernet password encrypt and decrypt on a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = fernet_encrypt_password(self.dummy_conf, random_pw)
        result = fernet_decrypt_password(self.dummy_conf, expected)
        self.assertEqual(random_pw, result, "failed fernet enc+dec")

    def test_aesgcm_encrypt_decrypt(self):
        """Test basic aesgcm password encrypt and decrypt on a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = aesgcm_encrypt_password(self.dummy_conf, random_pw)
        result = aesgcm_decrypt_password(self.dummy_conf, expected)
        self.assertEqual(random_pw, result, "failed aesgcm enc+dec")

    def test_aesgcm_encrypt_decrypt_static_iv(self):
        """Test basic aesgcm password encrypt and decrypt on a random string
        with a fixed initialization vector.
        """
        random_pw = generate_random_password(self.dummy_conf)
        entropy = make_safe_hash(random_pw, False)
        static_iv = prepare_aesgcm_iv(self.dummy_conf, iv_entropy=entropy)
        expected = aesgcm_encrypt_password(self.dummy_conf, random_pw,
                                           init_vector=static_iv)
        result = aesgcm_decrypt_password(self.dummy_conf, expected,
                                         init_vector=static_iv)
        self.assertEqual(random_pw, result, "failed aesgcm static iv enc+dec")

    def test_make_encrypt_decrypt(self):
        """Test default make encrypt and decrypt on a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = make_encrypt(self.dummy_conf, random_pw)
        result = make_decrypt(self.dummy_conf, expected)
        self.assertEqual(random_pw, result, "failed default enc+dec")

    def test_make_encrypt_variation(self):
        """Test make encrypt output variation on a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        # IMPORTANT: only aesgcm_static generates constant enc value!
        first = make_encrypt(self.dummy_conf, random_pw, algo="fernet")
        second = make_encrypt(self.dummy_conf, random_pw, algo="fernet")
        self.assertNotEqual(first, second, "aesgcm enc must not be constant")
        first = make_encrypt(self.dummy_conf, random_pw, algo="aesgcm")
        second = make_encrypt(self.dummy_conf, random_pw, algo="aesgcm")
        self.assertNotEqual(first, second, "fernet enc must not be constant")
        first = make_encrypt(self.dummy_conf, random_pw, algo="aesgcm_static")
        second = make_encrypt(self.dummy_conf, random_pw, algo="aesgcm_static")
        self.assertEqual(first, second, "aesgcm_static enc must be constant")

    def test_check_encrypt(self):
        """Test basic password simple encrypt and decrypt on a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        # IMPORTANT: only aesgcm_static generates constant enc value!
        encrypted = make_encrypt(self.dummy_conf, random_pw,
                                 algo="fernet")
        result = check_encrypt(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                               random_pw, encrypted, algo='fernet')
        self.assertFalse(result, "invalid match in fernet encrypt check")
        encrypted = make_encrypt(self.dummy_conf, random_pw, algo="aesgcm")
        result = check_encrypt(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                               random_pw, encrypted, algo='aesgcm')
        self.assertFalse(result, "invalid match in aesgcm encrypt check")
        encrypted = make_encrypt(self.dummy_conf, random_pw,
                                 algo="aesgcm_static")
        result = check_encrypt(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                               random_pw, encrypted, algo='aesgcm_static')
        self.assertTrue(result, "mismatch in aesgcm_static encrypt check")

    def test_password_reset_token_generate_and_verify(self):
        """Test basic password reset token generate and verify helper"""
        random_pw = generate_random_password(self.dummy_conf)
        hashed_pw = make_hash(random_pw)
        dummy_user = {'distinguished_name': DUMMY_USER}
        dummy_user['password_hash'] = hashed_pw
        timestamp = 42
        expected = generate_reset_token(self.dummy_conf, dummy_user,
                                        DUMMY_SERVICE, timestamp)
        parsed = parse_reset_token(self.dummy_conf, expected, DUMMY_SERVICE)
        self.assertEqual(parsed[0], timestamp, "failed parse token time")
        self.assertEqual(parsed[1], hashed_pw, "failed parse token hash")
        result = verify_reset_token(self.dummy_conf, dummy_user, expected,
                                    DUMMY_SERVICE, timestamp)
        self.assertTrue(result, "failed password reset token handling")

    def test_password_reset_token_verify_expired(self):
        """Test basic password reset token verify failure after it expired"""
        random_pw = generate_random_password(self.dummy_conf)
        hashed_pw = make_hash(random_pw)
        dummy_user = {'distinguished_name': DUMMY_USER}
        dummy_user['password_hash'] = hashed_pw
        timestamp = 42
        expected = generate_reset_token(self.dummy_conf, dummy_user,
                                        DUMMY_SERVICE, timestamp)
        parsed = parse_reset_token(self.dummy_conf, expected, DUMMY_SERVICE)
        self.assertEqual(parsed[0], timestamp, "failed parse token time")
        self.assertEqual(parsed[1], hashed_pw, "failed parse token hash")
        timestamp = 4242
        result = verify_reset_token(self.dummy_conf, dummy_user, expected,
                                    DUMMY_SERVICE, timestamp)
        self.assertFalse(result, "failed password reset token expiry check")

   # TODO: migrate remaining inline checks from module here instead


if __name__ == '__main__':
    testmain()
