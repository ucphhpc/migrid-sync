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

"""Unit tests of the MiG functionality file implementing the datatransfer backend"""

from __future__ import print_function
import os

import mig.shared.returnvalues as returnvalues
from mig.shared.defaults import CSRF_MINIMAL
from mig.shared.base import client_id_dir
from mig.shared.functionality.datatransfer import _main as submain, main as realmain

from tests.support import (
    MigTestCase,
    testmain,
    temppath,
    ensure_dirs_exist,
)


def create_http_environ(configuration):
    """Small helper that can create a minimum viable environ dict suitable
    for passing to http-facing code for the supplied configuration.
    """

    environ = {}
    environ["MIG_CONF"] = configuration.config_file
    environ["HTTP_HOST"] = "localhost"
    environ["PATH_INFO"] = "/"
    environ["REMOTE_ADDR"] = "127.0.0.1"
    environ["SCRIPT_URI"] = "".join(
        ("https://", environ["HTTP_HOST"], environ["PATH_INFO"])
    )
    return environ


def _only_output_objects(output_objects, with_object_type=None):
    return [o for o in output_objects if o["object_type"] == with_object_type]


class MigSharedFunctionalityDataTransfer(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    TEST_CLIENT_ID = (
        "/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com"
    )

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        # ensure a user home directory for our test user
        conf_user_home = self.configuration.user_home[:-1]
        test_client_dir = client_id_dir(self.TEST_CLIENT_ID)
        test_user_dir = os.path.join(conf_user_home, test_client_dir)

        # ensure a user db that includes our test user
        conf_user_db_home = ensure_dirs_exist(self.configuration.user_db_home)
        temppath(conf_user_db_home, self)
        prepared_fixture = self.prepareFixtureAssert(
            "MiG-users.db--example",
            fixture_format="binary",
        )

        prepared_fixture.copy_as_temp(prefix=conf_user_db_home)

        # create the test user home directory
        self.test_user_dir = ensure_dirs_exist(test_user_dir)
        temppath(self.test_user_dir, self)

        # ensure the user_settings home directory for our test user
        conf_user_settings_home = ensure_dirs_exist(self.configuration.user_settings)
        temppath(conf_user_settings_home, self)
        test_user_settings_dir = os.path.join(conf_user_settings_home, test_client_dir)
        ensure_dirs_exist(test_user_settings_dir)

        self.test_environ = create_http_environ(self.configuration)

    def test_default_disabled_site_transfer(self):
        self.assertFalse(self.configuration.site_enable_transfers)

        result = realmain(self.TEST_CLIENT_ID, {})
        (output_objects, status) = result
        self.assertEqual(status, returnvalues.OK)

        text_objects = _only_output_objects(output_objects, with_object_type="text")
        self.assertEqual(len(text_objects), 1)
        self.assertIn("text", text_objects[0])
        text_object = text_objects[0]["text"]
        expected_response_msg = "Data import/export is disabled on this site."
        self.assertIn(expected_response_msg, text_object)

    def test_show_action_enabled_site_transfer(self):
        payload = {"action": ["show"]}
        self.configuration.site_enable_transfers = True

        (output_objects, status) = submain(
            self.configuration,
            self.logger,
            client_id=self.TEST_CLIENT_ID,
            user_arguments_dict=payload,
            environ=self.test_environ,
        )
        self.assertEqual(status, returnvalues.OK)

        # We don't expect any text messages here
        text_objects = _only_output_objects(output_objects, with_object_type="text")
        self.assertEqual(len(text_objects), 0)

    def test_deltransfer_without_transfer_id(self):
        non_existing_transfer_id = "non-existing-transfer-id"
        payload = {"action": ["deltransfer"], "transfer_id": [non_existing_transfer_id]}
        self.configuration.site_enable_transfers = True
        self.configuration.site_csrf_protection = CSRF_MINIMAL
        self.test_environ["REQUEST_METHOD"] = "post"

        (output_objects, status) = submain(
            self.configuration,
            self.logger,
            client_id=self.TEST_CLIENT_ID,
            user_arguments_dict=payload,
            environ=self.test_environ,
        )
        self.assertEqual(status, returnvalues.CLIENT_ERROR)

        error_text_objects = _only_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_text_objects), 1)
        self.assertEqual(
            error_text_objects[0]["text"], "existing transfer_id is required for delete"
        )

    def test_redotransfer_without_transfer_id(self):
        non_existing_transfer_id = "non-existing-transfer-id"
        payload = {
            "action": ["redotransfer"],
            "transfer_id": [non_existing_transfer_id],
        }
        self.configuration.site_enable_transfers = True
        self.configuration.site_csrf_protection = CSRF_MINIMAL
        self.test_environ["REQUEST_METHOD"] = "post"

        (output_objects, status) = submain(
            self.configuration,
            self.logger,
            client_id=self.TEST_CLIENT_ID,
            user_arguments_dict=payload,
            environ=self.test_environ,
        )
        self.assertEqual(status, returnvalues.CLIENT_ERROR)

        error_text_objects = _only_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_text_objects), 1)
        self.assertEqual(
            error_text_objects[0]["text"],
            "existing transfer_id is required for reschedule",
        )


# TODO, add additional tests that succesfully makes data transfers across a range of protocols

if __name__ == "__main__":
    testmain()
