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
import unittest

from mig.shared.defaults import (
    PASSWORD_POLICIES,
    POLICY_CUSTOM,
    POLICY_HIGH,
    POLICY_MEDIUM,
    POLICY_MODERN,
    POLICY_NONE,
    POLICY_WEAK,
)
from mig.shared.pwcrypto import *
from mig.shared.pwcrypto import main as pwcrypto_main
from tests.support import (
    FakeConfiguration,
    MigTestCase,
    cleanpath,
    temppath,
    testmain,
)

DUMMY_USER = "dummy-user"
DUMMY_ID = "dummy-id"
# NOTE: these passwords are not and should not ever be used outside unit tests
DUMMY_WEAK_PW = "foobar"
DUMMY_MEDIUM_PW = "QZFnCp7h"
DUMMY_HIGH_PW = "QZFnp7I-GZ"
DUMMY_MODERN_PW = "QZFnCp7hmI1G"
DUMMY_GENERATED_PW = "7hmI1GnCpQZF"
DUMMY_WEAK_PW_MD5 = "3858f62230ac3c915f300c664312c63f"
DUMMY_WEAK_PW_SHA256 = (
    "c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2"
)
DUMMY_WEAK_PW_PBKDF2 = (
    "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$epib2rEg/HYTQZFnCp7hmIGZ6rzHnViy"
)
DUMMY_MEDIUM_PW_PBKDF2 = (
    "PBKDF2$sha256$10000$ebQHnDX1rzY9Rizb$0vUJ9/4ThhsN4cRaKYmOj4N0YKEsozTr"
)
DUMMY_HIGH_PW_PBKDF2 = (
    "PBKDF2$sha256$10000$HR+KcqLyQe3v0WSk$CtxMAomi8JHiI7gWc/PH5Ey00zW1Now3"
)
DUMMY_MODERN_PW_MD5 = "a06d169a171ef7d4383b212457162d93"
DUMMY_MODERN_PW_SHA256 = (
    "d293dcb9762c87641ea1decbfe76d84ec51b13d6a1e688cdf1a838eebc5bb1a9"
)
DUMMY_MODERN_PW_PBKDF2 = (
    "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$B22uw6C7C4VFiYAe4Vf10n58FHrn1pjX"
)
DUMMY_MODERN_PW_DIGEST = "DIGEST$custom$CONFSALT$64756D6D792D7265616C6D3A64756D6D792D7520DE71261F96A2FE48A67DD0877F2A2C"
DUMMY_MODERN_DIGEST_SCRAMBLE = "53BB031C1F96A2FE48A67DD0877F2A2C"
DUMMY_MODERN_PW_SCRAMBLE = "53BB031C1F96A2FE48A67DD0877F2A2C"
DUMMY_MODERN_PW_AESGCM_SIV_ENCRYPTED = b"xRsT1qHmiM3xqDjuvFuxqQ==.g4-Gt83uRrdvVWwX0SF1iMza3NyKJbp2sEYVkw==.ICAgIG1pZ3JpZCBhdXRoZW50aWNhdGVkMjA1MDAxMDE="
DUMMY_MODERN_PW_RESET_TOKEN = b"gAAAAABo63hYqeHE7Db93pMxWn1sWzj2Z-6td2UhA5gKYa4KV096ndV-AO0pp6hrR9jXKcwWAouLCMiNC0BRudeCAYHoBii15lTRbP9b7JzvJjeusbidjRxqcJg0om6bbtSK1Rz_RBTq_jhdAk4v-7PccWlZ15dVJ4j-X3X4zSsBWIOR5y6Y-bA="
DUMMY_METHOD = "dummy-method"
DUMMY_OPERATION = "dummy-operation"
DUMMY_ARGS = {"dummy-key": "dummy-val"}
DUMMY_CSRF_TOKEN = (
    "351cc47e0cd5c155fa4c4d3d0a6f1ee8f20eeb293ba13d59ede9d2a789687d3d"
)
DUMMY_CSRF_TRUST_TOKEN = (
    "466c0bacd045a060a201c4e08c749c2e19743613422e0381ab0a57706c9fa2b8"
)
DUMMY_HOME_DIR = "dummy_user_home"
DUMMY_SETTINGS_DIR = "dummy_user_settings"
# TODO: adjust password reset token helpers to handle configured services
#       it currently silently fails if not in migoid(c) or migcert
# DUMMY_SERVICE = 'dummy-svc'
DUMMY_SERVICE = "migoid"
DUMMY_REALM = "dummy-realm"
DUMMY_PATH = "dummy-path"
DUMMY_PATH_MD5 = "d19033877452e8c217d3cddebbc37419"
DUMMY_SALT = b"53BB031C4ECCE4900BD64AB8EA361B6B"
DUMMY_ENTROPY = b"\xd2\x93\xdc\xb9v,\x87d\x1e\xa1\xde\xcb\xfev\xd8N\xc5\x1b\x13\xd6\xa1\xe6\x88\xcd\xf1\xa88\xee\xbc[\xb1\xa9"
DUMMY_FERNET_KEY = "NDg3OTcyNzE1NTQ2Nzc3ODYxNjc0NjRFRDZGMjNFQzY="
DUMMY_AESGCM_KEY = b"48797271554677786167464ED6F23EC6"
DUMMY_AESGCM_STATIC_IV = (
    b"\xc5\x1b\x13\xd6\xa1\xe6\x88\xcd\xf1\xa88\xee\xbc[\xb1\xa9"
)
DUMMY_AESGCM_AAD_PREFIX = b"\xc5\x1b\x13\xd6\xa1\xe6\x88\xcd\xf1\xa88\xee\xbc[\xb1\xa9\xa88\xee\xbc[\xb1\xa9"
DUMMY_AESGCM_AAD = b" \xc5\x1b\x13\xd6\xa1\xe6\x88\xcd\xf1\xa88\xee\xbc[\xb1\xa9\xa88\xee\xbc[\xb1\xa920500101"
# NOTE: we avoid any percent expansion values of actual date here to freeze AAD
DUMMY_FIXED_TIMESTAMP = "20500101"


