# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_useradm - unit test of the corresponding mig shared module
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

from __future__ import print_function
import codecs
import os
import shutil
import sys
import unittest

from tests.support import MIG_BASE, TEST_OUTPUT_DIR, MigTestCase, testmain
from tests.support.picklesupp import PickleAssertMixin

from mig.shared.base import keyword_auto
from mig.shared.useradm import create_user, _USERADM_CONFIG_DIR_KEYS


class TestMigSharedUsedadm_create_user(MigTestCase, PickleAssertMixin):
    def before_each(self):
        configuration = self.configuration

        for config_key in _USERADM_CONFIG_DIR_KEYS:
            dir_path = getattr(configuration, config_key)[0:-1]
            try:
                shutil.rmtree(dir_path)
            except:
                pass

        self.expected_user_db_home = configuration.user_db_home[0:-1]
        self.expected_user_db_file = os.path.join(
            self.expected_user_db_home, 'MiG-users.db')

    def _provide_configuration(self):
        return 'testconfig'

    def test_user_db_is_created(self):
        user_dict = {}
        user_dict['full_name'] = "Test User"
        user_dict['organization'] = "Test Org"
        user_dict['state'] = "NA"
        user_dict['country'] = "DK"
        user_dict['email'] = "user@example.com"
        user_dict['comment'] = "This is the create comment"
        user_dict['password'] = "password"
        create_user(user_dict, self.configuration,
                    keyword_auto, default_renew=True)

        # presence of user home
        path_kind = MigTestCase._absolute_path_kind(self.expected_user_db_home)
        self.assertEqual(path_kind, 'dir')

        # presence of user db
        path_kind = MigTestCase._absolute_path_kind(self.expected_user_db_file)
        self.assertEqual(path_kind, 'file')

    def test_user_entry_is_recorded(self):
        def _generate_salt():
            return b'CCCC12344321CCCC'

        expected_user_id = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=user@example.com'
        expected_user_unique_id = 'OUejmKGMFWPWLyi5chqQalxDgltTuG1SoZUsqGyj32yY3275GjA2GfMo5odeWuKQ'
        expected_user_password_hash = "PBKDF2$sha256$10000$b'CCCC12344321CCCC'$b'bph8p/avUq42IYeOdJoJuUqrJ7Q32eaT'"

        user_dict = {}
        user_dict['full_name'] = "Test User"
        user_dict['organization'] = "Test Org"
        user_dict['state'] = "NA"
        user_dict['country'] = "DK"
        user_dict['email'] = "user@example.com"
        user_dict['comment'] = "This is the create comment"
        user_dict['password'] = "password"

        create_user(user_dict, self.configuration,
                    keyword_auto, default_renew=True)

        pickled = self.assertPickledFile(self.expected_user_db_file)
        # FIXME: Python3 pickle appears to be keyed by bytes
        picked_expected_user_id = expected_user_id.encode('utf8')
        self.assertIn(picked_expected_user_id, pickled)

        actual_user_object = pickled[picked_expected_user_id]

        # TODO: remove resetting the handful of keys here done because changes
        #       to make them assertion frienfly values will increase the size
        #       of the diff which, at time of commit, are best minimised.
        actual_user_object[b'created'] = 9999999999.9999999
        actual_user_object[b'unique_id'] = '__UNIQUE_ID__'

        self.assertEqual(actual_user_object, {
            b'full_name': b'Test User',
            b'organization': b'Test Org',
            b'state': b'NA',
            b'country': b'DK',
            b'email': b'user@example.com',
            b'comment': b'This is the create comment',
            b'password': b'password',
            b'distinguished_name': picked_expected_user_id,
            b'created': 9999999999.9999999,
            b'unique_id': '__UNIQUE_ID__',
            b'openid_names': [],
        })


if __name__ == '__main__':
    testmain()
