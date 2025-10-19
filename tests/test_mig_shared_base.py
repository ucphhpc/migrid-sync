# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_base - unit tests for shared base helpers
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Unit tests for mig.shared.base module"""

import sys
from mig.shared.base import client_id_dir
from tests.support import MigTestCase, testmain

from mig.shared.base import main as base_main


class TestMigSharedBase(MigTestCase):
    """Test mig.shared.base functions"""

    def test_client_id_dir_basic(self):
        """Test basic client_id_dir conversion"""
        input_id = "/C=DK/CN=John Doe"
        expected = "+C=DK+CN=John_Doe"
        self.assertEqual(client_id_dir(input_id), expected)

    def test_client_id_dir_mixed_fields(self):
        """Test conversion with multiple field types"""
        input_id = "/CN=Alice/O=Open Science/OU=Research Team/emailAddress=alice@example.com"
        expected = "+CN=Alice+O=Open_Science+OU=Research_Team+emailAddress=alice@example.com"
        self.assertEqual(client_id_dir(input_id), expected)

    def test_client_id_dir_spaces(self):
        """Test space replacement in remapped fields"""
        input_id = "/O=Data Center 1/CN=Bob Johnson"
        expected = "+O=Data_Center_1+CN=Bob_Johnson"
        self.assertEqual(client_id_dir(input_id), expected)

    def test_client_id_dir_special_chars(self):
        """Test preservation of special characters"""
        input_id = "/CN=Müller/O=Entrepôt"
        expected = "+CN=Müller+O=Entrepôt"
        self.assertEqual(client_id_dir(input_id), expected)

    def test_client_id_dir_edge_cases(self):
        """Test edge case handling"""
        self.assertEqual(client_id_dir(""), "")
        self.assertEqual(client_id_dir("/CN=Single"), "+CN=Single")

    def test_client_id_dir_preserve_underscores(self):
        """Test underscore preservation in all fields"""
        input_id = "/OU=Dev_Team/emailAddress=user_name@site.com"
        expected = "+OU=Dev_Team+emailAddress=user_name@site.com"
        self.assertEqual(client_id_dir(input_id), expected)

    def test_existing_main(self):
        """Run built-in self-tests and check output"""
        def raise_on_error_exit(exit_code):
            if exit_code != 0:
                if raise_on_error_exit.last_print is not None:
                    identifying_message = raise_on_error_exit.last_print
                else:
                    identifying_message = 'unknown'
                raise AssertionError(
                    'failure in unittest/testcore: %s' % (identifying_message,))
        raise_on_error_exit.last_print = None

        def record_last_print(value):
            raise_on_error_exit.last_print = value

        base_main(_exit=raise_on_error_exit, _print=record_last_print)


if __name__ == '__main__':
    testmain()
