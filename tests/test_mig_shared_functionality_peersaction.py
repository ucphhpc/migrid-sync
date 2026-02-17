# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_cat - unit test of the corresponding mig module
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
import unittest

from tests.support import MIG_BASE, PY2, TEST_DATA_DIR, MigTestCase, testmain, \
    temppath, ensure_dirs_exist
from tests.support.wsgisupp import WsgiAssertMixin, prepare_wsgi

import mig.shared.returnvalues as returnvalues
from mig.shared.base import client_id_dir
from mig.shared.functionality.peersaction import _main as submain


def _import_forcibly(module_name, relative_module_dir=None):
    """Custom import function to allow an import of a file for testing
    that resides within a non-module directory."""

    module_path = os.path.join(MIG_BASE, 'mig')
    if relative_module_dir is not None:
        module_path = os.path.join(module_path, relative_module_dir)
    sys.path.append(module_path)
    mod = importlib.import_module(module_name)
    sys.path.pop(-1)  # do not leave the forced module path
    return mod


migwsgi = _import_forcibly('migwsgi', relative_module_dir='wsgi-bin')


class MigSharedFunctionalityPeersaction(MigTestCase, WsgiAssertMixin):
    """Wrap unit tests for the corresponding module"""

    TEST_CLIENT_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        # force messages logged by the wsgi to be visible by the test suite
        # TODO: this should be done by the test support infractruture
        self.configuration.logger = self.logger
        self.test_user_dir = self._provision_test_user(self, self.TEST_CLIENT_DN)

    def test_should_not_break_with_content_type_text_plain(self):
        payload = {
            'action': ['reject'],
            'peers_label': [],
            'peers_kind': ['collaboration'],
            'peers_expire': '',
            'peers_format': ['userid'],
            'peers_content': ['ABCDE'],
            'peers_invite': '',
        }

        fake_wsgi = prepare_wsgi(self.configuration,
                         'http://localhost/peersaction.py',
                         method='POST',
                         headers={
                            'Content-Type': 'text/plain'
                         },
                         form=payload,
                         mig_user_dn=self.TEST_CLIENT_DN)


        self.application_args = (
            fake_wsgi.environ,
            fake_wsgi.start_response,
        )
        self.application_kwargs = dict(
            configuration=self.configuration,
            _set_os_environ=False,
        )
        wsgi_result = migwsgi.application(
            *self.application_args,
            **self.application_kwargs
        )

        self.assertWsgiResponse(wsgi_result, fake_wsgi, None)


if __name__ == '__main__':
    testmain()
