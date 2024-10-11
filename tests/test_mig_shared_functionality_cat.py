# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_cat - cat functionality unit test
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

"""Unit tests of the MiG functionality file implementing the cat backend"""

from __future__ import print_function
import importlib
import os
import shutil
import sys

from tests.support import MIG_BASE, TEST_DATA_DIR, MigTestCase, testmain, \
    fixturefile, fixturefile_normname, ensure_dirs_exist, temppath

from mig.shared.base import client_id_dir
from mig.shared.functionality.cat import _main as main


def create_http_environ(configuration):
    """Small helper that can create a minimum viable environ dict suitable
    for passing to http-facing code for the supplied configuration.
    """

    environ = {}
    environ['MIG_CONF'] = configuration.config_file
    environ['HTTP_HOST'] = 'localhost'
    environ['PATH_INFO'] = '/'
    environ['REMOTE_ADDR'] = '127.0.0.1'
    environ['SCRIPT_URI'] = ''.join(('https://', environ['HTTP_HOST'],
                                     environ['PATH_INFO']))
    return environ


class MigSharedFunctionalityCat(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    TEST_CLIENT_ID = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        # ensure a user home directory for our test user
        conf_user_home = self.configuration.user_home[:-1]
        test_client_dir = client_id_dir(self.TEST_CLIENT_ID)
        test_user_dir = os.path.join(conf_user_home, test_client_dir)

        # ensure a user db that includes our test user
        conf_user_db_home = ensure_dirs_exist(self.configuration.user_db_home)
        temppath(conf_user_db_home, self, skip_output_anchor=True)
        db_fixture, db_fixture_file = fixturefile('MiG-users.db--example',
                                                  fixture_format='binary',
                                                  include_path=True)
        test_db_file = temppath(fixturefile_normname('MiG-users.db--example',
                                                     prefix=conf_user_db_home),
                                self, skip_output_anchor=True)
        shutil.copyfile(db_fixture_file, test_db_file)

        # create the test user home directory
        self.test_user_dir = ensure_dirs_exist(test_user_dir)
        temppath(self.test_user_dir, self, skip_output_anchor=True)
        self.test_environ = create_http_environ(self.configuration)

    def test_file_serving_a_single_file_match(self):
        with open(os.path.join(self.test_user_dir, 'foobar.txt'), 'w'):
            pass
        payload = {
            'path': ['foobar.txt'],
        }

        (output_objects, status) = main(self.configuration, self.logger,
                                        client_id=self.TEST_CLIENT_ID,
                                        user_arguments_dict=payload,
                                        environ=self.test_environ)
        self.assertEqual(len(output_objects), 1)
        output_obj = output_objects[0]
        self.assertEqual(output_obj['object_type'], 'file_output')

    def test_file_serving_at_limit(self):
        test_binary_file = os.path.realpath(
            os.path.join(TEST_DATA_DIR, 'loading.gif'))
        test_binary_file_size = os.stat(test_binary_file).st_size
        with open(test_binary_file, 'rb') as fh_test_file:
            test_binary_file_data = fh_test_file.read()
        shutil.copyfile(test_binary_file, os.path.join(
            self.test_user_dir, 'loading.gif'))
        payload = {
            'output_format': ['file'],
            'path': ['loading.gif'],
        }

        self.configuration.wwwserve_max_bytes = test_binary_file_size

        (output_objects, status) = main(self.configuration, self.logger,
                                        client_id=self.TEST_CLIENT_ID,
                                        user_arguments_dict=payload,
                                        environ=self.test_environ)
        # TODO: two file_output objects seem to be returned
        self.assertEqual(len(output_objects), 3)
        relevant_obj = output_objects[2]
        self.assertEqual(relevant_obj['object_type'], 'file_output')
        self.assertEqual(len(relevant_obj['lines']), 1)
        self.assertEqual(relevant_obj['lines'][0], test_binary_file_data)

    def test_file_serving_over_limit(self):
        test_binary_file = os.path.realpath(os.path.join(TEST_DATA_DIR,
                                                         'loading.gif'))
        test_binary_file_size = os.stat(test_binary_file).st_size
        with open(test_binary_file, 'rb') as fh_test_file:
            test_binary_file_data = fh_test_file.read()
        shutil.copyfile(test_binary_file, os.path.join(self.test_user_dir,
                                                       'loading.gif'))
        payload = {
            'output_format': ['file'],
            'path': ['loading.gif'],
        }

        self.configuration.wwwserve_max_bytes = test_binary_file_size - 1

        (output_objects, status) = main(self.configuration, self.logger,
                                        client_id=self.TEST_CLIENT_ID,
                                        user_arguments_dict=payload,
                                        environ=self.test_environ)
        self.assertEqual(len(output_objects), 4)
        relevant_obj = output_objects[3]
        self.assertEqual(relevant_obj['object_type'], 'error_text')
        self.assertEqual(relevant_obj['text'],
                         "Site configuration prevents web serving contents "
                         "bigger than 3896 bytes - please use better "
                         "alternatives (sftp) to retrieve large data.")


if __name__ == '__main__':
    testmain()
