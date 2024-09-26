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

"""Unit tests of the MiG functionality file implementing the cat resource."""

from __future__ import print_function
import importlib
import os
import shutil
import sys

from tests.support import MIG_BASE, MigTestCase, testmain, \
    fixturefile, fixturefile_normname, \
    _ensuredirs, _temppath

from mig.shared.base import client_id_dir
from mig.shared.functionality.cat import _main as main


def create_http_environ(configuration, wsgi_variables={}):
    """Small helper that can create a minimum viable environ dict suitable
    for passing to http-facing code for the supplied configuration."""

    environ = {}
    environ['MIG_CONF'] = configuration.config_file
    environ['HTTP_HOST'] = wsgi_variables.get('http_host', 'localhost')
    environ['PATH_INFO'] = wsgi_variables.get('path_info', '/')
    environ['REMOTE_ADDR'] = wsgi_variables.get('remote_addr', '127.0.0.1')
    environ['SCRIPT_URI'] = ''.join(('http://', environ['HTTP_HOST'], environ['PATH_INFO']))
    return environ


class MigCgibinCat(MigTestCase):
    TEST_CLIENT_ID = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        # ensure a user home directory for our test user
        conf_user_home = self.configuration.user_home[:-1]
        test_client_dir = client_id_dir(self.TEST_CLIENT_ID)
        test_user_dir = os.path.join(conf_user_home, test_client_dir)

        # ensure a user db that includes our test user
        conf_user_db_home = _ensuredirs(self.configuration.user_db_home)
        _temppath(conf_user_db_home, self)
        db_fixture, db_fixture_file = fixturefile('MiG-users.db--example', fixture_format='binary', include_path=True)
        test_db_file = _temppath(fixturefile_normname('MiG-users.db--example', prefix=conf_user_db_home), self)
        shutil.copyfile(db_fixture_file, test_db_file)

        # create the test user home directory
        self.test_user_dir = _ensuredirs(test_user_dir)
        _temppath(self.test_user_dir, self)
        self.test_environ = create_http_environ(self.configuration)

    def test_returns_file_output_with_single_file_match(self):
        with open(os.path.join(self.test_user_dir, 'foobar.txt'), 'w'):
            pass
        payload = {
            'path': ['foobar.txt'],
        }

        (output_objects, status) = main(self.configuration, self.logger, client_id=self.TEST_CLIENT_ID, user_arguments_dict=payload, environ=self.test_environ)
        self.assertEqual(len(output_objects), 1)
        output_obj = output_objects[0]
        self.assertEqual(output_obj['object_type'], 'file_output')


if __name__ == '__main__':
    testmain()
