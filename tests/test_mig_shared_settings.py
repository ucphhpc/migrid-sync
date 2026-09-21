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

from mig.shared.settings import (
    load_settings,
    parse_and_save_settings,
    update_settings,
)
from mig.shared.settingskeywords import get_keywords_dict

from tests.support import (
    MigTestCase,
    ensure_dirs_exist,
    testmain,
)
from tests.support.usersupp import (
    OTHER_USER_DN,
    TEST_USER_DN,
    UserAssertMixin,
)

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

    def __add_mrsl_key_val(self, mrsl, key, val):
        """Add formatted key and val entries to existing mrsl"""
        return """%s

::%s::
%s
""" % (mrsl.strip(), key.upper(), val)

    def _add_mrsl_ui(self, mrsl, user_interface):
        """Add user_interface to existing mrsl"""
        return self.__add_mrsl_key_val(mrsl, 'USER_INTERFACE', user_interface)

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def before_each(self):
        """Create clean test environment for vgridaccess tests"""
        conf = self.configuration
        conf.user_interface = ['V3', 'V2', 'V4', 'V1']
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
        kwd = get_keywords_dict()
        # self.settings_defaults = dict([(i, kwd[i]['Value']) for i in kwd])
        self.settings_defaults = {i: kwd[i]['Value'] for i in kwd}

    def test_settings_save_load(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        self.assertTrue(os.path.exists(self.TEST_USER_SETTINGS))

        saved = load_settings(TEST_USER_DN, self.configuration)
        # NOTE: saved should be a non-empty dict at this point
        self.assertTrue(isinstance(saved, dict))
        self.assertEqual(saved['EMAIL'], [TEST_USER_EMAIL])
        self.assertEqual(saved['SITE_USER_MENU'],
                         ['sharelinks', 'people', 'peers'])
        # NOTE: we no longer auto save default values for optional vars
        for key in saved:
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU'])

    def test_save_settings_email_and_menu_does_not_change_user_interface(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        saved = load_settings(TEST_USER_DN, self.configuration)
        self.assertTrue(isinstance(saved, dict))
        self.assertEqual(saved['EMAIL'], [TEST_USER_EMAIL])
        self.assertEqual(saved['SITE_USER_MENU'], ['sharelinks', 'people',
                                                   'peers'])
        self.assertNotEqual(saved.get('USER_INTERFACE', 'UNSET'), 'V2')
        self.assertEqual(saved.get('USER_INTERFACE', 'UNSET'), 'UNSET')

    # TODO: fix issue 667 and re-enable this test
    @unittest.skip("Fix parser to not skip kw default value when conf differs")
    def test_settings_save_with_user_interface_v2(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(self._add_mrsl_ui(INIT_SETTINGS_MRSL, 'V2'))
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        saved = load_settings(TEST_USER_DN, self.configuration)
        # print("DEBUG: loaded saved %s" % saved)
        # NOTE: saved should be a non-empty dict at this point
        self.assertTrue(isinstance(saved, dict))
        self.assertEqual(saved['EMAIL'], [TEST_USER_EMAIL])
        self.assertEqual(saved['SITE_USER_MENU'], ['sharelinks', 'people',
                                                   'peers'])
        self.assertEqual(saved['USER_INTERFACE'], 'V2')
        # NOTE: we no longer auto save default values for optional vars
        for key in saved:
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU',
                                    'USER_INTERFACE'])

    def test_settings_replace_existing_values(self):
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
        # NOTE: we no longer auto save default values for optional vars
        for key in updated:
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU'])

    def test_settings_replace_with_user_interface_v1(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(self._add_mrsl_ui(INIT_SETTINGS_MRSL, 'V1'))
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        updated = load_settings(TEST_USER_DN, self.configuration)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], [TEST_USER_EMAIL])
        self.assertEqual(updated['SITE_USER_MENU'], ['sharelinks', 'people',
                                                     'peers'])
        self.assertEqual(updated['USER_INTERFACE'], 'V1')
        # NOTE: we no longer auto save default values for optional vars
        for key in updated:
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU',
                                    'USER_INTERFACE'])

    # TODO: fix issue 667 and re-enable this test
    @unittest.skip("Fix parser to not skip kw default value when conf differs")
    def test_settings_replace_with_user_interface_v2(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(self._add_mrsl_ui(INIT_SETTINGS_MRSL, 'V2'))
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        updated = load_settings(TEST_USER_DN, self.configuration)
        # print("DEBUG: loaded updated %s" % updated)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], [TEST_USER_EMAIL])
        self.assertEqual(updated['SITE_USER_MENU'], ['sharelinks', 'people',
                                                     'peers'])
        self.assertEqual(updated['USER_INTERFACE'], 'V2')
        # NOTE: we no longer auto save default values for optional vars
        for key in updated:
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU',
                                    'USER_INTERFACE'])

    def test_settings_replace_with_user_interface_v3(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(self._add_mrsl_ui(INIT_SETTINGS_MRSL, 'V3'))
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        updated = load_settings(TEST_USER_DN, self.configuration)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], [TEST_USER_EMAIL])
        self.assertEqual(updated['SITE_USER_MENU'], ['sharelinks', 'people',
                                                     'peers'])
        self.assertEqual(updated['USER_INTERFACE'], 'V3')
        # NOTE: we no longer auto save default values for optional vars
        for key in updated:
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU',
                                    'USER_INTERFACE'])

    def test_settings_replace_with_user_interface_v4(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(self._add_mrsl_ui(INIT_SETTINGS_MRSL, 'V4'))
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        updated = load_settings(TEST_USER_DN, self.configuration)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], [TEST_USER_EMAIL])
        self.assertEqual(updated['SITE_USER_MENU'], ['sharelinks', 'people',
                                                     'peers'])
        self.assertEqual(updated['USER_INTERFACE'], 'V4')
        # NOTE: we no longer auto save default values for optional vars
        for key in updated:
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU',
                                    'USER_INTERFACE'])

    @unittest.skip("Fix parser to reject invalid ui values and enable")
    def test_settings_replace_with_user_interface_invalid(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(self._add_mrsl_ui(INIT_SETTINGS_MRSL, 'V0'))
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        updated = load_settings(TEST_USER_DN, self.configuration)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], [TEST_USER_EMAIL])
        self.assertEqual(updated['SITE_USER_MENU'], ['sharelinks', 'people',
                                                     'peers'])
        self.assertNotEqual(updated['USER_INTERFACE'], 'V0')
        # NOTE: we no longer auto save default values for optional vars
        for key in updated:
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU',
                                    'USER_INTERFACE'])

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

    def test_update_settings_user_interface_v2(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        changes = {'USER_INTERFACE': 'V2'}
        updated = update_settings(
            TEST_USER_DN, self.configuration, changes, self.settings_defaults)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['USER_INTERFACE'], 'V2')

    def test_update_settings_user_interface_same_as_conf_default(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        changes = {'USER_INTERFACE': 'V3'}
        updated = update_settings(
            TEST_USER_DN, self.configuration, changes, self.settings_defaults)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['USER_INTERFACE'], 'V3')

    def test_update_settings_user_interface_v4(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        changes = {'USER_INTERFACE': 'V4'}
        updated = update_settings(
            TEST_USER_DN, self.configuration, changes, self.settings_defaults)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['USER_INTERFACE'], 'V4')

    @unittest.skip("Fix parser to reject invalid ui values and enable")
    def test_update_settings_user_interface_invalid_fails(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        changes = {'USER_INTERFACE': 'V0'}
        updated = update_settings(
            TEST_USER_DN, self.configuration, changes, self.settings_defaults)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertNotEqual(updated['USER_INTERFACE'], 'V0')

    @unittest.skip("Fix parser to not force default keyword ui value")
    def test_update_settings_email_does_not_change_user_interface(self):
        with open(self.TEST_SETTINGS_MRSL, 'w') as mrsl_fd:
            mrsl_fd.write(INIT_SETTINGS_MRSL)
        save_status, save_msg = parse_and_save_settings(
            self.TEST_SETTINGS_MRSL, TEST_USER_DN, self.configuration)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        saved = load_settings(TEST_USER_DN, self.configuration)
        # print("DEBUG: loaded orig %s" % saved)
        self.assertTrue(isinstance(saved, dict))
        self.assertEqual(saved['EMAIL'], [TEST_USER_EMAIL])
        self.assertNotEqual(saved.get('USER_INTERFACE', 'UNSET'), 'V2')
        self.assertEqual(saved.get('USER_INTERFACE', 'UNSET'), 'UNSET')

        changes = {'EMAIL': [TEST_USER_EMAIL, OTHER_USER_EMAIL]}
        update_res = update_settings(
            TEST_USER_DN, self.configuration, changes, self.settings_defaults)
        # NOTE: updated should be a non-empty dict at this point
        # print("DEBUG: update res %s" % update_res)
        self.assertTrue(isinstance(update_res, dict))
        updated = load_settings(TEST_USER_DN, self.configuration)
        # print("DEBUG: loaded %s" % updated)
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], [TEST_USER_EMAIL, OTHER_USER_EMAIL])
        self.assertNotEqual(updated.get('USER_INTERFACE', 'UNSET'), 'V2')
        self.assertEqual(updated.get('USER_INTERFACE', 'UNSET'), '')


if __name__ == '__main__':
    testmain()
