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
from mig.shared.base import client_id_dir, client_dir_id, get_site_base_url, \
    mask_creds
from tests.support import MigTestCase, testmain
from tests.support.configsupp import FakeConfiguration
from mig.shared.defaults import csrf_field

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

    def test_client_dir_id_basic(self):
        """Test basic client_dir_id conversion"""
        input_dir = "+C=DK+CN=John_Doe"
        expected_id = "/C=DK/CN=John Doe"
        self.assertEqual(client_dir_id(input_dir), expected_id)

    def test_client_dir_id_mixed_fields(self):
        """Test conversion with multiple field types"""
        input_dir = "+CN=Alice+O=Open_Science+OU=Research_Team+emailAddress=alice@example.com"
        expected_id = "/CN=Alice/O=Open Science/OU=Research Team/emailAddress=alice@example.com"
        self.assertEqual(client_dir_id(input_dir), expected_id)

    def test_client_dir_id_underscore_to_space(self):
        """Test underscore replacement in remapped fields"""
        input_dir = "+O=Data_Center_1+CN=Bob_Johnson"
        expected_id = "/O=Data Center 1/CN=Bob Johnson"
        self.assertEqual(client_dir_id(input_dir), expected_id)

    def test_client_dir_id_special_chars(self):
        """Test preservation of special characters"""
        input_dir = "+CN=Müller+O=Entrepôt"
        expected_id = "/CN=Müller/O=Entrepôt"
        self.assertEqual(client_dir_id(input_dir), expected_id)

    def test_client_dir_id_edge_cases(self):
        """Test edge case handling"""
        self.assertEqual(client_dir_id(""), "")
        self.assertEqual(client_dir_id("+CN=Single"), "/CN=Single")

    def test_client_dir_id_underscore_handling(self):
        """Test underscore replacement in remapped fields and preservation elsewhere."""
        input_dir = "+OU=Dev_Team+emailAddress=user_name@site.com"
        expected_id = "/OU=Dev Team/emailAddress=user_name@site.com"
        self.assertEqual(client_dir_id(input_dir), expected_id)

    def test_get_site_base_url_prefers_https(self):
        """Test get_site_base_url prefers HTTPS when available."""
        config = FakeConfiguration()
        config.migserver_http_url = "http://example.com"
        config.migserver_https_url = "https://example.com"
        self.assertEqual(get_site_base_url(config), "https://example.com")

    def test_get_site_base_url_fallback_to_http(self):
        """Test get_site_base_url falls back to HTTP when HTTPS is not available."""
        config = FakeConfiguration()
        config.migserver_http_url = "http://example.com"
        config.migserver_https_url = ""  # Not available
        self.assertEqual(get_site_base_url(config), "http://example.com")

    def test_mask_creds_default_masking(self):
        """Test mask_creds with default fields and value."""
        user_dict = {
            'username': 'testuser',
            'password': 'secret_password',
            'password_hash': 'a_long_hash',
            'email': 'user@example.com'
        }
        masked = mask_creds(user_dict)
        self.assertEqual(masked['username'], 'testuser')
        self.assertEqual(masked['password'], '**HIDDEN**')
        self.assertEqual(masked['password_hash'], '**HIDDEN**')
        self.assertEqual(masked['email'], 'user@example.com')

    def test_mask_creds_original_dict_unmodified(self):
        """Test that mask_creds does not modify the original dictionary."""
        original_dict = {'password': 'secret'}
        mask_creds(original_dict)
        self.assertEqual(original_dict['password'], 'secret')

    def test_mask_creds_custom_fields_and_value(self):
        """Test mask_creds with custom fields and a custom masked value."""
        user_dict = {'api_key': '12345', 'session_id': 'abcde'}
        masked = mask_creds(
            user_dict,
            mask_fields=['api_key'],
            masked_value='[REDACTED]'
        )
        self.assertEqual(masked['api_key'], '[REDACTED]')
        self.assertEqual(masked['session_id'], 'abcde')

    def test_mask_creds_with_subst_map(self):
        """Test mask_creds with the subst_map for regex substitution."""
        user_dict = {
            'connection_string': 'user:password@db.example.com',
            'other_field': 'some_value'
        }
        subst_map = {
            'connection_string': (r':.*@', r':<masked>@')
        }
        masked = mask_creds(user_dict, subst_map=subst_map)
        self.assertEqual(masked['connection_string'], 'user:<masked>@db.example.com')
        self.assertEqual(masked['other_field'], 'some_value')

    def test_mask_creds_no_maskable_fields(self):
        """Test mask_creds with a dictionary containing no maskable fields."""
        user_dict = {'username': 'test', 'role': 'user'}
        masked = mask_creds(user_dict)
        self.assertEqual(user_dict, masked)

    def test_mask_creds_empty_dict(self):
        """Test mask_creds with an empty dictionary."""
        self.assertEqual(mask_creds({}), {})

    def test_mask_creds_csrf_field(self):
        """Test that the default csrf_field is masked."""
        user_dict = {csrf_field: 'some_csrf_token', 'other': 'value'}
        masked = mask_creds(user_dict)
        self.assertEqual(masked[csrf_field], '**HIDDEN**')
        self.assertEqual(masked['other'], 'value')

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
