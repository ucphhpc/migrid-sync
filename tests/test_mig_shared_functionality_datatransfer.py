# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_datatransfer - unit test of the corresponding mig module
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
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin
from tests.support.wsgisupp import create_http_environ, filter_output_objects


class MigSharedFunctionalityDataTransfer(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self.test_user_dir = self._provision_test_user(self, TEST_USER_DN)
        self.test_environ = create_http_environ(self.configuration)

    def test_default_disabled_site_transfer(self):
        self.assertFalse(self.configuration.site_enable_transfers)

        result = realmain(TEST_USER_DN, {}, self.test_environ)
        (output_objects, status) = result
        self.assertEqual(status, returnvalues.OK)

        text_objects = filter_output_objects(
            output_objects, with_object_type="text")
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
            client_id=TEST_USER_DN,
            user_arguments_dict=payload,
            environ=self.test_environ,
        )
        self.assertEqual(status, returnvalues.OK)

        # We don't expect any text messages here
        text_objects = filter_output_objects(
            output_objects, with_object_type="text")
        self.assertEqual(len(text_objects), 0)

    def test_deltransfer_without_transfer_id(self):
        non_existing_transfer_id = "non-existing-transfer-id"
        payload = {"action": ["deltransfer"],
                   "transfer_id": [non_existing_transfer_id]}
        self.configuration.site_enable_transfers = True
        self.configuration.site_csrf_protection = CSRF_MINIMAL
        self.test_environ["REQUEST_METHOD"] = "post"

        (output_objects, status) = submain(
            self.configuration,
            self.logger,
            client_id=TEST_USER_DN,
            user_arguments_dict=payload,
            environ=self.test_environ,
        )
        self.assertEqual(status, returnvalues.CLIENT_ERROR)

        error_text_objects = filter_output_objects(
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
            client_id=TEST_USER_DN,
            user_arguments_dict=payload,
            environ=self.test_environ,
        )
        self.assertEqual(status, returnvalues.CLIENT_ERROR)

        error_text_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_text_objects), 1)
        self.assertEqual(
            error_text_objects[0]["text"],
            "existing transfer_id is required for reschedule",
        )


# TODO: extend tests to cover data transfers across a range of protocols

if __name__ == "__main__":
    testmain()
