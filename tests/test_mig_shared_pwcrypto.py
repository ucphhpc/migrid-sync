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

import os
import sys

from tests.support import MigTestCase, FakeConfiguration, \
    cleanpath, temppath, testmain

from mig.shared.defaults import POLICY_NONE, POLICY_WEAK, POLICY_MEDIUM, \
    POLICY_HIGH, POLICY_MODERN, POLICY_CUSTOM, PASSWORD_POLICIES
from mig.shared.pwcrypto import *


DUMMY_USER = "dummy-user"
DUMMY_ID = "dummy-id"
DUMMY_PW = 'foobar'
DUMMY_PW_HASH = \
    "PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$epib2rEg/HYTQZFnCp7hmIGZ6rzHnViy"
DUMMY_HOME_DIR = 'dummy_user_home'
DUMMY_SETTINGS_DIR = 'dummy_user_settings'
DUMMY_SERVICE = 'svc'


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
            site_password_policy=POLICY_HIGH,
            site_password_legacy_policy=POLICY_MEDIUM,
            site_password_cracklib=False)

    def test_make_hash_constant_string(self):
        """Test basic hashing of a fixed string to be constant for a fixed
        random seed.
        """
        actual = make_hash(DUMMY_PW, _urandom=lambda vlen: b'0' * vlen)
        self.assertEqual(actual, DUMMY_PW_HASH, "mismatch hashing string")

    def test_check_hash(self):
        """Test basic hash checking of a fixed string"""

        random_pw = generate_random_password(self.dummy_conf)
        expected = make_hash(random_pw)
        result = check_hash(self.dummy_conf, DUMMY_SERVICE, DUMMY_USER,
                            random_pw, expected)

        self.assertTrue(result, "mismatch in hash check")


if __name__ == '__main__':
    testmain()
