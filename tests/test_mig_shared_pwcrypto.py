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
DUMMY_WEAK_PW_PBKDF2 = \
    "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$epib2rEg/HYTQZFnCp7hmIGZ6rzHnViy"
DUMMY_HOME_DIR = 'dummy_user_home'
DUMMY_SETTINGS_DIR = 'dummy_user_settings'
DUMMY_SERVICE = 'dummy-svc'
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
        first = make_hash(
            DUMMY_WEAK_PW, _urandom=lambda vlen: DUMMY_SALT[:vlen])
        second = make_hash(
            DUMMY_WEAK_PW, _urandom=lambda vlen: DUMMY_SALT[:vlen])
        self.assertEqual(first, second, "hashing is not constant")

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

    def test_check_hash_constant(self):
        """Test basic hash checking of a constant string"""
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

    def test_check_digest(self):
        """Test basic digest checking of a random string"""
        random_pw = generate_random_password(self.dummy_conf)
        expected = make_digest(DUMMY_REALM, DUMMY_USER,
                               DUMMY_MODERN_PW, DUMMY_SALT)
        result = check_digest(self.dummy_conf, DUMMY_SERVICE, DUMMY_REALM,
                              DUMMY_USER, DUMMY_MODERN_PW, expected,
                              DUMMY_SALT)
        self.assertTrue(result, "mismatch in digest check")

   # TODO: migrate inline checks from module here instead


if __name__ == '__main__':
    testmain()
