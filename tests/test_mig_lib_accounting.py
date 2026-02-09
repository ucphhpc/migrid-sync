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

from mig.lib.accounting import get_usage, human_readable_filesize, \
    update_accounting
from mig.shared.base import client_id_dir
from mig.shared.defaults import peers_filename
from tests.support import MigTestCase, ensure_dirs_exist

TEST_MTIME = 1768925307
TEST_SOFTLIMIT_BYTES = 109951162777600
TEST_HARDLIMIT_BYTES = 109951162777600
TEST_CLIENT_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@user.com'
TEST_CLIENT_BYTES = 206128256
TEST_EXT_DN = '/C=DK/ST=NA/L=NA/O=PEER Org/OU=NA/CN=Test Peer/emailAddress=peer@example.com'
TEST_EXT_BYTES = 16806128256
TEST_FREEZE_BYTES = 128256
TEST_VGRID_NAME1 = 'TestVgrid1'
TEST_VGRID_BYTES1 = 406128256
TEST_VGRID_NAME2 = 'TestVgrid2'
TEST_VGRID_BYTES2 = 606128256
TEST_VGRID_NAME3 = 'TestVgrid3'
TEST_VGRID_BYTES3 = 806128256
TEST_VGRID_TOTAL_BYTES = TEST_VGRID_BYTES1 \
    + TEST_VGRID_BYTES2 \
    + TEST_VGRID_BYTES3
TEST_TOTAL_BYTES = TEST_CLIENT_BYTES \
    + TEST_EXT_BYTES \
    + TEST_FREEZE_BYTES \
    + TEST_VGRID_TOTAL_BYTES
TEST_LUSTRE_QUOTA_INFO = {'next_pid': 192, 'mtime': TEST_MTIME}
TEST_CLIENT_USAGE = {'lustre_pid': 42,
                     'files': 11,
                     'bytes': TEST_CLIENT_BYTES,
                     'softlimit_bytes': TEST_SOFTLIMIT_BYTES,
                     'hardlimit_bytes': TEST_HARDLIMIT_BYTES,
                     'mtime': TEST_MTIME}
TEST_VGRID_USAGE1 = {'lustre_pid': 43,
                     'files': 111,
                     'bytes': TEST_VGRID_BYTES1,
                     'softlimit_bytes': TEST_SOFTLIMIT_BYTES,
                     'hardlimit_bytes': TEST_HARDLIMIT_BYTES,
                     'mtime': TEST_MTIME}
TEST_VGRID_USAGE2 = {'lustre_pid': 44,
                     'files': 222,
                     'bytes': TEST_VGRID_BYTES2,
                     'softlimit_bytes': TEST_SOFTLIMIT_BYTES,
                     'hardlimit_bytes': TEST_HARDLIMIT_BYTES,
                     'mtime': TEST_MTIME}
TEST_VGRID_USAGE3 = {'lustre_pid': 45,
                     'files': 333,
                     'bytes': TEST_VGRID_BYTES3,
                     'softlimit_bytes': TEST_SOFTLIMIT_BYTES,
                     'hardlimit_bytes': TEST_HARDLIMIT_BYTES,
                     'mtime': TEST_MTIME}
TEST_EXT_USAGE = {'lustre_pid': 46,
                  'files': 1,
                  'bytes': TEST_EXT_BYTES,
                  'softlimit_bytes': TEST_SOFTLIMIT_BYTES,
                  'hardlimit_bytes': TEST_HARDLIMIT_BYTES,
                  'mtime': TEST_MTIME}
TEST_FREEZE_USAGE = {'lustre_pid': 47,
                     'files': 1,
                     'bytes': TEST_FREEZE_BYTES,
                     'softlimit_bytes': TEST_SOFTLIMIT_BYTES,
                     'hardlimit_bytes': TEST_HARDLIMIT_BYTES,
                     'mtime': TEST_MTIME}
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


