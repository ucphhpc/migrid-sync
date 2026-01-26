# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_accounting - unit test of the corresponding mig lib module
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Unit tests for the migrid module pointed to in the filename"""

import os
import pickle

from mig.lib.accounting import update_accounting, get_usage
from mig.shared.base import client_id_dir
from mig.shared.defaults import peers_filename
from tests.support import MigTestCase, ensure_dirs_exist


class MigLibAccounting(MigTestCase):
    """Unit tests for quota related helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test"""

        # Define fake quota

        TEST_LUSTRE_QUOTA_INFO = {'next_pid': 192, 'mtime': 1768925307}

        TEST_CLIENT_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@user.com'
        TEST_VGRID_NAME1 = 'TestVgrid1'
        TEST_VGRID_NAME2 = 'TestVgrid2'
        TEST_VGRID_NAME3 = 'TestVgrid3'
        TEST_EXT_DN = '/C=DK/ST=NA/L=NA/O=PEER Org/OU=NA/CN=Test Peer/emailAddress=peer@example.com'

        TEST_CLIENT_USAGE = {'lustre_pid': 42,
                             'files': 11,
                             'bytes': 206128256,
                             'softlimit_bytes': 109951162777600,
                             'hardlimit_bytes': 109951162777600,
                             'mtime': 1768925307}

        TEST_VGRID_USAGE1 = {'lustre_pid': 43,
                             'files': 111,
                             'bytes': 406128256,
                             'softlimit_bytes': 109951162777600,
                             'hardlimit_bytes': 109951162777600,
                             'mtime': 1768925307}

        TEST_VGRID_USAGE2 = {'lustre_pid': 44,
                             'files': 222,
                             'bytes': 606128256,
                             'softlimit_bytes': 109951162777600,
                             'hardlimit_bytes': 109951162777600,
                             'mtime': 1768925307}

        TEST_VGRID_USAGE3 = {'lustre_pid': 45,
                             'files': 333,
                             'bytes': 806128256,
                             'softlimit_bytes': 109951162777600,
                             'hardlimit_bytes': 109951162777600,
                             'mtime': 1768925307}

        TEST_EXT_USAGE = {'lustre_pid': 46,
                          'files': 1,
                          'bytes': 16806128256,
                          'softlimit_bytes': 109951162777600,
                          'hardlimit_bytes': 109951162777600,
                          'mtime': 1768925307}

        TEST_FREEZE_USAGE = {'lustre_pid': 47,
                             'files': 1,
                             'bytes': 128256,
                             'softlimit_bytes': 109951162777600,
                             'hardlimit_bytes': 109951162777600,
                             'mtime': 1768925307}

        TEST_PEERS = {TEST_EXT_DN: {'kind': 'collaboration',
                                    'distinguished_name': TEST_EXT_DN,
                                    'country': 'DK',
                                    'label': 'TEST',
                                    'state': '',
                                    'expire': '2222-12-31',
                                    'full_name': 'Test Peer',
                                    'organization': 'PEER Org',
                                    'email': 'peer@example.com'
                                    }}

        # Create fake fs layout matching real systems

        self.configuration.site_enable_quota = True
        self.configuration.site_enable_accounting = True
        self.configuration.quota_backend = 'lustre'

        QUOTA_BASEPATH = os.path.join(self.configuration.quota_home,
                                      self.configuration.quota_backend)
        QUOTA_USER_PATH = os.path.join(QUOTA_BASEPATH, 'user')
        QUOTA_VGRID_PATH = os.path.join(QUOTA_BASEPATH, 'vgrid')
        QUOTA_FREEZE_PATH = os.path.join(QUOTA_BASEPATH, 'freeze')
        TEST_CLIENT_PEERS_PATH = os.path.join(self.configuration.user_settings,
                                              client_id_dir(TEST_CLIENT_DN))
        ensure_dirs_exist(self.configuration.vgrid_home)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.accounting_home)
        ensure_dirs_exist(self.configuration.quota_home)
        ensure_dirs_exist(QUOTA_USER_PATH)
        ensure_dirs_exist(QUOTA_VGRID_PATH)
        ensure_dirs_exist(QUOTA_FREEZE_PATH)
        ensure_dirs_exist(TEST_CLIENT_PEERS_PATH)

        # Ensure fake vgrid and write owner

        for vgrid_name in [TEST_VGRID_NAME1,
                           TEST_VGRID_NAME2,
                           TEST_VGRID_NAME3]:
            vgrid_home_path = os.path.join(
                self.configuration.vgrid_home, vgrid_name)
            ensure_dirs_exist(vgrid_home_path)
            vgrid_owners_filepath = os.path.join(vgrid_home_path, 'owners')
            with open(vgrid_owners_filepath, 'wb') as fh:
                fh.write(pickle.dumps([TEST_CLIENT_DN]))

        # Write fake quota

        TEST_LUSTRE_QUOTA_INFO_FILEPATH \
            = os.path.join(self.configuration.quota_home,
                           '%s.pck' % self.configuration.quota_backend)
        with open(TEST_LUSTRE_QUOTA_INFO_FILEPATH, 'wb') as fh:
            fh.write(pickle.dumps(TEST_LUSTRE_QUOTA_INFO))

        QUOTA_TEST_CLIENT_PATH \
            = os.path.join(QUOTA_USER_PATH,
                           "%s.pck" % client_id_dir(TEST_CLIENT_DN))

        with open(QUOTA_TEST_CLIENT_PATH, 'wb') as fh:
            fh.write(pickle.dumps(TEST_CLIENT_USAGE))

        QUOTA_TEST_VGRID_FILEPATH1 = os.path.join(QUOTA_VGRID_PATH,
                                                  "%s.pck" % TEST_VGRID_NAME1)
        with open(QUOTA_TEST_VGRID_FILEPATH1, 'wb') as fh:
            fh.write(pickle.dumps(TEST_VGRID_USAGE1))

        QUOTA_TEST_VGRID_FILEPATH2 = os.path.join(QUOTA_VGRID_PATH,
                                                  "%s.pck" % TEST_VGRID_NAME2)
        with open(QUOTA_TEST_VGRID_FILEPATH2, 'wb') as fh:
            fh.write(pickle.dumps(TEST_VGRID_USAGE2))

        QUOTA_TEST_VGRID_FILEPATH3 = os.path.join(QUOTA_VGRID_PATH,
                                                  "%s.pck" % TEST_VGRID_NAME3)
        with open(QUOTA_TEST_VGRID_FILEPATH3, 'wb') as fh:
            fh.write(pickle.dumps(TEST_VGRID_USAGE3))

        TEST_CLIENT_PEERS_FILEPATH = os.path.join(
            TEST_CLIENT_PEERS_PATH, peers_filename)
        with open(TEST_CLIENT_PEERS_FILEPATH, 'wb') as fh:
            fh.write(pickle.dumps(TEST_PEERS))

        QUOTA_TEST_CLIENT_EXT_PATH \
            = os.path.join(QUOTA_USER_PATH,
                           "%s.pck" % client_id_dir(TEST_EXT_DN))
        with open(QUOTA_TEST_CLIENT_EXT_PATH, 'wb') as fh:
            fh.write(pickle.dumps(TEST_EXT_USAGE))

        QUOTA_TEST_FREEZE_PATH = os.path.join(QUOTA_FREEZE_PATH,
                                              "%s.pck"
                                              % client_id_dir(TEST_CLIENT_DN))
        with open(QUOTA_TEST_FREEZE_PATH, 'wb') as fh:
            fh.write(pickle.dumps(TEST_FREEZE_USAGE))

    def test_accounting(self):
        """Test accounting update and usage"""
        # Create accounting
        retval = update_accounting(self.configuration)
        self.assertTrue(retval)

        # Check accounting

        usage = get_usage(self.configuration)
        self.assertNotEqual(usage, {})

        accounting = usage.get('accounting', {})
        test_user_accounting = accounting.get(
            '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@user.com', {})
        self.assertNotEqual(test_user_accounting, {})

        home_total = test_user_accounting.get('home_total', 0)
        self.assertEqual(home_total, 206128256)

        vgrid_total = test_user_accounting.get('vgrid_total', 0)
        self.assertEqual(vgrid_total, 1818384768)

        ext_users_total = test_user_accounting.get('ext_users_total', 0)
        self.assertEqual(ext_users_total, 16806128256)

        freeze_total = test_user_accounting.get('freeze_total', 0)
        self.assertEqual(freeze_total, 128256)

        total_bytes = test_user_accounting.get('total_bytes', 0)
        self.assertEqual(total_bytes, 18830769536)
