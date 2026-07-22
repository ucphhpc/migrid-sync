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

# Imports required for the unit test wrapping
import mig.shared.returnvalues as returnvalues

# Imports of the code under test
from mig.shared.functionality.docs import main as backend_main

# Imports required for the unit tests themselves
from tests.support import (
    MigTestCase,
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
        self.test_environ = create_http_environ(
            self.configuration, "wsgi-bin/docs.py"
        )
        self.configuration.site_enable_styling = False
        self.configuration.site_enable_widgets = False

    def test_show_default_anonymous_site_docs(self):
        payload = {"show": [""]}

        output_objects, status = backend_main(
            "",
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

        # Check expected title contents
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)
        self.assertTrue(title_objects[0]["skipmenu"])
        self.assertTrue(title_objects[0]["skipuserprofile"])
        # No bling here for anon users
        self.assertTrue(title_objects[0]["skipuserstyle"])
        self.assertTrue(title_objects[0]["skipwidgets"])

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 2)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 6)

    def test_show_default_anonymous_site_docs_with_bling(self):
        payload = {"show": [""]}
        self.configuration.site_enable_styling = True
        self.configuration.site_enable_widgets = True

        output_objects, status = backend_main(
            "",
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

        # Check expected title contents
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)
        self.assertTrue(title_objects[0]["skipmenu"])
        self.assertTrue(title_objects[0]["skipuserprofile"])
        # No bling here for anon users
        self.assertTrue(title_objects[0]["skipuserstyle"])
        self.assertTrue(title_objects[0]["skipwidgets"])

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 2)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 6)

    def test_show_default_site_docs(self):
        payload = {"show": [""]}

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

        # Check expected title contents
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)
        self.assertFalse(title_objects[0]["skipmenu"])
        self.assertFalse(title_objects[0]["skipuserprofile"])
        # Only bling here if enabled in conf
        self.assertNotEqual(
            title_objects[0]["skipuserstyle"],
            self.configuration.site_enable_styling,
        )
        self.assertNotEqual(
            title_objects[0]["skipwidgets"],
            self.configuration.site_enable_widgets,
        )

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 2)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 6)

    def test_show_default_site_docs_with_bling(self):
        self.configuration.site_enable_styling = True
        self.configuration.site_enable_widgets = True
        payload = {"show": [""]}

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

        # Check expected title contents
        title_objects = filter_output_objects(
            output_objects, with_object_type="title"
        )
        self.assertEqual(len(title_objects), 1)
        self.assertFalse(title_objects[0]["skipmenu"])
        self.assertFalse(title_objects[0]["skipuserprofile"])
        # Only bling here if enabled in conf
        self.assertNotEqual(
            title_objects[0]["skipuserstyle"],
            self.configuration.site_enable_styling,
        )
        self.assertNotEqual(
            title_objects[0]["skipwidgets"],
            self.configuration.site_enable_widgets,
        )

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertEqual(len(text_objects), 2)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 6)

    def test_show_default_credits(self):
        payload = {"show": ["credits"]}

        output_objects, status = backend_main(
            client_id=TEST_USER_DN,
            user_arguments_dict=payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.OK)

        # Check expected error messages
        error_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_objects), 0)

        # Check expected text messages
        text_objects = filter_output_objects(
            output_objects, with_object_type="text"
        )
        self.assertTrue(len(text_objects) >= 20)

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 3)

        # Check expected links
        link_objects = filter_output_objects(
            output_objects, with_object_type="link"
        )
        self.assertTrue(len(link_objects) >= 20)

    def test_show_cracklib_credits_when_enabled(self):
        self.configuration.site_password_cracklib = True
        # Needs one service with password login to trigger conditional
        self.configuration.site_enable_sftp = True
        payload = {"show": ["credits"]}

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

        # Check expected links
        link_objects = filter_output_objects(
            output_objects, with_object_type="link"
        )
        self.assertTrue(len(link_objects) >= 20)
        self.assertTrue(
            [i for i in link_objects if "cracklib" in i["title"].lower()]
        )

    def test_hide_cracklib_credits_when_disabled(self):
        self.configuration.site_password_cracklib = False
        # Needs one service with password login to trigger conditional
        self.configuration.site_enable_sftp = True
        payload = {"show": ["credits"]}

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

        # Check expected links
        link_objects = filter_output_objects(
            output_objects, with_object_type="link"
        )
        self.assertTrue(len(link_objects) >= 20)
        self.assertFalse(
            [i for i in link_objects if "cracklib" in i["title"].lower()]
        )

    def test_hide_cracklib_credits_when_unused(self):
        # Hidden if no password login service enabled
        self.configuration.site_password_cracklib = True
        self.configuration.site_enable_sftp = False
        payload = {"show": ["credits"]}

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

        # Check expected links
        link_objects = filter_output_objects(
            output_objects, with_object_type="link"
        )
        self.assertTrue(len(link_objects) >= 20)
        self.assertFalse(
            [i for i in link_objects if "cracklib" in i["title"].lower()]
        )

    def test_show_default_credits_no_longer_has_broken_html_br_tag(self):
        payload = {"show": ["credits"]}

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

        # Check expected html snippets
        html_objects = filter_output_objects(
            output_objects, with_object_type="html_form"
        )
        self.assertEqual(len(html_objects), 3)
        self.assertFalse([i for i in html_objects if "<br \>" in i["text"]])


# TODO: add additional tests to cover other uses

if __name__ == "__main__":
    testmain()