class MigLibAccounting(MigTestCase):
    """Unit tests for accounting related helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test"""

        # Create fake fs layout matching real systems

        self.configuration.site_enable_quota = True
        self.configuration.site_enable_accounting = True
        self.configuration.quota_backend = 'lustre'

        quota_basepath = os.path.join(self.configuration.quota_home,
                                      self.configuration.quota_backend)
        quota_user_path = os.path.join(quota_basepath, 'user')
        quota_vgrid_path = os.path.join(quota_basepath, 'vgrid')
        quota_freeze_path = os.path.join(quota_basepath, 'freeze')
        test_client_peers_path = os.path.join(self.configuration.user_settings,
                                              client_id_dir(TEST_CLIENT_DN))

        ensure_dirs_exist(self.configuration.vgrid_home)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.accounting_home)
        ensure_dirs_exist(self.configuration.quota_home)
        ensure_dirs_exist(quota_user_path)
        ensure_dirs_exist(quota_vgrid_path)
        ensure_dirs_exist(quota_freeze_path)
        ensure_dirs_exist(test_client_peers_path)

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

        test_lustre_quota_info_filepath \
            = os.path.join(self.configuration.quota_home,
                           '%s.pck' % self.configuration.quota_backend)
        with open(test_lustre_quota_info_filepath, 'wb') as fh:
            fh.write(pickle.dumps(TEST_LUSTRE_QUOTA_INFO))

        quota_test_client_path \
            = os.path.join(quota_user_path,
                           "%s.pck" % client_id_dir(TEST_CLIENT_DN))

        with open(quota_test_client_path, 'wb') as fh:
            fh.write(pickle.dumps(TEST_CLIENT_USAGE))

        quot_test_vgrid_filepath1 = os.path.join(quota_vgrid_path,
                                                 "%s.pck" % TEST_VGRID_NAME1)
        with open(quot_test_vgrid_filepath1, 'wb') as fh:
            fh.write(pickle.dumps(TEST_VGRID_USAGE1))

        quot_test_vgrid_filepath2 = os.path.join(quota_vgrid_path,
                                                 "%s.pck" % TEST_VGRID_NAME2)
        with open(quot_test_vgrid_filepath2, 'wb') as fh:
            fh.write(pickle.dumps(TEST_VGRID_USAGE2))

        quot_test_vgrid_filepath3 = os.path.join(quota_vgrid_path,
                                                 "%s.pck" % TEST_VGRID_NAME3)
        with open(quot_test_vgrid_filepath3, 'wb') as fh:
            fh.write(pickle.dumps(TEST_VGRID_USAGE3))

        test_client_peers_filepath = os.path.join(
            test_client_peers_path, peers_filename)
        with open(test_client_peers_filepath, 'wb') as fh:
            fh.write(pickle.dumps(TEST_PEERS))

        quota_test_client_ext_path \
            = os.path.join(quota_user_path,
                           "%s.pck" % client_id_dir(TEST_EXT_DN))
        with open(quota_test_client_ext_path, 'wb') as fh:
            fh.write(pickle.dumps(TEST_EXT_USAGE))

        quota_test_freeze_path = os.path.join(quota_freeze_path,
                                              "%s.pck"
                                              % client_id_dir(TEST_CLIENT_DN))
        with open(quota_test_freeze_path, 'wb') as fh:
            fh.write(pickle.dumps(TEST_FREEZE_USAGE))

    def test_accounting(self):
        """Test accounting update and usage"""

        # Update accounting information based on quote

        retval = update_accounting(self.configuration)
        self.assertTrue(retval)

        # Check updated accounting data

        usage = get_usage(self.configuration)
        self.assertNotEqual(usage, {})

        accounting = usage.get('accounting', {})
        test_user_accounting = accounting.get(TEST_CLIENT_DN, {})
        self.assertNotEqual(test_user_accounting, {})

        home_total = test_user_accounting.get('home_total', 0)
        self.assertEqual(home_total, TEST_CLIENT_BYTES)

        vgrid_total = test_user_accounting.get('vgrid_total', 0)
        self.assertEqual(vgrid_total, TEST_VGRID_TOTAL_BYTES)

        ext_users_total = test_user_accounting.get('ext_users_total', 0)
        self.assertEqual(ext_users_total, TEST_EXT_BYTES)

        freeze_total = test_user_accounting.get('freeze_total', 0)
        self.assertEqual(freeze_total, TEST_FREEZE_BYTES)

        total_bytes = test_user_accounting.get('total_bytes', 0)
        self.assertEqual(total_bytes, TEST_TOTAL_BYTES)

    def test_human_readable_filesize_valid(self):
        """Test human-friendly format helper success on valid byte sizes"""
        valid = [(0, "0 B"), (42, "42.000 B"), (2**10, "1.000 KiB"),
                 (2**30, "1.000 GiB"), (2**50, "1.000 PiB"),
                 (2**89, "512.000 YiB"), (2**90 - 2**70, "1023.999 YiB")]
        for (size, expect) in valid:
            self.assertEqual(human_readable_filesize(size), expect)

    def test_human_readable_filesize_invalid(self):
        """Test human-friendly format helper failure on invalid byte sizes"""
        invalid = [(i, "NaN") for i in [False, None, "", "one", -1, 1.2, 2**90,
                                        2**128]]
        for (size, expect) in invalid:
            self.assertEqual(human_readable_filesize(size), expect)
