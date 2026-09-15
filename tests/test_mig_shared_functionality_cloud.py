# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_cloud - unit test of the corresponding mig module
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

"""Unit tests of the MiG functionality file implementing the cloud backend"""

from __future__ import print_function

# Imports required for the unit test wrapping
import mig.shared.returnvalues as returnvalues

# Imports of the code under test
from mig.shared.functionality.cloud import main as backend_main

# Imports required for the unit tests themselves
from tests.support import (
    MigTestCase,
    testmain,
)
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin
from tests.support.wsgisupp import create_http_environ, filter_output_objects


class MigSharedFunctionalityCloud(MigTestCase, UserAssertMixin):
    """Wrap unit tests for the corresponding module"""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self.test_user_dir = self._provision_test_user(self, TEST_USER_DN)
        self.test_environ = create_http_environ(
            self.configuration, "wsgi-bin/cloud.py"
        )
        self.configuration.site_enable_cloud = True
        self.configuration.site_cloud_access = [("distinguished_name", ".*")]

    def test_cloud_disabled_site_cloud(self):
        self.configuration.site_enable_cloud = False
        payload = {}

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
        expected_response_msg = "The cloud service is not enabled on this site"
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
        self.assertEqual(len(html_objects), 0)

    def test_show_default_user_cloud(self):
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
        self.assertEqual(len(html_objects), 4)

    def test_cloud_no_access_fails(self):
        self.configuration.site_cloud_access = [("role", "privileged")]
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
        relevant_obj = error_objects[0]
        self.assertIn(
            "You don't have permission to access the cloud",
            relevant_obj["text"],
        )

        # Check expected header messages
        header_objects = filter_output_objects(
            output_objects, with_object_type="header"
        )
        self.assertEqual(len(header_objects), 0)

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 0)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 0)

    def test_show_unavailable_cloud_fails(self):
        self.configuration.cloud_services = [
            {
                "service_name": "TestCloud",
                "service_title": "Test Cloud Title",
                "service_desc": "Test Cloud Info",
                "service_rules_of_conduct": "Test Cloud Rules of Conduct",
            }
        ]
        payload = {}

        output_objects, status = None, None
        with self.assertLogs(level="ERROR") as log_capture:
            output_objects, status = backend_main(
                TEST_USER_DN,
                payload,
                environ=self.test_environ,
                init_main_res=(self.configuration, self.logger, None, None),
            )
        if log_capture.output:
            # NOTE: we may end up here if openstackclient is unavailable
            self.assertTrue(
                any(
                    "require openstackclient" in msg
                    for msg in log_capture.output
                )
            )
            self.assertEqual(status, returnvalues.SYSTEM_ERROR)
        else:
            self.assertEqual(status, returnvalues.CLIENT_ERROR)

        # Check expected error messages
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 1)
        relevant_obj = error_objects[0]
        if status == returnvalues.CLIENT_ERROR:
            self.assertIn("Failed to connect to cloud", relevant_obj["text"])
        else:
            self.assertIn("is currently unavailable", relevant_obj["text"])

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
        self.assertEqual(len(html_objects), 8)


# TODO: add additional tests to cover other uses

if __name__ == "__main__":
    testmain()