class MigSharedPwCrypto(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def before_each(self):
        test_user_home = temppath(DUMMY_HOME_DIR, self, ensure_dir=True)
        test_user_settings = cleanpath(
            DUMMY_SETTINGS_DIR, self, ensure_dir=True
        )
        # make two requisite root folders for the dummy user
        os.mkdir(os.path.join(test_user_home, DUMMY_USER))
        os.mkdir(os.path.join(test_user_settings, DUMMY_USER))
        # now create a configuration
        self.dummy_conf = FakeConfiguration(
            user_home=test_user_home,
            user_settings=test_user_settings,
            site_password_policy="%s:12" % POLICY_MODERN,
            site_password_legacy_policy=POLICY_MEDIUM,
            site_password_cracklib=False,
            site_crypto_salt=DUMMY_SALT,
            site_password_salt=DUMMY_SALT,
            site_digest_salt=DUMMY_SALT,
            site_login_methods=[DUMMY_SERVICE],
            site_signup_methods=[DUMMY_SERVICE],
        )
        # TODO: fix the below pylint issue to make CI happy without this hack
        # NOTE: for whatever reason pylint fails with Instance of
        #       'FakeConfiguration' has no 'site_password_legacy_policy' member
        #       (no-member) unless we explicitly (re-)init it here
        self.dummy_conf.site_password_legacy_policy = getattr(
            self.dummy_conf, "site_password_legacy_policy", POLICY_NONE
        )
        self.assertEqual(
            self.dummy_conf.site_password_legacy_policy, POLICY_MEDIUM
        )

    def test_best_crypt_salt(self):
        """Test selection of best salt based on salt availability in
        configuration. Disable best choice in turn and check fallback.
        """
        expected = DUMMY_SALT
        actual = best_crypt_salt(self.dummy_conf)
        self.assertEqual(actual, expected, "best crypt salt not found")
        self.dummy_conf.site_crypto_salt = ""
        actual = best_crypt_salt(self.dummy_conf)
        self.assertEqual(actual, expected, "2nd best crypt salt not found")
        self.dummy_conf.site_password_salt = ""
        actual = best_crypt_salt(self.dummy_conf)
        self.assertEqual(actual, expected, "3rd best crypt salt not found")
        self.dummy_conf.site_digest_salt = ""
        actual = None
        try:
            actual = best_crypt_salt(self.dummy_conf)
        except Exception as exc:
            pass
        self.assertTrue(actual is None, "best crypt salt failed to err")

    def test_password_requirements(self):
        """Test parse password policy for default MODERN and legacy MEDIUM"""
        expected = (12, 1, [])
        result = password_requirements(self.dummy_conf.site_password_policy)
        self.assertEqual(expected[0], result[0], "failed pw req chars")
        self.assertEqual(expected[1], result[1], "failed pw req classes")
        self.assertEqual(expected[2], result[2], "failed pw req errors")
        expected = (8, 3, [])
        result = password_requirements(
            self.dummy_conf.site_password_legacy_policy
        )
        self.assertEqual(expected[0], result[0], "failed legacy pw req chars")
        self.assertEqual(expected[1], result[1], "failed legacy pw req classes")
        self.assertEqual(expected[2], result[2], "failed legacy pw req errors")

    def test_parse_password_policy(self):
        """Test parse password policy for default MODERN and legacy MEDIUM"""
        expected = (12, 1)
        result = parse_password_policy(self.dummy_conf)
        self.assertEqual(expected[0], result[0], "failed parse policy chars")
        self.assertEqual(expected[1], result[1], "failed parse policy classes")
        expected = (8, 3)
        result = parse_password_policy(self.dummy_conf, use_legacy=True)
        self.assertEqual(expected[0], result[0], "failed parse policy chars")
        self.assertEqual(expected[1], result[1], "failed parse policy classes")

    def test_assure_password_strength(self):
        """Test assure password strength"""
        try:
            allow_weak = assure_password_strength(
                self.dummy_conf, DUMMY_WEAK_PW
            )
        except ValueError as vae:
            allow_weak = False
        self.assertFalse(allow_weak, "allowed weak pw")
        try:
            allow_weak = assure_password_strength(
                self.dummy_conf, DUMMY_WEAK_PW, allow_legacy=True
            )
        except ValueError as vae:
            allow_weak = False
        self.assertFalse(allow_weak, "allowed weak pw with legacy")
        # NOTE: only allow medium with legacy
        try:
            allow_medium = assure_password_strength(
                self.dummy_conf, DUMMY_MEDIUM_PW
            )
        except ValueError as vae:
            allow_medium = False
        self.assertFalse(allow_medium, "allowed medium pw without legacy")
        try:
            allow_medium = assure_password_strength(
                self.dummy_conf, DUMMY_MEDIUM_PW, allow_legacy=True
            )
        except ValueError as vae:
            allow_medium = False
        self.assertTrue(allow_medium, "refused medium pw with legacy")
        # NOTE: only allow high with legacy - not long enough for modern
        try:
            allow_high = assure_password_strength(
                self.dummy_conf, DUMMY_HIGH_PW
            )
        except ValueError as vae:
            allow_high = False
        self.assertFalse(allow_high, "allowed high pw without legacy")
        try:
            allow_high = assure_password_strength(
                self.dummy_conf, DUMMY_HIGH_PW, allow_legacy=True
            )
        except ValueError as vae:
            allow_high = False
        self.assertTrue(allow_high, "refused high pw with legacy")
        try:
            allow_modern = assure_password_strength(
                self.dummy_conf, DUMMY_MODERN_PW
            )
        except ValueError as vae:
            allow_modern = False
        self.assertTrue(allow_modern, "refused modern pw")
        try:
            allow_modern = assure_password_strength(
                self.dummy_conf, DUMMY_MODERN_PW, allow_legacy=True
            )
        except ValueError as vae:
            allow_modern = False
        self.assertTrue(allow_modern, "refused modern pw with legacy")

    def test_valid_login_password(self):
        """Test valid login password checker which assures password strength"""
        allow_weak = valid_login_password(self.dummy_conf, DUMMY_WEAK_PW)
        self.assertFalse(allow_weak, "allowed login with weak pw")
        allow_medium = valid_login_password(self.dummy_conf, DUMMY_MEDIUM_PW)
        self.assertTrue(allow_medium, "refused login with medium pw")
        allow_modern = valid_login_password(self.dummy_conf, DUMMY_MODERN_PW)
        self.assertTrue(allow_modern, "refused login with modern pw")

    def test_make_simple_hash_fixed(self):
        """Test basic hashing of a fixed string to be constant"""
        expected = DUMMY_MODERN_PW_MD5
        actual = make_simple_hash(DUMMY_MODERN_PW)
        self.assertEqual(actual, expected, "mismatch simple hash string")

    def test_make_simple_hash_constant_string(self):
        """Test basic hashing of a fixed string to be constant"""
        first = make_simple_hash(DUMMY_MODERN_PW)
        second = make_simple_hash(DUMMY_MODERN_PW)
        self.assertEqual(first, second, "simple hashing is not constant")

    def test_make_path_hash_fixed(self):
        """Test basic hashing of a fixed path string to be constant"""
        expected = DUMMY_PATH_MD5
        actual = make_path_hash(self.dummy_conf, DUMMY_PATH)
        self.assertEqual(actual, expected, "mismatch path hash string")

    def test_make_path_hash_constant_string(self):
        """Test basic hashing of a fixed path string to be constant"""
        first = make_path_hash(self.dummy_conf, DUMMY_PATH)
        second = make_path_hash(self.dummy_conf, DUMMY_PATH)
        self.assertEqual(first, second, "path hashing is not constant")

    def test_make_safe_hash_fixed(self):
        """Test basic hashing of a fixed string to be constant"""
        expected = DUMMY_MODERN_PW_SHA256
        actual = make_safe_hash(DUMMY_MODERN_PW)
        self.assertEqual(actual, expected, "mismatch safe hash string")

    def test_make_safe_hash_constant_string(self):
        """Test basic hashing of a fixed string to be constant"""
        first = make_safe_hash(DUMMY_MODERN_PW)
        second = make_safe_hash(DUMMY_MODERN_PW)
        self.assertEqual(first, second, "safe hashing is not constant")

    def test_make_hash_fixed_seed(self):
        """Test basic hashing of a fixed string to be constant for a fixed
        random seed.
        """
        expected = DUMMY_MODERN_PW_PBKDF2
        actual = make_hash(DUMMY_MODERN_PW, _urandom=lambda vlen: b"0" * vlen)
        self.assertEqual(actual, expected, "mismatch hashing string")

    def test_make_hash_constant_string(self):
        """Test basic hashing of a fixed string to be constant for a particular
        random seed. I.e. the value may differ across interpreter invocations
        but remains constant in same interpreter.
        """
        first = make_hash(
            DUMMY_MODERN_PW, _urandom=lambda vlen: DUMMY_SALT[:vlen]
        )
        second = make_hash(
            DUMMY_MODERN_PW, _urandom=lambda vlen: DUMMY_SALT[:vlen]
        )
        self.assertEqual(first, second, "same seed hashing is not constant")

    def test_check_hash_reject_weak(self):
        """Test basic hash checking of a constant weak complexity password"""
        expected = DUMMY_WEAK_PW_PBKDF2
        result = check_hash(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_WEAK_PW,
            expected,
            strict_policy=True,
        )
        self.assertFalse(result, "check hash should fail on weak pw")

    def test_check_hash_reject_medium_without_legacy(self):
        """Test basic hash checking of a constant medium complexity password
        without legacy password support.
        """
        expected = DUMMY_MEDIUM_PW_PBKDF2
        result = check_hash(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_MEDIUM_PW,
            expected,
            strict_policy=True,
            allow_legacy=False,
        )
        self.assertFalse(result, "check hash strict should fail on medium pw")

    def test_check_hash_accept_medium_with_legacy(self):
        """Test basic hash checking of a constant medium complexity password
        with legacy password support.
        """
        expected = DUMMY_MEDIUM_PW_PBKDF2
        result = check_hash(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_MEDIUM_PW,
            expected,
            strict_policy=True,
            allow_legacy=True,
        )
        self.assertTrue(result, "check hash with legacy must accept medium pw")

    def test_check_hash_accept_high(self):
        """Test basic hash checking of a constant high complexity password
        without legacy password support.
        """
        expected = DUMMY_HIGH_PW_PBKDF2
        self.dummy_conf.site_password_policy = POLICY_HIGH
        result = check_hash(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_HIGH_PW,
            expected,
            strict_policy=True,
            allow_legacy=False,
        )
        self.assertTrue(result, "check hash must accept high complexity pw")

    def test_check_hash_accept_modern(self):
        """Test basic hash checking of a constant modern complexity password
        without legacy password support.
        """
        expected = DUMMY_MODERN_PW_PBKDF2
        result = check_hash(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_MODERN_PW,
            expected,
            strict_policy=True,
            allow_legacy=False,
        )
        self.assertTrue(result, "check hash must accept modern complexity pw")

    def test_check_hash_fixed(self):
        """Test basic hash checking of a fixed string"""
        expected = DUMMY_MEDIUM_PW_PBKDF2
        result = check_hash(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_MEDIUM_PW,
            expected,
            strict_policy=True,
        )
        self.assertFalse(result, "check hash should reject medium pw")
        result = check_hash(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_MEDIUM_PW,
            expected,
            strict_policy=False,
            allow_legacy=True,
        )
        self.assertTrue(result, "check hash failed medium pw when not strict")
        expected = DUMMY_MODERN_PW_PBKDF2
        result = check_hash(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_MODERN_PW,
            expected,
            strict_policy=True,
        )
        self.assertTrue(result, "check hash failed modern pw")

    def test_check_hash_random(self):
        """Test basic hashing and hash checking of a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = make_hash(random_pw)
        result = check_hash(
            self.dummy_conf, DUMMY_SERVICE, DUMMY_USER, random_pw, expected
        )
        self.assertTrue(result, "mismatch in random hash and check")

    def test_make_hash_variation(self):
        """Test how hashing of a fixed string varies depending on random seed.
        I.e. the value likely remains constant in same interpreter but differs
        across interpreter invocations.
        """
        first = make_hash(
            DUMMY_MODERN_PW, _urandom=lambda vlen: DUMMY_SALT[:vlen]
        )
        second = make_hash(
            DUMMY_MODERN_PW, _urandom=lambda vlen: DUMMY_SALT[::-1][:vlen]
        )
        self.assertNotEqual(first, second, "varying seed hashing is constant")

    def test_check_hash_despite_variation(self):
        """Test that check_hash works independently of random seed variation.
        I.e. the hash value differs across interpreter invocations but testing
        the same password against each succeeds.
        """
        first = make_hash(
            DUMMY_MODERN_PW, _urandom=lambda vlen: DUMMY_SALT[:vlen]
        )
        second = make_hash(
            DUMMY_MODERN_PW, _urandom=lambda vlen: DUMMY_SALT[::-1][:vlen]
        )
        result = check_hash(
            self.dummy_conf, DUMMY_SERVICE, DUMMY_USER, DUMMY_MODERN_PW, first
        )
        self.assertTrue(result, "mismatch in 1st random password hash check")
        result = check_hash(
            self.dummy_conf, DUMMY_SERVICE, DUMMY_USER, DUMMY_MODERN_PW, second
        )
        self.assertTrue(result, "mismatch in 2nd random password hash check")

    def test_scramble_digest_fixed(self):
        """Test basic scramble of a fixed string to be constant"""
        expected = DUMMY_MODERN_DIGEST_SCRAMBLE
        actual = scramble_digest(DUMMY_SALT, DUMMY_MODERN_PW)
        self.assertEqual(actual, expected, "mismatch scramble digest string")

    def test_unscramble_digest_fixed(self):
        """Test basic unscramble of a fixed string to be constant"""
        expected = DUMMY_MODERN_PW
        actual = unscramble_digest(DUMMY_SALT, DUMMY_MODERN_DIGEST_SCRAMBLE)
        self.assertEqual(actual, expected, "mismatch unscramble digest string")

    def test_make_digest_fixed(self):
        """Test basic digest of a fixed string"""
        expected = DUMMY_MODERN_PW_DIGEST
        result = make_digest(
            DUMMY_REALM, DUMMY_USER, DUMMY_MODERN_PW, DUMMY_SALT
        )
        self.assertEqual(expected, result, "mismatch in fixed digest")

    def test_check_digest_fixed(self):
        """Test basic digest checking of a fixed string"""
        expected = DUMMY_MODERN_PW_DIGEST
        result = check_digest(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_REALM,
            DUMMY_USER,
            DUMMY_MODERN_PW,
            expected,
            DUMMY_SALT,
        )
        self.assertTrue(result, "mismatch in fixed digest check")

    def test_check_digest_random(self):
        """Test basic digest checking of a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        random_salt = base64.b16encode(os.urandom(16))
        expected = make_digest(DUMMY_REALM, DUMMY_USER, random_pw, random_salt)
        result = check_digest(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_REALM,
            DUMMY_USER,
            random_pw,
            expected,
            random_salt,
        )
        self.assertTrue(result, "mismatch in random digest check")

    def test_digest_constant_string(self):
        """Test basic digest of a fixed string to be constant for a particular
        random seed. I.e. the value may differ across interpreter invocations
        but remains constant in same interpreter.
        """
        first = make_digest(
            DUMMY_REALM, DUMMY_USER, DUMMY_MODERN_PW, DUMMY_SALT
        )
        second = make_digest(
            DUMMY_REALM, DUMMY_USER, DUMMY_MODERN_PW, DUMMY_SALT
        )
        self.assertEqual(first, second, "basic digest is not constant")

    def test_scramble_password_fixed(self):
        """Test basic scramble of a fixed string to be constant"""
        expected = DUMMY_MODERN_PW_SCRAMBLE
        actual = scramble_password(DUMMY_SALT, DUMMY_MODERN_PW)
        self.assertEqual(actual, expected, "mismatch scramble pw string")

    def test_unscramble_password_fixed(self):
        """Test basic unscramble of a fixed string to be constant"""
        expected = DUMMY_MODERN_PW
        actual = unscramble_password(DUMMY_SALT, DUMMY_MODERN_PW_SCRAMBLE)
        self.assertEqual(actual, expected, "mismatch unscramble pw string")

    def test_make_scramble_fixed(self):
        """Test basic scramble of a fixed string to be constant"""
        expected = DUMMY_MODERN_PW_SCRAMBLE
        actual = make_scramble(DUMMY_MODERN_PW, DUMMY_SALT)
        self.assertEqual(actual, expected, "mismatch make scramble string")

    def test_check_scramble_fixed(self):
        """Test basic scramble checking of a fixed string"""
        expected = DUMMY_MODERN_PW_SCRAMBLE
        result = check_scramble(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_MODERN_PW,
            expected,
            DUMMY_SALT,
        )
        self.assertTrue(result, "mismatch in fixed scramble check")

    def test_check_scramble_random(self):
        """Test basic scramble checking of a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        random_salt = base64.b16encode(os.urandom(16))
        expected = make_scramble(DUMMY_MODERN_PW, random_salt)
        result = check_scramble(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            DUMMY_MODERN_PW,
            expected,
            random_salt,
        )
        self.assertTrue(result, "mismatch in random scramble check")

    def test_scramble_constant_string(self):
        """Test basic scramble of a fixed string to be constant for a particular
        salt.
        """
        first = make_scramble(DUMMY_MODERN_PW, DUMMY_SALT)
        second = make_scramble(DUMMY_MODERN_PW, DUMMY_SALT)
        self.assertEqual(first, second, "basic scramble is not constant")

    def test_prepare_fernet_key(self):
        """Test basic fernet secret key preparation on a fixed string."""
        expected = DUMMY_FERNET_KEY
        result = prepare_fernet_key(self.dummy_conf)
        self.assertEqual(expected, result, "failed prepare fernet key")

    def test_fernet_encrypt_decrypt(self):
        """Test basic fernet password encrypt and decrypt on a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = fernet_encrypt_password(self.dummy_conf, random_pw)
        result = fernet_decrypt_password(self.dummy_conf, expected)
        self.assertEqual(random_pw, result, "failed fernet enc+dec")

    def test_prepare_aesgcm_key(self):
        """Test basic aesgcm secret key preparation on a fixed string."""
        expected = DUMMY_AESGCM_KEY
        result = prepare_aesgcm_key(self.dummy_conf)
        self.assertEqual(expected, result, "failed prepare aesgcm key")

    def test_aesgcm_encrypt_decrypt(self):
        """Test basic aesgcm password encrypt and decrypt on a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = aesgcm_encrypt_password(self.dummy_conf, random_pw)
        result = aesgcm_decrypt_password(self.dummy_conf, expected)
        self.assertEqual(random_pw, result, "failed aesgcm enc+dec")

    def test_prepare_aesgcm_static_iv_fixed(self):
        """Test basic aesgcm initialization vector preparation on a fixed
        entropy value.
        """
        expected = DUMMY_AESGCM_STATIC_IV
        result = prepare_aesgcm_iv(self.dummy_conf, iv_entropy=DUMMY_ENTROPY)
        self.assertEqual(expected, result, "failed prepare aesgcm static iv")

    def test_prepare_aesgcm_aad_fixed(self):
        """Test basic aesgcm additional auth data preparation on a fixed
        entropy and date value.
        """
        expected = DUMMY_AESGCM_AAD
        result = prepare_aesgcm_aad(
            self.dummy_conf,
            DUMMY_AESGCM_AAD_PREFIX,
            aad_stamp=DUMMY_FIXED_TIMESTAMP,
        )
        self.assertEqual(expected, result, "failed prepare aesgcm aad")

    def test_aesgcm_encrypt_static_iv_fixed(self):
        """Test basic aesgcm password encrypt on a fixed string with a fixed
        initialization vector and date helper.
        """
        expected = DUMMY_MODERN_PW_AESGCM_SIV_ENCRYPTED
        result = aesgcm_encrypt_password(
            self.dummy_conf,
            DUMMY_MODERN_PW,
            init_vector=DUMMY_AESGCM_STATIC_IV,
            aad_stamp=DUMMY_FIXED_TIMESTAMP,
        )
        self.assertEqual(expected, result, "failed fixed aesgcm static iv enc")

    def test_aesgcm_decrypt_static_iv_fixed(self):
        """Test basic aesgcm password decrypt on a fixed string with a fixed
        initialization vector.
        """
        expected = DUMMY_MODERN_PW
        result = aesgcm_decrypt_password(
            self.dummy_conf,
            DUMMY_MODERN_PW_AESGCM_SIV_ENCRYPTED,
            init_vector=DUMMY_AESGCM_STATIC_IV,
        )
        self.assertEqual(expected, result, "failed fixed aesgcm static iv den")

    def test_aesgcm_encrypt_decrypt_static_iv(self):
        """Test basic aesgcm password encrypt and decrypt on a random string
        with a fixed initialization vector.
        """
        random_pw = generate_random_password(self.dummy_conf)
        entropy = make_safe_hash(random_pw, False)
        static_iv = prepare_aesgcm_iv(self.dummy_conf, iv_entropy=entropy)
        expected = aesgcm_encrypt_password(
            self.dummy_conf, random_pw, init_vector=static_iv
        )
        result = aesgcm_decrypt_password(
            self.dummy_conf, expected, init_vector=static_iv
        )
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
        encrypted = make_encrypt(self.dummy_conf, random_pw, algo="fernet")
        result = check_encrypt(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            random_pw,
            encrypted,
            algo="fernet",
        )
        self.assertFalse(result, "invalid match in fernet encrypt check")
        encrypted = make_encrypt(self.dummy_conf, random_pw, algo="aesgcm")
        result = check_encrypt(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            random_pw,
            encrypted,
            algo="aesgcm",
        )
        self.assertFalse(result, "invalid match in aesgcm encrypt check")
        encrypted = make_encrypt(
            self.dummy_conf, random_pw, algo="aesgcm_static"
        )
        result = check_encrypt(
            self.dummy_conf,
            DUMMY_SERVICE,
            DUMMY_USER,
            random_pw,
            encrypted,
            algo="aesgcm_static",
        )
        self.assertTrue(result, "mismatch in aesgcm_static encrypt check")

    def test_assure_reset_supported(self):
        """Test basic password reset token check for a fixed user and auth"""
        dummy_user = {"distinguished_name": DUMMY_USER}
        dummy_user["password_hash"] = DUMMY_MODERN_PW_PBKDF2
        result = assure_reset_supported(
            self.dummy_conf, dummy_user, DUMMY_SERVICE
        )
        self.assertTrue(result, "failed assure reset supported")

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires constant random seed")
    def test_generate_reset_token_fixed(self):
        """Test basic password reset token generate for a fixed string"""
        dummy_user = {"distinguished_name": DUMMY_USER}
        dummy_user["password_hash"] = DUMMY_MODERN_PW_PBKDF2
        timestamp = 42
        expected = DUMMY_MODERN_PW_RESET_TOKEN
        result = generate_reset_token(
            self.dummy_conf, dummy_user, DUMMY_SERVICE, timestamp
        )
        self.assertEqual(
            expected, result, "failed generate password reset token"
        )

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires constant random seed")
    def test_parse_reset_token_fixed(self):
        """Test basic password reset token parse for a fixed string"""
        timestamp = 42
        result = parse_reset_token(
            self.dummy_conf, DUMMY_MODERN_PW_RESET_TOKEN, DUMMY_SERVICE
        )
        self.assertEqual(result[0], timestamp, "failed parse token time")
        self.assertEqual(
            result[1], DUMMY_MODERN_PW_PBKDF2, "failed parse token hash"
        )

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires constant random seed")
    def test_verify_reset_token_fixed(self):
        """Test basic password reset token verify for a fixed string"""
        dummy_user = {"distinguished_name": DUMMY_USER}
        dummy_user["password_hash"] = DUMMY_MODERN_PW_PBKDF2
        timestamp = 42
        result = verify_reset_token(
            self.dummy_conf,
            dummy_user,
            DUMMY_MODERN_PW_RESET_TOKEN,
            DUMMY_SERVICE,
            timestamp,
        )
        self.assertTrue(result, "failed password reset token handling")

    def test_password_reset_token_generate_and_verify(self):
        """Test basic password reset token generate and verify helper"""
        random_pw = generate_random_password(self.dummy_conf)
        hashed_pw = make_hash(random_pw)
        dummy_user = {"distinguished_name": DUMMY_USER}
        dummy_user["password_hash"] = hashed_pw
        timestamp = 42
        expected = generate_reset_token(
            self.dummy_conf, dummy_user, DUMMY_SERVICE, timestamp
        )
        parsed = parse_reset_token(self.dummy_conf, expected, DUMMY_SERVICE)
        self.assertEqual(parsed[0], timestamp, "failed parse token time")
        self.assertEqual(parsed[1], hashed_pw, "failed parse token hash")
        result = verify_reset_token(
            self.dummy_conf, dummy_user, expected, DUMMY_SERVICE, timestamp
        )
        self.assertTrue(result, "failed password reset token handling")

    def test_password_reset_token_verify_expired(self):
        """Test basic password reset token verify failure after it expired"""
        random_pw = generate_random_password(self.dummy_conf)
        hashed_pw = make_hash(random_pw)
        dummy_user = {"distinguished_name": DUMMY_USER}
        dummy_user["password_hash"] = hashed_pw
        timestamp = 42
        expected = generate_reset_token(
            self.dummy_conf, dummy_user, DUMMY_SERVICE, timestamp
        )
        parsed = parse_reset_token(self.dummy_conf, expected, DUMMY_SERVICE)
        self.assertEqual(parsed[0], timestamp, "failed parse token time")
        self.assertEqual(parsed[1], hashed_pw, "failed parse token hash")
        timestamp = 4242
        result = verify_reset_token(
            self.dummy_conf, dummy_user, expected, DUMMY_SERVICE, timestamp
        )
        self.assertFalse(result, "failed password reset token expiry check")

    def test_make_csrf_token_fixed(self):
        """Test basic csrf token generate for a fixed method, operation and
        client id.
        """
        expected = DUMMY_CSRF_TOKEN
        result = make_csrf_token(
            self.dummy_conf, DUMMY_METHOD, DUMMY_OPERATION, DUMMY_ID
        )
        self.assertEqual(expected, result, "failed make csrf token")

    def test_make_csrf_trust_token_fixed(self):
        """Test basic csrf trust token generate for a fixed method, operation,
        client id and args.
        """
        expected = DUMMY_CSRF_TRUST_TOKEN
        result = make_csrf_trust_token(
            self.dummy_conf,
            DUMMY_METHOD,
            DUMMY_OPERATION,
            DUMMY_ARGS,
            DUMMY_ID,
        )
        self.assertEqual(expected, result, "failed make csrf trust token")

    def test_generate_random_password(self):
        """Test basic generate password"""
        result = generate_random_password(self.dummy_conf)
        self.assertTrue(result, "failed generate password")
        self.assertTrue(len(result) == 12, "failed generate password length")

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires constant random seed")
    def test_generate_random_password_fixed_seed(self):
        """Test basic generate password is constant with fixed random seed"""
        expected = DUMMY_GENERATED_PW
        result = generate_random_password(self.dummy_conf)
        self.assertEqual(
            expected, result, "failed generate password with fixed seed"
        )

    # TODO: migrate remaining inline checks from module here instead
    def test_existing_main(self):
        def raise_on_error_exit(exit_code):
            if exit_code != 0:
                if raise_on_error_exit.last_print is not None:
                    identifying_message = raise_on_error_exit.last_print
                else:
                    identifying_message = "unknown"
                raise AssertionError(
                    "failure in unittest/testcore: %s" % (identifying_message,)
                )

        raise_on_error_exit.last_print = None

        def record_last_print(value):
            raise_on_error_exit.last_print = value

        pwcrypto_main(_exit=raise_on_error_exit, _print=record_last_print)


if __name__ == "__main__":
    testmain()
