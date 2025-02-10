# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_useradm - unit test of the corresponding mig shared module
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

"""Unit tests for the migrid module pointed to in the filename"""

from past.builtins import basestring
import binascii
import difflib
import io
import os
import pwd
import sys
import unittest

from tests.support import MIG_BASE, TEST_OUTPUT_DIR, PY2, MigTestCase, \
    FakeConfiguration, testmain, cleanpath, is_path_within

from mig.shared.defaults import keyword_auto, htaccess_filename, \
    DEFAULT_USER_ID_FORMAT
from mig.shared.useradm import assure_current_htaccess

DUMMY_USER = 'dummy-user'
DUMMY_STALE_USER = 'dummy-stale-user'
DUMMY_HOME_DIR = 'dummy_user_home'
DUMMY_SETTINGS_DIR = 'dummy_user_settings'
DUMMY_MRSL_FILES_DIR = 'dummy_mrsl_files'
DUMMY_RESOURCE_PENDING_DIR = 'dummy_resource_pending'
DUMMY_CACHE_DIR = 'dummy_user_cache'
DUMMY_HOME_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_HOME_DIR)
DUMMY_SETTINGS_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_SETTINGS_DIR)
DUMMY_MRSL_FILES_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_MRSL_FILES_DIR)
DUMMY_RESOURCE_PENDING_PATH = os.path.join(TEST_OUTPUT_DIR,
                                           DUMMY_RESOURCE_PENDING_DIR)
DUMMY_CACHE_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_CACHE_DIR)
DUMMY_USER_DICT = {'distinguished_name': DUMMY_USER,
                   'short_id': '%s@my.org' % DUMMY_USER}
DUMMY_REL_HTACCESS_PATH = os.path.join(DUMMY_HOME_DIR, DUMMY_USER,
                                       htaccess_filename)
DUMMY_HTACCESS_PATH = DUMMY_REL_HTACCESS_PATH.replace(DUMMY_HOME_DIR,
                                                      DUMMY_HOME_PATH)
DUMMY_REL_HTACCESS_BACKUP_PATH = os.path.join(DUMMY_CACHE_DIR, DUMMY_USER,
                                              "%s.old" % htaccess_filename)
DUMMY_HTACCESS_BACKUP_PATH = DUMMY_REL_HTACCESS_BACKUP_PATH.replace(
    DUMMY_CACHE_DIR, DUMMY_CACHE_PATH)
DUMMY_REQUIRE_USER = 'require user "%s"' % DUMMY_USER
DUMMY_REQUIRE_STALE_USER = 'require user "%s"' % DUMMY_STALE_USER
DUMMY_CONF = FakeConfiguration(user_home=DUMMY_HOME_PATH,
                               user_settings=DUMMY_SETTINGS_PATH,
                               user_cache=DUMMY_CACHE_PATH,
                               mrsl_files_dir=DUMMY_MRSL_FILES_PATH,
                               resource_pending=DUMMY_RESOURCE_PENDING_PATH,
                               site_user_id_format=DEFAULT_USER_ID_FORMAT,
                               short_title='dummysite',
                               support_email='support@dummysite.org',
                               user_openid_providers=['dummyoidprovider.org'],
                               )


class MigSharedUseradm__assure_current_htaccess(MigTestCase):
    """Unit test helper for the migrid code pointed to in class name"""

    def before_each(self):
        """The create_user call requires quite a few helper dirs"""
        os.makedirs(os.path.join(DUMMY_HOME_PATH, DUMMY_USER))
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        os.makedirs(os.path.join(DUMMY_MRSL_FILES_PATH, DUMMY_USER))
        os.makedirs(os.path.join(DUMMY_RESOURCE_PENDING_PATH, DUMMY_USER))
        os.makedirs(os.path.join(DUMMY_CACHE_PATH, DUMMY_USER))
        cleanpath(DUMMY_HOME_PATH, self)
        cleanpath(DUMMY_SETTINGS_PATH, self)
        cleanpath(DUMMY_MRSL_FILES_PATH, self)
        cleanpath(DUMMY_RESOURCE_PENDING_PATH, self)
        cleanpath(DUMMY_CACHE_PATH, self)

    def assertHtaccessRequireUserClause(self, generated, expected):
        """Makes sure generated htaccess file contains the expected string"""
        if isinstance(generated, basestring):
            with io.open(generated) as htaccess_file:
                generated = htaccess_file.read()

        #print("DEBUG: generated htaccess:\n%s" % generated)

        generated_lines = generated.split('\n')
        if not expected in generated_lines:
            raise AssertionError("no such require user line: %s" % expected)

    def test_skips_accounts_without_short_id(self):
        user_dict = {}
        user_dict.update(DUMMY_USER_DICT)
        del user_dict['short_id']
        assure_current_htaccess(DUMMY_CONF, DUMMY_USER, user_dict, False,
                                False)

        try:
            path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_PATH)
            # File should not exist here at all
            self.assertNotEqual(path_kind, "file")
        except OSError as ignore_oserr:
            #print("DEBUG: oserror found as expected: %s" % ignore_oserr)
            pass

    # NOTE: hits unrelated python3 issues on main so only enable on next
    @unittest.skipUnless(PY2, "Python 2 only")
    def test_creates_missing_htaccess_file(self):
        user_dict = {}
        user_dict.update(DUMMY_USER_DICT)
        assure_current_htaccess(DUMMY_CONF, DUMMY_USER, user_dict, False,
                                False)

        path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_PATH)
        # File should exist here and be valid
        self.assertEqual(path_kind, "file")
        path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_BACKUP_PATH)
        # Backup file should exist here and be empty
        self.assertEqual(path_kind, "file")

        self.assertHtaccessRequireUserClause(DUMMY_HTACCESS_PATH,
                                             DUMMY_REQUIRE_USER)

    # NOTE: hits unrelated python3 issues on main so only enable on next
    @unittest.skipUnless(PY2, "Python 2 only")
    def test_repairs_existing_stale_htaccess_file(self):
        user_dict = {}
        user_dict.update(DUMMY_USER_DICT)
        # Fake stale user ID directly through DN
        user_dict['distinguished_name'] = DUMMY_STALE_USER
        assure_current_htaccess(DUMMY_CONF, DUMMY_USER, user_dict, False,
                                False)

        # Verify stale
        self.assertHtaccessRequireUserClause(DUMMY_HTACCESS_PATH,
                                             DUMMY_REQUIRE_STALE_USER)

        # Reset stale user ID and retry
        user_dict = {}
        user_dict.update(DUMMY_USER_DICT)
        assure_current_htaccess(DUMMY_CONF, DUMMY_USER, user_dict, False,
                                False)

        path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_PATH)
        # File should exist here and be valid
        self.assertEqual(path_kind, "file")
        path_kind = self.assertPathExists(DUMMY_REL_HTACCESS_BACKUP_PATH)
        # Backup file should exist here and be empty
        self.assertEqual(path_kind, "file")

        self.assertHtaccessRequireUserClause(DUMMY_HTACCESS_PATH,
                                             DUMMY_REQUIRE_USER)


if __name__ == '__main__':
    testmain()
