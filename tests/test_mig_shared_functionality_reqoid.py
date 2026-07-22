# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_reqoid - unit test of the corresponding mig module
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

"""Unit tests of the MiG functionality file implementing the reqoid backend"""

from __future__ import print_function

import unittest

# Imports required for the unit test wrapping
import mig.shared.returnvalues as returnvalues

# Imports of the code under test
from mig.shared.functionality.reqoid import main as backend_main

# Imports required for the unit tests themselves
from tests.support import (
    MigTestCase,
    ensure_dirs_exist,
    testmain,
)
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin
from tests.support.wsgisupp import create_http_environ, filter_output_objects

TEST_USER_EMAIL = TEST_USER_DN.split("/emailAddress=", 1)[-1]


class MigSharedFunctionalityReqoid(MigTestCase, UserAssertMixin):
    """Wrap unit tests for the corresponding module"""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        ensure_dirs_exist(self.configuration.resource_home)
        ensure_dirs_exist(self.configuration.vgrid_home)
        ensure_dirs_exist(self.configuration.mig_system_files)
        self.test_user_dir = self._provision_test_user(self, TEST_USER_DN)
        self.test_environ = create_http_environ(
            self.configuration, "wsgi-bin/reqoid.py"
        )

    def test_reqoid_disabled_site_openid(self):
        self.assertFalse(self.configuration.site_enable_openid)
        payload = {}

        result = backend_main(TEST_USER_DN, payload, self.test_environ)
        output_objects, status = result
        self.assertEqual(status, returnvalues.SYSTEM_ERROR)

        # We expect one error message here
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 1)
        self.assertIn("text", error_objects[0])
        text_object = error_objects[0]["text"]
        expected_response_msg = "Local OpenID login is not enabled on this site"
        self.assertIn(expected_response_msg, text_object)

        # We don't expect any text message here
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # We don't expect any html snippets here
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 0)

    @unittest.skip("TODO: fix missing script init in backend and re-enable")
    def test_show_default_anonymous_user_reqoid(self):
        self.configuration.site_enable_openid = True
        self.configuration.site_signup_methods = ["migoid"]
        payload = {}

        output_objects, status = backend_main(
            client_id="",
            user_arguments_dict=payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.OK)

        # We don't expect any error messages here
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 0)

        # We expect title without menu and user specifics here
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)
        self.assertTrue(title_objects[0]["skipmenu"])

        # We don't expect any text messages here
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # We expect 2 html snippets here and blank form
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 2)
        relevant_obj = html_objects[1]
        self.assertIn("Please enter your information", relevant_obj["text"])
        self.assertNotIn("value='%s'" % TEST_USER_EMAIL, relevant_obj["text"])

    @unittest.skip("TODO: fix missing script init in backend and re-enable")
    def test_show_url_prefill_user_reqoid(self):
        self.configuration.site_enable_openid = True
        self.configuration.site_signup_methods = ["migoid"]
        payload = {"email": [TEST_USER_EMAIL]}

        output_objects, status = backend_main(
            client_id="",
            user_arguments_dict=payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.OK)

        # We don't expect any error messages here
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 0)

        # We expect title without menu and user specifics here
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)
        self.assertTrue(title_objects[0]["skipmenu"])

        # We don't expect any text messages here
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # We expect 2 html snippets here and blank form
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 2)
        relevant_obj = html_objects[1]
        self.assertIn("Please enter your information", relevant_obj["text"])
        self.assertIn("value='%s'" % TEST_USER_EMAIL, relevant_obj["text"])

    @unittest.skip("TODO: fix missing script init in backend and re-enable")
    def test_show_default_authenticated_user_reqoid(self):
        self.configuration.site_enable_openid = True
        self.configuration.site_signup_methods = ["migoid"]
        payload = {}

        output_objects, status = backend_main(
            client_id=TEST_USER_DN,
            user_arguments_dict=payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.OK)

        # We don't expect any error messages here
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 0)

        # We expect title without menu and user specifics here
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)
        self.assertTrue(title_objects[0]["skipmenu"])

        # We don't expect any text messages here
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # We expect 3 html snippets here and pre-filled form for ID
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 3)
        relevant_obj = html_objects[1]
        self.assertIn(
            "you already have valid MiG credentials", relevant_obj["text"]
        )
        relevant_obj = html_objects[2]
        self.assertIn("value='%s'" % TEST_USER_EMAIL, relevant_obj["text"])


# TODO: add additional tests to cover other uses
if __name__ == "__main__":
    testmain()
