# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_settings - unit test of the corresponding mig shared module
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

import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from tests.support import TEST_OUTPUT_DIR, MigTestCase, FakeConfiguration, \
    cleanpath, testmain
from mig.shared.settings import load_settings, update_settings, \
    parse_and_save_settings

DUMMY_USER = "dummy-user"
DUMMY_SETTINGS_DIR = 'dummy_user_settings'
DUMMY_SETTINGS_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_SETTINGS_DIR)
DUMMY_SYSTEM_FILES_DIR = 'dummy_system_files'
DUMMY_SYSTEM_FILES_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_SYSTEM_FILES_DIR)
DUMMY_TMP_DIR = 'dummy_tmp'
DUMMY_TMP_FILE = 'settings.mRSL'
DUMMY_TMP_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_TMP_DIR)
DUMMY_MRSL_PATH = os.path.join(DUMMY_TMP_PATH, DUMMY_TMP_FILE)

DUMMY_USER_INTERFACE = ['V3', 'V42']
DUMMY_DEFAULT_UI = 'V42'
DUMMY_INIT_MRSL = """
::EMAIL::
john@doe.org

::SITE_USER_MENU::
sharelinks
people
peers
"""
DUMMY_UPDATE_MRSL = """
::EMAIL::
jane@doe.org

::SITE_USER_MENU::
people
"""
DUMMY_CONF = FakeConfiguration(user_settings=DUMMY_SETTINGS_PATH,
                               mig_system_files=DUMMY_SYSTEM_FILES_PATH,
                               user_interface=DUMMY_USER_INTERFACE,
                               new_user_default_ui=DUMMY_DEFAULT_UI)


class MigSharedSettings(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def test_settings_save_load(self):
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        cleanpath(DUMMY_SETTINGS_DIR, self)
        os.makedirs(os.path.join(DUMMY_SYSTEM_FILES_PATH, DUMMY_USER))
        cleanpath(DUMMY_SYSTEM_FILES_DIR, self)
        os.makedirs(os.path.join(DUMMY_TMP_PATH))
        cleanpath(DUMMY_TMP_DIR, self)

        with open(DUMMY_MRSL_PATH, 'w') as mrsl_fd:
            mrsl_fd.write(DUMMY_INIT_MRSL)
        save_status, save_msg = parse_and_save_settings(
            DUMMY_MRSL_PATH, DUMMY_USER, DUMMY_CONF)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        saved_path = os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER, 'settings')
        self.assertTrue(os.path.exists(saved_path))

        settings = load_settings(DUMMY_USER, DUMMY_CONF)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(settings, dict))
        self.assertEqual(settings['EMAIL'], ['john@doe.org'])
        self.assertEqual(settings['SITE_USER_MENU'],
                         ['sharelinks', 'people', 'peers'])
        # NOTE: we no longer auto save default values for optional vars
        for key in settings.keys():
            self.assertTrue(key in ['EMAIL', 'SITE_USER_MENU'])
        # Any saved USER_INTERFACE value must match configured default if set
        self.assertEqual(settings.get('USER_INTERFACE', DUMMY_DEFAULT_UI),
                         DUMMY_DEFAULT_UI)

    def test_settings_replace(self):
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        cleanpath(DUMMY_SETTINGS_DIR, self)
        os.makedirs(os.path.join(DUMMY_SYSTEM_FILES_PATH, DUMMY_USER))
        cleanpath(DUMMY_SYSTEM_FILES_DIR, self)
        os.makedirs(os.path.join(DUMMY_TMP_PATH))
        cleanpath(DUMMY_TMP_DIR, self)

        with open(DUMMY_MRSL_PATH, 'w') as mrsl_fd:
            mrsl_fd.write(DUMMY_INIT_MRSL)
        save_status, save_msg = parse_and_save_settings(
            DUMMY_MRSL_PATH, DUMMY_USER, DUMMY_CONF)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        with open(DUMMY_MRSL_PATH, 'w') as mrsl_fd:
            mrsl_fd.write(DUMMY_UPDATE_MRSL)
        save_status, save_msg = parse_and_save_settings(
            DUMMY_MRSL_PATH, DUMMY_USER, DUMMY_CONF)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        updated = load_settings(DUMMY_USER, DUMMY_CONF)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], ['jane@doe.org'])
        self.assertEqual(updated['SITE_USER_MENU'], ['people'])

    def test_update_settings(self):
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        cleanpath(DUMMY_SETTINGS_DIR, self)
        os.makedirs(os.path.join(DUMMY_SYSTEM_FILES_PATH, DUMMY_USER))
        cleanpath(DUMMY_SYSTEM_FILES_DIR, self)
        os.makedirs(os.path.join(DUMMY_TMP_PATH))
        cleanpath(DUMMY_TMP_DIR, self)

        with open(DUMMY_MRSL_PATH, 'w') as mrsl_fd:
            mrsl_fd.write(DUMMY_INIT_MRSL)
        save_status, save_msg = parse_and_save_settings(
            DUMMY_MRSL_PATH, DUMMY_USER, DUMMY_CONF)
        self.assertTrue(save_status)
        self.assertFalse(save_msg)

        changes = {'EMAIL': ['john@doe.org', 'jane@doe.org']}
        defaults = {}
        updated = update_settings(DUMMY_USER, DUMMY_CONF, changes, defaults)
        # NOTE: updated should be a non-empty dict at this point
        self.assertTrue(isinstance(updated, dict))
        self.assertEqual(updated['EMAIL'], ['john@doe.org', 'jane@doe.org'])


if __name__ == '__main__':
    testmain()
