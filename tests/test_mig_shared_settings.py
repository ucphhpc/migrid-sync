# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_settings - unit test of the corresponding mig shared module
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
import unittest

from mig.shared.settings import load_settings, update_settings, \
    parse_and_save_settings
from mig.shared.settingskeywords import get_keywords_dict

from tests.support import MigTestCase, ensure_dirs_exist, testmain
from tests.support.usersupp import UserAssertMixin, TEST_USER_DN, OTHER_USER_DN

TEST_USER_EMAIL = TEST_USER_DN.split('/emailAddress=', 1)[1]
OTHER_USER_EMAIL = OTHER_USER_DN.split('/emailAddress=', 1)[1]

INIT_SETTINGS_MRSL = """
::EMAIL::
test@example.com

::SITE_USER_MENU::
sharelinks
people
peers
"""
UPDATE_SETTINGS_MRSL = """
::EMAIL::
other@example.com

::SITE_USER_MENU::
people
"""


class MigSharedSettings(MigTestCase, UserAssertMixin):
    """Wrap unit tests for the corresponding module"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def before_each(self):
        """Create clean test environment for vgridaccess tests"""
        conf = self.configuration
        conf.user_interface = ['V3', 'V2', 'V4']
        conf.new_user_default_ui = 'V3'
        used_state_dirs = [
            conf.mig_system_files,
            conf.mig_system_run,
            conf.user_home,
            conf.user_settings,
        ]
        for state_dir in used_state_dirs:
            ensure_dirs_exist(state_dir)
            # Make sure no stale data is left
            self.assertEqual(os.listdir(state_dir), [])
        user_home = self._provision_test_user(self, TEST_USER_DN)
        self.TEST_USER_HOME = user_home
        client_dir = user_home.replace(conf.user_home, '').strip(os.sep)
        self.TEST_USER_SETTINGS = os.path.join(conf.user_settings, client_dir,
                                               'settings')
        self.TEST_SETTINGS_MRSL = os.path.join(conf.mrsl_files_dir, client_dir,
                                               'settings.mRSL')
        self.settings_defaults = get_keywords_dict()

    def test_settings_save_load(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        self.assertTrue(os.path.exists(self.TEST_USER_SETTINGS))

        settings = load_settings(TEST_USER_DN, self.configuration)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(settings, dict))
        self.assertEqual(settings['EMAIL'], [TEST_USER_EMAIL])
        self.assertEqual(settings['SITE_USER_MENU'],
                         ['sharelinks', 'people', 'peers'])
        # NOTE: we no longer auto save default values for optional vars
        for key in settings.keys():
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU'])
        # Any saved USER_INTERFACE value must match configured default if set
        default_ui = self.configuration.new_user_default_ui
        self.assertEqual(settings.get('USER_INTERFACE', default_ui),
                         default_ui)

    def test_settings_replace(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(UPDATE_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        updated = load_settings(TEST_USER_DN, self.configuration)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], [OTHER_USER_EMAIL])
        self.assertEqual(updated['SITE_USER_MENU'], ['people'])

    def test_update_settings_email(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        changes = {'EMAIL': [TEST_USER_EMAIL, OTHER_USER_EMAIL]}
        updated = update_settings(
            TEST_USER_DN, self.configuration, changes, self.settings_defaults)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], [TEST_USER_EMAIL, OTHER_USER_EMAIL])

    def test_update_settings_user_interface_downgrade(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        changes = {'USER_INTERFACE': ['V2']}
        updated = update_settings(
            TEST_USER_DN, self.configuration, changes, self.settings_defaults)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['USER_INTERFACE'], ['V2'])

    def test_update_settings_user_interface_upgrade(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        changes = {'USER_INTERFACE': ['V4']}
        updated = update_settings(
            TEST_USER_DN, self.configuration, changes, self.settings_defaults)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['USER_INTERFACE'], ['V4'])

    @unittest.skip("Fix parser to reject invalid ui values and enable")
    def test_update_settings_user_interface_invalid_fails(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        changes = {'USER_INTERFACE': ['V1']}
        updated = update_settings(
            TEST_USER_DN, self.configuration, changes, self.settings_defaults)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertNotEqual(updated['USER_INTERFACE'], ['V1'])


if __name__ == '__main__':
    testmain()
