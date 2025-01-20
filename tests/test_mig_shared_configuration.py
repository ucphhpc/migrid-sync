# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_configuration - unit test of configuration
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

"""Unit tests for the configuration object"""

import inspect
import os
import unittest

from tests.support import MigTestCase, testmain, \
    MIG_BASE, TEST_OUTPUT_DIR, TEST_DATA_DIR
from tests.support.fixturesupp import FixtureAssertMixin

from mig.shared.configuration import Configuration, fix_missing, \
    _CONFIGURATION_ARGUMENTS, _CONFIGURATION_PROPERTIES

TEST_TEMPLATE_CACHE_DIR = os.path.join(TEST_OUTPUT_DIR, "__template_cache__")


class MigSharedConfiguration__static_definitions(MigTestCase):
    """Coverage of the static definitions underlying Configuration objects."""

    def test_consistent_parameters(self):
        configuration_defaults_keys = set(_CONFIGURATION_PROPERTIES.keys())
        mismatched = _CONFIGURATION_ARGUMENTS - configuration_defaults_keys

        self.assertEqual(len(mismatched), 0,
                         "configuration defaults do not match arguments")


class MigSharedConfiguration__incomplete_configurations(MigTestCase):
    """Coverage of loaded Configuration instances."""

    SUBSTITUTED_PROPERTIES = [
        'server_fqdn',
        'admin_email',
        'migserver_http_url',
        'mig_server_id',
        'smtp_server',
        'user_sftp_address',
        'user_sftp_subsys_address',
        'user_davs_address',
        'user_ftps_address',
        'user_openid_address',
    ]

    def test_fix_missing_completes_an_empty_file(self):
        conf_file = os.path.join(TEST_OUTPUT_DIR, "empty.conf")
        open(conf_file, 'w').close()

        def noop(*args):
            pass

        fix_missing(conf_file, print=noop)

        # check it is now a valid configuration
        try:
            Configuration(conf_file, skip_log=True, disable_auth_log=True)
        except Exception as exc:
            self.assertFalse(True, 'should not be reached')

    def test_fix_missing_performs_substitutions(self):
        conf_file = os.path.join(TEST_OUTPUT_DIR, "empty.conf")
        open(conf_file, 'w').close()

        def noop(*args):
            pass

        fix_missing(conf_file, user='testuser', fqdn='testhost', print=noop)
        fixed_configuration = Configuration(
            conf_file, skip_log=True, disable_auth_log=True)

        # check the substitutions were made correctly
        only_substituted_properties = {attr: getattr(fixed_configuration, attr)
                                       for attr in self.SUBSTITUTED_PROPERTIES}
        admin_email = only_substituted_properties.pop('admin_email')
        admin_email.endswith('@localhost')
        self.assertEqual(only_substituted_properties, {
            'mig_server_id': 'testhost.0',
            'migserver_http_url': 'http://testhost',
            'server_fqdn': 'testhost',
            'smtp_server': 'testhost',
            'user_davs_address': 'testhost',
            'user_ftps_address': 'testhost',
            'user_openid_address': 'testhost',
            'user_sftp_address': 'testhost',
            'user_sftp_subsys_address': 'testhost',
        })


class MigSharedConfiguration__loaded_configurations(MigTestCase):
    """Coverage of loaded Configuration instances."""

    def test_argument_new_user_default_ui_is_replaced(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised.conf')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.new_user_default_ui, 'V3')

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

    def test_structured_templates_defaults(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--empty_templates.conf')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        division = configuration.division(section_name='TEMPLATES')
        self.assertEqual(division.__dict__, {
            'base_packages': [],
            'cache_dir': os.path.join(MIG_BASE, 'state', 'templates'),
        })

    def test_structured_templates_enabled(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--templates.conf')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        division = configuration.division(section_name='TEMPLATES')
        self.assertEqual(division.__dict__, {
            'base_packages': ['testplugin'],
            'cache_dir': TEST_TEMPLATE_CACHE_DIR,
        })


class MigSharedConfiguration__new_instance(MigTestCase, FixtureAssertMixin):
    """Coverage of programatically created Configuration instances."""

    def test_default_object(self):
        prepared_fixture = self.prepareFixtureAssert(
            'mig_shared_configuration--new', fixture_format='json')

        configuration = Configuration(None)
        # TODO: the following work-around default values set for these on the
        #       instance that no longer make total sense but fiddling with them
        #       is better as a follow-up.
        configuration.certs_path = '/some/place/certs'
        configuration.state_path = '/some/place/state'
        configuration.mig_path = '/some/place/mig'

        actual_values = Configuration.to_dict(configuration)

        prepared_fixture.assertAgainstFixture(actual_values)

    def test_object_isolation(self):
        configuration_1 = Configuration(None)
        configuration_2 = Configuration(None)

        # change one of the configuration objects
        configuration_1.default_page.append('foobar')

        # check the other was not affected
        self.assertEqual(configuration_2.default_page, [''])

    def test_structured_templates_defaults(self):
        configuration = Configuration(
            None, skip_log=True, disable_auth_log=True)

        division = configuration.division(section_name='TEMPLATES')
        self.assertEqual(division.__dict__, {
            'base_packages': [],
            'cache_dir': os.path.join(MIG_BASE, 'state', 'templates'),
        })


if __name__ == '__main__':
    testmain()
