# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_configuration - unit test of configuration
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

"""Unit tests for the configuration object"""

import inspect
import os
import unittest

from tests.support import MigTestCase, TEST_DATA_DIR, PY2, testmain, \
    fixturefile
from mig.shared.configuration import Configuration


def _is_method(value):
    return type(value).__name__ == 'method'


def _to_dict(obj):
    return {k: v for k, v in inspect.getmembers(obj)
            if not (k.startswith('__') or _is_method(v))}


class MigSharedConfiguration(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def test_argument_storage_protocols(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised.conf')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        # TODO: add a test to cover filtering of a mix of valid+invalid protos
        # self.assertEqual(configuration.storage_protocols, ['xxx', 'yyy', 'zzz'])
        # TODO: why does even our explicit testdata value 'sftp' yield [] here?
        # self.assertEqual(configuration.storage_protocols, ['sftp'])
        self.assertEqual(configuration.storage_protocols, [])

    def test_argument_wwwserve_max_bytes(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised.conf')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.wwwserve_max_bytes, 43211234)

    def test_argument_include_sections(self):
        """Test that include_sections path default is set"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised.conf')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections,
                         '/home/mig/mig/server/MiGserver.d')

    def test_argument_custom_include_sections(self):
        """Test that include_sections path override is correctly applied"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')

        self.assertTrue(os.path.isdir(test_conf_section_dir))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections,
                         test_conf_section_dir)

    def test_argument_include_sections_quota(self):
        """Test that QUOTA conf section overrides are correctly applied"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'quota.conf')

        self.assertTrue(os.path.isfile(test_conf_section_file))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertEqual(configuration.quota_backend, 'dummy')
        self.assertEqual(configuration.quota_user_limit, 4242)
        self.assertEqual(configuration.quota_vgrid_limit, 4242424242)

    def test_argument_include_sections_cloud_misty(self):
        """Test that CLOUD_MISTY conf section is correctly applied"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'cloud_misty.conf')

        self.assertTrue(os.path.isfile(test_conf_section_file))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertIsInstance(configuration.cloud_services, list)
        self.assertTrue(configuration.cloud_services)
        self.assertIsInstance(configuration.cloud_services[0], dict)
        self.assertTrue(configuration.cloud_services[0].get('service_name',
                                                            False))
        self.assertEqual(configuration.cloud_services[0]['service_name'],
                         'MISTY')
        self.assertEqual(configuration.cloud_services[0]['service_desc'],
                         'MISTY service')
        self.assertEqual(configuration.cloud_services[0]['service_provider_flavor'],
                         'nostack')

    def test_argument_include_sections_global_accepted(self):
        """Test that peripheral GLOBAL conf overrides are accepted (policy)"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'global.conf')

        self.assertTrue(os.path.isfile(test_conf_section_file))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertEqual(configuration.admin_email, "admin@somewhere.org")
        self.assertEqual(configuration.vgrid_resources, "resources.custom")
        self.assertEqual(configuration.vgrid_triggers, "triggers.custom")
        self.assertEqual(configuration.vgrid_sharelinks, "sharelinks.custom")
        self.assertEqual(configuration.vgrid_monitor, "monitor.custom")

    def test_argument_include_sections_global_rejected(self):
        """Test that core GLOBAL conf overrides are rejected (policy)"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'global.conf')

        self.assertTrue(os.path.isfile(test_conf_section_file))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        # Run through the snippet values and check that override didn't succeed
        # and then that default is left set. The former _could_ be left out but
        # is kept explicit for clarity in case something breaks by changes.
        self.assertNotEqual(configuration.include_sections, '/tmp/MiGserver.d')
        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertNotEqual(configuration.mig_path, '/tmp/mig/mig')
        self.assertEqual(configuration.mig_path, '/home/mig/mig')
        self.assertNotEqual(configuration.logfile, '/tmp/mig.log')
        self.assertEqual(configuration.logfile, 'mig.log')
        self.assertNotEqual(configuration.loglevel, 'warning')
        self.assertEqual(configuration.loglevel, 'info')
        self.assertNotEqual(configuration.server_fqdn, 'somewhere.org')
        self.assertEqual(configuration.server_fqdn, '')
        self.assertNotEqual(configuration.migserver_public_url,
                            'https://somewhere.org')
        self.assertEqual(configuration.migserver_public_url, '')
        self.assertNotEqual(configuration.migserver_https_sid_url,
                            'https://somewhere.org')
        self.assertEqual(configuration.migserver_https_sid_url, '')
        self.assertNotEqual(configuration.user_openid_address, 'somewhere.org')
        self.assertNotEqual(configuration.user_openid_address, 'somewhere.org')
        self.assertEqual(configuration.user_openid_address, '')
        self.assertNotEqual(configuration.user_openid_port, 4242)
        self.assertEqual(configuration.user_openid_port, 8443)
        self.assertNotEqual(configuration.user_openid_key, '/tmp/openid.key')
        self.assertEqual(configuration.user_openid_key, '')
        self.assertNotEqual(configuration.user_openid_log, '/tmp/openid.log')
        self.assertEqual(configuration.user_openid_log,
                         '/home/mig/state/log/openid.log')

    def test_argument_include_sections_site_accepted(self):
        """Test that peripheral SITE conf overrides are accepted (policy)"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'site.conf')

        self.assertTrue(os.path.isfile(test_conf_section_file))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertEqual(configuration.short_title, 'ACME Site')
        self.assertEqual(configuration.new_user_default_ui, 'V3')
        self.assertEqual(configuration.site_password_legacy_policy, 'MEDIUM')
        self.assertEqual(configuration.site_support_text,
                         'Custom support text')
        self.assertEqual(configuration.site_privacy_text,
                         'Custom privacy text')
        self.assertEqual(configuration.site_peers_notice,
                         'Custom peers notice')
        self.assertEqual(configuration.site_peers_contact_hint,
                         'Custom peers contact hint')
        self.assertIsInstance(configuration.site_freeze_admins, list)
        self.assertTrue(len(configuration.site_freeze_admins) == 1)
        self.assertTrue('BOFH' in configuration.site_freeze_admins)
        self.assertEqual(configuration.site_freeze_to_tape,
                         'Custom freeze to tape')
        self.assertEqual(configuration.site_freeze_doi_text,
                         'Custom freeze doi text')
        self.assertEqual(configuration.site_freeze_doi_url,
                         'https://somewhere.org/mint-doi')
        self.assertEqual(configuration.site_freeze_doi_url_field,
                         'archiveurl')

    def test_argument_include_sections_site_rejected(self):
        """Test that core SITE conf overrides are rejected (policy)"""

        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'site.conf')

        self.assertTrue(os.path.isfile(test_conf_section_file))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertEqual(configuration.site_enable_openid, False)
        self.assertEqual(configuration.site_enable_davs, False)
        self.assertEqual(configuration.site_enable_ftps, False)
        self.assertEqual(configuration.site_enable_sftp, False)
        self.assertEqual(configuration.site_enable_sftp_subsys, False)
        self.assertEqual(configuration.site_enable_crontab, True)
        self.assertEqual(configuration.site_enable_events, False)
        self.assertEqual(configuration.site_enable_notify, False)
        self.assertEqual(configuration.site_enable_imnotify, False)
        self.assertEqual(configuration.site_enable_transfers, False)

    def test_argument_include_sections_with_invalid_conf_filename(self):
        """Test that conf snippet with missing .conf extension gets ignored"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'dummy')

        self.assertTrue(os.path.isfile(test_conf_section_file))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        # Conf only contains SETTINGS section which is ignored due to mismatch
        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertIsInstance(configuration.language, list)
        self.assertFalse('Pig Latin' in configuration.language)
        self.assertEqual(configuration.language, ['English'])

    def test_argument_include_sections_with_section_name_mismatch(self):
        """Test that conf section must match filename"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'section-mismatch.conf')

        self.assertTrue(os.path.isfile(test_conf_section_file))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        # Conf only contains SETTINGS section which is ignored due to mismatch
        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertIsInstance(configuration.language, list)
        self.assertFalse('Pig Latin' in configuration.language)
        self.assertEqual(configuration.language, ['English'])

    def test_argument_include_sections_multi_ignores_other_sections(self):
        """Test that conf section must match filename and others are ignored"""
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'multi.conf')

        self.assertTrue(os.path.isfile(test_conf_section_file))
        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        # Conf contains MULTI and SETTINGS sections and latter must be ignored
        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertIsInstance(configuration.language, list)
        self.assertFalse('Spanglish' in configuration.language)
        self.assertEqual(configuration.language, ['English'])
        # TODO: rename file to valid section name we can check and enable next?
        # self.assertEqual(configuration.multi, 'blabla')

    @unittest.skipIf(PY2, "Python 3 only")
    def test_default_object(self):
        expected_values = fixturefile(
            'mig_shared_configuration--new', fixture_format='json')

        configuration = Configuration(None)
        # TODO: the following work-around default values set for these on the
        #       instance that no longer make total sense but fiddling with them
        #       is better as a follow-up.
        configuration.certs_path = '/some/place/certs'
        configuration.state_path = '/some/place/state'
        configuration.mig_path = '/some/place/mig'

        actual_values = _to_dict(configuration)

        self.maxDiff = None
        self.assertEqual(actual_values, expected_values)

    def test_object_isolation(self):
        configuration_1 = Configuration(None)
        configuration_2 = Configuration(None)

        # change one of the configuration objects
        configuration_1.default_page.append('foobar')

        # check the other was not affected
        self.assertEqual(configuration_2.default_page, [''])


if __name__ == '__main__':
    testmain()
