# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_cat - unit test of the corresponding mig module
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

"""Unit tests of the MiG functionality file implementing the cat backend"""

from __future__ import print_function

import os
import shutil

# Imports required for the unit test wrapping
import mig.shared.returnvalues as returnvalues

# Imports of the code under test
from mig.shared.functionality.cat import main as backend_main

# Imports required for the unit tests themselves
from tests.support import (
    TEST_DATA_DIR,
    MigTestCase,
    testmain,
)
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin
from tests.support.wsgisupp import create_http_environ, filter_output_objects


class MigSharedFunctionalityCat(MigTestCase, UserAssertMixin):
    """Wrap unit tests for the corresponding module"""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self.test_user_dir = self._provision_test_user(self, TEST_USER_DN)
        self.test_environ = create_http_environ(
            self.configuration, "wsgi-bin/cat.py"
        )

    def test_file_serving_a_single_file_match(self):
        test_data = "424242"
        with open(os.path.join(self.test_user_dir, "foobar.txt"), "w") as fd:
            fd.write(test_data)
        payload = {
            "path": ["foobar.txt"],
        }

        output_objects, status = backend_main(
            TEST_USER_DN,
            payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.OK)

        # NOTE: start entry with headers, title, header and actual content
        self.assertEqual(len(output_objects), 3)
        file_output_objects = filter_output_objects(
            output_objects, with_object_type="file_output"
        )
        self.assertEqual(len(file_output_objects), 1)
        relevant_obj = file_output_objects[0]
        self.assertEqual(len(relevant_obj["lines"]), 1)
        self.assertEqual(relevant_obj["lines"][0], test_data)

    def test_file_serving_at_limit(self):
        test_binary_file = os.path.realpath(
            os.path.join(TEST_DATA_DIR, "loading.gif")
        )
        test_binary_file_size = os.stat(test_binary_file).st_size
        with open(test_binary_file, "rb") as fh_test_file:
            test_binary_file_data = fh_test_file.read()
        shutil.copyfile(
            test_binary_file, os.path.join(self.test_user_dir, "loading.gif")
        )
        payload = {
            "output_format": ["file"],
            "path": ["loading.gif"],
        }

        self.configuration.wwwserve_max_bytes = test_binary_file_size

        output_objects, status = backend_main(
            TEST_USER_DN,
            payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.OK)

        # NOTE: start entry with headers, title and actual content
        self.assertEqual(len(output_objects), 3)
        file_output_objects = filter_output_objects(
            output_objects, with_object_type="file_output"
        )
        self.assertEqual(len(file_output_objects), 1)
        relevant_obj = file_output_objects[0]
        self.assertEqual(len(relevant_obj["lines"]), 1)
        self.assertEqual(relevant_obj["lines"][0], test_binary_file_data)

    def test_file_serving_over_limit_without_storage_protocols(self):
        test_binary_file = os.path.realpath(
            os.path.join(TEST_DATA_DIR, "loading.gif")
        )
        test_binary_file_size = os.stat(test_binary_file).st_size
        with open(test_binary_file, "rb") as fh_test_file:
            _ = fh_test_file.read()
        shutil.copyfile(
            test_binary_file, os.path.join(self.test_user_dir, "loading.gif")
        )
        payload = {
            "output_format": ["file"],
            "path": ["loading.gif"],
        }

        # NOTE: override default storage_protocols to empty in this test
        self.configuration.storage_protocols = []
        self.configuration.wwwserve_max_bytes = test_binary_file_size - 1

        output_objects, status = backend_main(
            TEST_USER_DN,
            payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.REJECT_PROCESSING_ERROR)

        # NOTE: start entry with headers, title and actual error message
        self.assertEqual(len(output_objects), 3)
        error_text_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_text_objects), 1)
        self.assertEqual(
            error_text_objects[0]["text"],
            "Site configuration prevents web serving contents "
            "bigger than 3896 bytes",
        )

    def test_file_serving_over_limit_with_storage_protocols_sftp(self):
        test_binary_file = os.path.realpath(
            os.path.join(TEST_DATA_DIR, "loading.gif")
        )
        test_binary_file_size = os.stat(test_binary_file).st_size
        with open(test_binary_file, "rb") as fh_test_file:
            _ = fh_test_file.read()
        shutil.copyfile(
            test_binary_file, os.path.join(self.test_user_dir, "loading.gif")
        )
        payload = {
            "output_format": ["file"],
            "path": ["loading.gif"],
        }

        self.configuration.storage_protocols = ["sftp"]
        self.configuration.wwwserve_max_bytes = test_binary_file_size - 1

        output_objects, status = backend_main(
            TEST_USER_DN,
            payload,
            environ=self.test_environ,
            init_main_res=(self.configuration, self.logger, None, None),
        )
        self.assertEqual(status, returnvalues.REJECT_PROCESSING_ERROR)

        # NOTE: start entry with headers, title and actual error message
        self.assertEqual(len(output_objects), 3)
        error_text_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        self.assertEqual(len(error_text_objects), 1)
        relevant_obj = error_text_objects[0]
        self.assertEqual(
            relevant_obj["text"],
            "Site configuration prevents web serving contents "
            "bigger than 3896 bytes - please use better "
            "alternatives (SFTP) to retrieve large data",
        )

    def test_main_passes_environ(self):
        payload = {}
        try:
            output_objects, status = backend_main(
                TEST_USER_DN,
                payload,
                environ=self.test_environ,
                init_main_res=(self.configuration, self.logger, None, None),
            )
        except Exception as unexpectedexc:
            raise AssertionError(
                "saw unexpected exception: %s" % (unexpectedexc,)
            )

        self.assertEqual(status, returnvalues.CLIENT_ERROR)

        # NOTE: start entry with headers, title, header, three actual error
        #       messages and finally a Go back link.
        self.assertEqual(len(output_objects), 6)
        error_text_objects = filter_output_objects(
            output_objects, with_object_type="error_text"
        )
        relevant_obj = error_text_objects[2]
        self.assertEqual(
            relevant_obj["text"],
            "Input arguments were rejected - not allowed for this script!",
        )


if __name__ == "__main__":
    testmain()
