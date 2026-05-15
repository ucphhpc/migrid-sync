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
        valid = [(0, "0 B"), (1, "1.000 B"), (42, "42.000 B"),
                 (2**10, "1.000 KiB"), (2**30, "1.000 GiB"),
                 (2**50, "1.000 PiB"), (2**89, "512.000 YiB"),
                 (2**90 - 2**70, "1023.999 YiB")]
        for (size, expect) in valid:
            self.assertEqual(human_readable_filesize(size), expect)

    def test_human_readable_filesize_invalid(self):
        """Test human-friendly format helper failure on invalid byte sizes"""
        invalid = [(i, "NaN") for i in [False, None, "", "one", -1, 1.2, 2**90,
                                        2**128]]
        for (size, expect) in invalid:
            self.assertEqual(human_readable_filesize(size), expect)

    def test_human_readable_filesize_decimals(self):
        """Test human-friendly format helper with custom decimal count"""
        cases = [(2**10, 0, "1 KiB"),
                 (2**10, 1, "1.0 KiB"),
                 (2**10, 2, "1.00 KiB"),
                 (2**10, 5, "1.00000 KiB")]
        for (size, decimals, expect) in cases:
            self.assertEqual(human_readable_filesize(size, decimals=decimals),
                             expect)

    def test_human_readable_filesize_si_format(self):
        """Test human-friendly format helper with SI byte units (powers of 1000)"""
        # SI exponent is still determined by log2, so values are based on 2**N
        valid = [(0, "0 B"), (42, "42.000 B"), (2**10, "1.024 KB"),
                 (2**20, "1.049 MB"), (2**30, "1.074 GB"), (2**50, "1.126 PB")]
        for (size, expect) in valid:
            self.assertEqual(
                human_readable_filesize(size, si_byte_format=True), expect)
        # decimals and si_byte_format compose correctly
        self.assertEqual(
            human_readable_filesize(2**10, decimals=1, si_byte_format=True),
            "1.0 KB")

    def test_get_usage_decimals(self):
        """Test get_usage passes decimals parameter through to report strings"""
        retval = update_accounting(self.configuration)
        self.assertTrue(retval)

        usage = get_usage(self.configuration, decimals=0)
        self.assertIsNotNone(usage)
        accounting = usage.get('accounting', {})
        test_user_accounting = accounting.get(TEST_CLIENT_DN, {})
        self.assertNotEqual(test_user_accounting, {})

        # Raw byte counts are unaffected by decimals
        self.assertEqual(test_user_accounting.get('total_bytes', 0),
                         TEST_TOTAL_BYTES)

        # total_report should use 0 decimal places
        total_report = test_user_accounting.get('total_report', '')
        expected_size = human_readable_filesize(TEST_TOTAL_BYTES, decimals=0)
        self.assertEqual(total_report, "Total usage: %s" % expected_size)

    def test_get_usage_si_format(self):
        """Test get_usage appends SI units alongside binary units in reports"""
        retval = update_accounting(self.configuration)
        self.assertTrue(retval)

        usage = get_usage(self.configuration, si_byte_format=True)
        self.assertIsNotNone(usage)
        accounting = usage.get('accounting', {})
        test_user_accounting = accounting.get(TEST_CLIENT_DN, {})
        self.assertNotEqual(test_user_accounting, {})

        # Raw byte counts are unaffected by si_byte_format
        self.assertEqual(test_user_accounting.get('total_bytes', 0),
                         TEST_TOTAL_BYTES)

        # All reports should include both binary and SI units separated by " / "
        for key in ('total_report', 'home_report', 'vgrid_report',
                    'freeze_report'):
            self.assertIn(' / ', test_user_accounting.get(key, ''),
                          msg="%r missing SI separator" % key)

    def test_get_usage_ext_users_report_format(self):
        """Test get_usage ext_users_report shows parsed name/email/org/country"""
        retval = update_accounting(self.configuration)
        self.assertTrue(retval)

        usage = get_usage(self.configuration)
        self.assertIsNotNone(usage)
        accounting = usage.get('accounting', {})
        test_user_accounting = accounting.get(TEST_CLIENT_DN, {})
        self.assertNotEqual(test_user_accounting, {})

        ext_users_report = test_user_accounting.get('ext_users_report', '')
        self.assertNotEqual(ext_users_report, '')
        # Report should show parsed user fields, not just the raw DN
        self.assertIn('Test Peer', ext_users_report)
        self.assertIn('peer@example.com', ext_users_report)
        self.assertIn('PEER Org', ext_users_report)
        self.assertIn('DK', ext_users_report)

    def test_get_usage_without_accounting_data(self):
        """Test get_usage returns None when no accounting data exists"""
        # Do not call update_accounting — no 'latest' file should exist.
        # The expected file-not-found errors are intentional here.
        self._logger.forgive_errors()
        usage = get_usage(self.configuration)
        self.assertIsNone(usage)

    def test_get_usage_empty_userlist_returns_all_users(self):
        """Test that an empty userlist returns all accounts including ext users"""
        retval = update_accounting(self.configuration)
        self.assertTrue(retval)

        usage_all = get_usage(self.configuration)
        accounting_all = usage_all.get('accounting', {})
        self.assertIn(TEST_CLIENT_DN, accounting_all)
        self.assertIn(TEST_EXT_DN, accounting_all)

    def test_get_usage_targeted_userlist_excludes_ext_user(self):
        """Test that a targeted userlist suppresses unrequested ext users"""
        retval = update_accounting(self.configuration)
        self.assertTrue(retval)

        usage_targeted = get_usage(self.configuration,
                                   userlist=[TEST_CLIENT_DN])
        accounting_targeted = usage_targeted.get('accounting', {})
        self.assertIn(TEST_CLIENT_DN, accounting_targeted)
        self.assertNotIn(TEST_EXT_DN, accounting_targeted)

    def test_get_usage_userlist_exposes_ext_user(self):
        """Test that explicitly listing an ext user in userlist includes them"""
        retval = update_accounting(self.configuration)
        self.assertTrue(retval)

        # Requesting TEST_CLIENT_DN alone suppresses the ext user.
        usage_targeted = get_usage(self.configuration,
                                   userlist=[TEST_CLIENT_DN])
        self.assertNotIn(TEST_EXT_DN,
                         usage_targeted.get('accounting', {}))

        # Explicitly requesting TEST_EXT_DN must include them.
        usage_explicit = get_usage(self.configuration,
                                   userlist=[TEST_EXT_DN])
        self.assertIsNotNone(usage_explicit)
        self.assertIn(TEST_EXT_DN, usage_explicit.get('accounting', {}))

    def test_accounting_freeze_disabled(self):
        """Test that freeze quota is ignored when site_enable_freeze is False"""
        self.configuration.site_enable_freeze = False
        retval = update_accounting(self.configuration)
        self.assertTrue(retval)

        usage = get_usage(self.configuration)
        self.assertIsNotNone(usage)
        test_user_accounting = usage.get('accounting', {}).get(
            TEST_CLIENT_DN, {})
        self.assertNotEqual(test_user_accounting, {})

        # Freeze files exist on disk but must not contribute to the total
        self.assertEqual(test_user_accounting.get('freeze_total', 0), 0)
        expected_total = (TEST_CLIENT_BYTES + TEST_EXT_BYTES
                          + TEST_VGRID_TOTAL_BYTES)
        self.assertEqual(test_user_accounting.get('total_bytes', 0),
                         expected_total)
