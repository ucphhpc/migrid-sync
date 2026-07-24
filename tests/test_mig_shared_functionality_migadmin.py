# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_migadmin - unit test of the corresponding mig module
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

"""Unit tests of the MiG functionality file implementing the migadmin
backend.
"""

from __future__ import print_function

import unittest

# Imports required for the unit test wrapping
import mig.shared.returnvalues as returnvalues

# Imports of the code under test
from mig.shared.functionality.migadmin import main as backend_main

# Imports required for the unit tests themselves
from tests.support import (
    MigTestCase,
    ensure_dirs_exist,
    testmain,
)
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin
from tests.support.wsgisupp import create_http_environ, filter_output_objects

TEST_USER_EMAIL = TEST_USER_DN.split("/emailAddress=", 1)[-1]


class MigSharedFunctionalityMigadmin(MigTestCase, UserAssertMixin):
    """Wrap unit tests for the corresponding module"""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        ensure_dirs_exist(self.configuration.user_home)
        ensure_dirs_exist(self.configuration.user_pending)
        ensure_dirs_exist(self.configuration.sitestats_home)
        ensure_dirs_exist(self.configuration.mig_system_files)
        self.test_user_dir = self._provision_test_user(self, TEST_USER_DN)
        self.test_environ = create_http_environ(
            self.configuration,
            "wsgi-bin/migadmin.py",
        )
        self.test_environ["SSL_CLIENT_S_DN"] = TEST_USER_DN
        self.configuration.site_enable_migadmin = True
        self.configuration.admin_list = [TEST_USER_DN]
        self.configuration.site_migadmin_view_access = ["ANY"]
        self.configuration.site_migadmin_act_access = ["ANY"]

    def test_migadmin_disabled_site_migadmin(self):
        self.configuration.site_enable_migadmin = False
        payload = {}

        output_objects, status = backend_main(
            TEST_USER_DN,
            payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.CLIENT_ERROR)

        # Check expected error messages
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 1)
        self.assertIn("text", error_objects[0])
        text_object = error_objects[0]["text"]
        expected_response_msg = "Site administration not enabled"
        self.assertIn(expected_response_msg, text_object)

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 1)

    @unittest.skip("TODO: fix CI installation of pgrep and re-enable")
    def test_show_default_user_migadmin(self):
        payload = {}

        output_objects, status = backend_main(
            TEST_USER_DN,
            payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.OK)

        # Check expected error messages
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 0)

        # Check expected header messages
        header_objects = filter_output_objects(
            output_objects, with_object_type="header"
        )
        self.assertEqual(len(header_objects), 1)

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 12)

    def test_migadmin_without_access_fails(self):
        payload = {}
        self.configuration.admin_list = []
        output_objects, status = backend_main(
            TEST_USER_DN,
            payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.CLIENT_ERROR)

        # Check expected error messages
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 1)
        self.assertIn("text", error_objects[0])
        text_object = error_objects[0]["text"]
        expected_response_msg = "MUST be a site admin"
        self.assertIn(expected_response_msg, text_object)

        # Check expected header messages
        header_objects = filter_output_objects(
            output_objects, with_object_type="header"
        )
        self.assertEqual(len(header_objects), 0)

        # Check expected title contents
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 1)

    def test_migadmin_view_with_auth_access_mismatch_fails(self):
        payload = {}
        self.configuration.site_migadmin_view_access = ["OpenID Connect"]
        self.configuration.site_migadmin_act_access = ["OpenID Connect"]
        output_objects, status = backend_main(
            TEST_USER_DN,
            payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.CLIENT_ERROR)

        # Check expected error messages
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 1)
        self.assertIn("text", error_objects[0])
        text_object = error_objects[0]["text"]
        expected_response_msg = "Admin view access requires"
        self.assertIn(expected_response_msg, text_object)

        # Check expected header messages
        header_objects = filter_output_objects(
            output_objects, with_object_type="header"
        )
        self.assertEqual(len(header_objects), 0)

        # Check expected title contents
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 1)

    def test_migadmin_with_invalid_action_fails(self):
        payload = {"action": ["INVALID"]}
        output_objects, status = backend_main(
            TEST_USER_DN,
            payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.SYSTEM_ERROR)

        # Check expected error messages
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 1)
        self.assertIn("text", error_objects[0])
        text_object = error_objects[0]["text"]
        expected_response_msg = "Invalid action"
        self.assertIn(expected_response_msg, text_object)

        # Check expected header messages
        header_objects = filter_output_objects(
            output_objects, with_object_type="header"
        )
        self.assertEqual(len(header_objects), 0)

        # Check expected title contents
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 1)


# TODO: add additional tests to cover other uses

if __name__ == "__main__":
    testmain()
