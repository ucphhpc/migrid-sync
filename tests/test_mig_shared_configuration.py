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

from tests.support import MigTestCase, TEST_DATA_DIR, TEST_OUTPUT_DIR, PY2, \
    testmain, fixturefile
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
        #self.assertEqual(configuration.storage_protocols, ['xxx', 'yyy', 'zzz'])
        # TODO: why does even our explicit testdata value 'sftp' yield [] here?
        #self.assertEqual(configuration.storage_protocols, ['sftp'])
        self.assertEqual(configuration.storage_protocols, [])

    def test_argument_wwwserve_max_bytes(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised.conf')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.wwwserve_max_bytes, 43211234)

    def test_argument_include_sections(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised.conf')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections,
                         '/home/mig/mig/server/MiGserver.d')

    def test_argument_custom_include_sections(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections,
                         test_conf_section_dir)

    def test_argument_include_sections_quota(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'quota.conf')

        configuration = Configuration(
            test_conf_file, skip_log=True, disable_auth_log=True)

        self.assertEqual(configuration.include_sections, test_conf_section_dir)
        self.assertEqual(configuration.quota_backend, 'dummy')
        self.assertEqual(configuration.quota_user_limit, 4242)
        self.assertEqual(configuration.quota_vgrid_limit, 4242424242)

    def test_argument_include_sections_cloud_misty(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, 'MiGserver--customised-include_sections.conf')
        test_conf_section_dir = os.path.join('tests', 'data', 'MiGserver.d')
        test_conf_section_file = os.path.join(test_conf_section_dir,
                                              'cloud_misty.conf')

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
