# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_docs - unit test of the corresponding mig module
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

"""Unit tests of the MiG functionality file implementing the docs backend"""

from __future__ import print_function

import os

# Imports required for the unit test wrapping
import mig.shared.returnvalues as returnvalues
from mig.shared.base import client_id_dir

# Imports of the code under test
from mig.shared.functionality.docs import _main as submain
from mig.shared.functionality.docs import main as realmain

# Imports required for the unit tests themselves
from tests.support import (
    MigTestCase,
    ensure_dirs_exist,
    temppath,
    testmain,
)
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin
from tests.support.wsgisupp import create_http_environ, filter_output_objects


class MigSharedFunctionalityDocs(MigTestCase, UserAssertMixin):
    """Wrap unit tests for the corresponding module"""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self.test_user_dir = self._provision_test_user(self, TEST_USER_DN)
        self.test_environ = create_http_environ(self.configuration)

    def test_show_default_site_docs(self):
        payload = {"show": [""]}

        output_objects, status = submain(
            self.configuration,
            self.logger,
            client_id=TEST_USER_DN,
            user_arguments_dict=payload,
            environ=self.test_environ,
        )
        self.assertEqual(status, returnvalues.OK)

        # We expect two text messages here
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 2)

        # We expect 6 html snippets here
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 6)


# TODO: add additional tests to cover other uses

if __name__ == "__main__":
    testmain()
