# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_base - unit tests for shared base helpers
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
# -- END_HEADER ---
#

"""Unit tests for mig.shared.base module"""

import os
import sys
import unittest

# Imports of the code under test
from mig.shared.base import allow_script, auth_type_description, brief_list, \
    canonical_user, canonical_user_with_peers, client_alias, client_dir_id, \
    client_id_dir, distinguished_name_to_user, expand_openid_alias, \
    extract_field, fill_distinguished_name, fill_user, generate_https_urls, \
    get_client_id, get_short_id, get_site_base_url, get_user_id, get_xgi_bin, \
    hexlify, invisible_dir, invisible_file, invisible_path, is_gdp_user, \
    legacy_main, mask_creds, pretty_format_user, requested_backend, \
    requested_page, requested_url_base, string_snippet, \
    unhexlify, user_base_dir, valid_dir_input, verify_local_url
# Imports required for the unit test wrapping
from mig.shared.defaults import cert_field_order, csrf_field, \
    gdp_distinguished_field, valid_gdp_anon_scripts, valid_gdp_auth_scripts
# Imports required for the unit tests themselves
from tests.support import FakeConfiguration, MigTestCase, testmain

TEST_USER_ID = "/C=DK/O=Test Org/CN=John Doe/emailAddress=john@doe.org"
TEST_USER_DIR = "+C=DK+O=Test_Org+CN=John_Doe+emailAddress=john@doe.org"
TEST_EMAIL = TEST_ALIAS = "john@doe.org"
TEST_FULL_NAME = "John Doe"
TEST_ORGANIZATION = "Test Org"
TEST_COUNTRY = "DK"
TEST_STATE = 'VT'
TEST_CLIENT_ALIAS = 'L0NfREsvT19UZXN0IE9yZy9DTl9Kb2huIERvZS9lbWFpbEFkZHJlc3Nfam9obkBkb2Uub3Jn'
GDP_USER_ID = "/C=DK/CN=John Doe/emailAddress=john@doe.org/GDP=projectx"
GDP_USER_DIR = "+C=DK+CN=John_Doe+emailAddress=john@doe.org+GDP=projectx"
GDP_EMAIL = GDP_ALIAS = "john@doe.org@projectx"


class TestMigSharedBase(MigTestCase):
    """Test mig.shared.base functions"""

    def _provide_configuration(self):
        """Set up isolated test configuration and logger for the tests"""
        return 'testconfig'

    def before_each(self):
        """Setup fake configuration before each test."""
        self.configuration.migserver_http_url = "http://mig.plain"
        self.configuration.migserver_https_url = "https://mig.crypt"
        self.configuration.migserver_public_url = "https://mig.pub"
        self.configuration.migserver_public_alias_url = "https://mig.pub.alias"
        self.configuration.migserver_https_mig_cert_url = "https://mig.cert"
        self.configuration.migserver_https_ext_cert_url = "https://ext.cert"
        self.configuration.migserver_https_mig_oid_url = "https://mig.oid"
        self.configuration.migserver_https_ext_oid_url = "https://ext.oid"
        self.configuration.migserver_https_mig_oidc_url = "https://mig.oidc"
        self.configuration.migserver_https_ext_oidc_url = "https://ext.oidc"
        self.configuration.migserver_https_sid_url = "https://mig.sid"
        self.configuration.site_enable_wsgi = False
        self.configuration.site_login_methods = []
        self.configuration.user_mig_oid_title = "UNSET"
        self.configuration.user_mig_cert_title = "UNSET"
        self.configuration.user_ext_oid_title = "UNSET"
        self.configuration.user_ext_cert_title = "UNSET"

    def test_client_id_dir_basic(self):
        """Test basic client_id_dir conversion"""
        self.assertEqual(client_id_dir(TEST_USER_ID), TEST_USER_DIR)

    def test_client_id_dir_mixed_fields(self):
        """Test conversion with multiple field types"""
        input_id = "/CN=Alice/O=Open Science/OU=Research Team/" \
                   "emailAddress=alice@example.com"
        expected = "+CN=Alice+O=Open_Science+OU=Research_Team+" \
                   "emailAddress=alice@example.com"
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
        self.assertEqual(client_dir_id(TEST_USER_DIR), TEST_USER_ID)

    def test_client_dir_id_mixed_fields(self):
        """Test conversion with multiple field types"""
        input_dir = "+CN=Alice+O=Open_Science+OU=Research_Team+" \
                    "emailAddress=alice@example.com"
        expected_id = "/CN=Alice/O=Open Science/OU=Research Team/" \
                      "emailAddress=alice@example.com"
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
        """Test underscore replacement in remapped fields and preservation
        elsewhere."""
        input_dir = "+OU=Dev_Team+emailAddress=user_name@site.com"
        expected_id = "/OU=Dev Team/emailAddress=user_name@site.com"
        self.assertEqual(client_dir_id(input_dir), expected_id)

    def test_get_site_base_url_prefers_https(self):
        """Test get_site_base_url prefers HTTPS when available."""
        self.configuration.migserver_https_url = "https://example.com"
        self.configuration.migserver_http_url = "http://example.com"
        self.assertEqual(get_site_base_url(
            self.configuration), "https://example.com")

    def test_get_site_base_url_fallback_to_http(self):
        """Test get_site_base_url falls back to HTTP when HTTPS is not
        available."""
        self.configuration.migserver_http_url = "http://example.com"
        self.configuration.migserver_https_url = ""  # Not available
        self.assertEqual(get_site_base_url(self.configuration),
                         "http://example.com")

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
        self.assertEqual(masked['connection_string'],
                         'user:<masked>@db.example.com')
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

    def test_extract_field_exists(self):
        """Test extracting an existing field from a distinguished name."""
        self.assertEqual(extract_field(TEST_USER_ID, 'full_name'),
                         TEST_FULL_NAME)
        self.assertEqual(extract_field(TEST_USER_ID, 'organization'),
                         TEST_ORGANIZATION)
        self.assertEqual(extract_field(TEST_USER_ID, 'country'), TEST_COUNTRY)
        self.assertEqual(extract_field(TEST_USER_ID, 'email'), TEST_EMAIL)

    def test_extract_field_not_exists(self):
        """Test extracting a non-existent field returns None."""
        self.assertIsNone(extract_field(TEST_USER_ID, 'missing'))
        self.assertIsNone(extract_field(TEST_USER_ID, 'dummy'))

    def test_extract_field_with_na_value(self):
        """Test extracting a field with 'NA' value, which should be an empty
        string."""
        self.assertEqual(extract_field('/C=DK/DUMMY=NA/CN=TEST', 'DUMMY'), '')

    def test_extract_field_custom_field(self):
        """Test extracting a custom (non-standard) field."""
        self.assertEqual(extract_field('/C=DK/DUMMY=proj1/CN=Test', 'DUMMY'),
                         'proj1')

    def test_extract_field_empty_dn(self):
        """Test extracting from an empty distinguished name."""
        self.assertIsNone(extract_field("", 'full_name'))

    def test_extract_field_malformed_dn(self):
        """Test extracting from a malformed distinguished name."""
        dn_empty_val = "/C=US/O=/CN=John Doe"
        self.assertEqual(extract_field(dn_empty_val, 'organization'), '')
        dn_no_equals = "/C=US/O/CN=John Doe"
        self.assertIsNone(extract_field(dn_no_equals, 'organization'))

    def test_distinguished_name_to_user_basic(self):
        """Test basic conversion from distinguished name to user dictionary."""
        user_dict = distinguished_name_to_user(TEST_USER_ID)
        expected = {
            'distinguished_name': TEST_USER_ID,
            'country': TEST_COUNTRY,
            'organization': TEST_ORGANIZATION,
            'full_name': TEST_FULL_NAME,
            'email': TEST_EMAIL,
        }
        self.assertEqual(user_dict, expected)

    def test_distinguished_name_to_user_with_na(self):
        """Test that 'NA' values are converted to empty strings."""
        dn = "%s/dummy=NA" % TEST_USER_ID
        user_dict = distinguished_name_to_user(dn)
        expected = {
            'distinguished_name': dn,
            'country': TEST_COUNTRY,
            'organization': TEST_ORGANIZATION,
            'full_name': TEST_FULL_NAME,
            'email': TEST_EMAIL,
            'dummy': ''
        }
        self.assertEqual(user_dict, expected)

    def test_distinguished_name_to_user_with_custom_field(self):
        """Test handling of non-standard fields."""
        dn = "%s/dummy=proj1" % TEST_USER_ID
        user_dict = distinguished_name_to_user(dn)
        expected = {
            'distinguished_name': dn,
            'country': TEST_COUNTRY,
            'organization': TEST_ORGANIZATION,
            'full_name': TEST_FULL_NAME,
            'email': TEST_EMAIL,
            'dummy': 'proj1'
        }
        self.assertEqual(user_dict, expected)

    def test_distinguished_name_to_user_empty_and_malformed(self):
        """Test behavior with empty and malformed distinguished names."""
        # Empty DN
        self.assertEqual(distinguished_name_to_user(""),
                         {'distinguished_name': ''})

        # Malformed part (no '=')
        dn_malformed = "/C=US/O/CN=John Doe"
        user_dict_malformed = distinguished_name_to_user(dn_malformed)
        expected_malformed = {
            'distinguished_name': dn_malformed,
            'country': 'US',
            'full_name': TEST_FULL_NAME
        }
        self.assertEqual(user_dict_malformed, expected_malformed)

        # Empty value
        dn_empty_val = "/C=DK/O=/CN=John Doe"
        user_dict_empty_val = distinguished_name_to_user(dn_empty_val)
        expected_empty_val = {
            'distinguished_name': dn_empty_val,
            'country': TEST_COUNTRY,
            'organization': '',
            'full_name': TEST_FULL_NAME
        }
        self.assertEqual(user_dict_empty_val, expected_empty_val)

    def test_fill_distinguished_name_from_fields(self):
        """Test filling distinguished_name from other user fields."""
        user = {
            'full_name': 'Jane Doe',
            'organization': 'Test Corp',
            'country': TEST_COUNTRY,
            'email': 'jane.doe@example.com'
        }
        fill_distinguished_name(user)
        expected_dn = "/C=DK/ST=NA/L=NA/O=Test Corp/OU=NA/CN=Jane Doe" \
                      "/emailAddress=jane.doe@example.com"
        self.assertEqual(user['distinguished_name'], expected_dn)

    def test_fill_distinguished_name_with_gdp(self):
        """Test filling distinguished_name with a GDP project field."""
        user = {
            'full_name': 'Jane Doe',
            'organization': 'Test Corp',
            'country': TEST_COUNTRY,
            gdp_distinguished_field: 'project_x'
        }
        fill_distinguished_name(user)
        expected_dn = "/C=DK/ST=NA/L=NA/O=Test Corp/OU=NA/CN=Jane Doe" \
                      "/emailAddress=NA/GDP=project_x"
        self.assertEqual(user['distinguished_name'], expected_dn)

    def test_fill_distinguished_name_already_exists(self):
        """Test that an existing distinguished_name is not overwritten."""
        user = {
            'distinguished_name': TEST_USER_ID,
            'full_name': 'Jane Doe',
            'country': 'US'
        }
        original_user = user.copy()
        returned_user = fill_distinguished_name(user)
        self.assertIs(returned_user, user)
        self.assertEqual(user, original_user)

    def test_fill_distinguished_name_empty_user(self):
        """Test filling distinguished_name from an empty user dictionary."""
        user = {}
        fill_distinguished_name(user)
        expected_dn = "/C=NA/ST=NA/L=NA/O=NA/OU=NA/CN=NA/emailAddress=NA"
        self.assertEqual(user['distinguished_name'], expected_dn)

    def test_fill_user_completes_dict(self):
        """Test that fill_user adds missing fields and preserves existing
        ones."""
        user = {
            'full_name': TEST_FULL_NAME,
            'extra_field': 'extra_value'
        }
        fill_user(user)

        # Check that existing values are preserved
        self.assertEqual(user['full_name'], TEST_FULL_NAME)
        self.assertEqual(user['extra_field'], 'extra_value')

        # Check that missing standard fields are added with empty strings
        self.assertEqual(user['organization'], '')
        self.assertEqual(user['country'], '')

        # Check that all standard keys are present
        for key, _ in cert_field_order:
            self.assertIn(key, user)

    def test_fill_user_with_empty_dict(self):
        """Test fill_user with an empty dictionary."""
        user = {}
        fill_user(user)
        self.assertEqual(len(user), len(cert_field_order))
        for key, _ in cert_field_order:
            self.assertEqual(user[key], '')

    def test_fill_user_modifies_in_place_and_returns_self(self):
        """Test that fill_user modifies the dictionary in-place and returns
        it."""
        user = {}
        returned_user = fill_user(user)
        self.assertIs(user, returned_user)

    def test_canonical_user_transformations(self):
        """Test canonical_user applies all transformations correctly."""
        user_dict = {
            'full_name': '  john doe  ',
            'email': 'John@DoE.ORG',
            'country': 'dk',
            'state': 'vt',
            'organization': '  Test Org  ',
            'extra_field': 'should be removed',
            'id': 123
        }
        limit_fields = ['full_name', 'email',
                        'country', 'state', 'organization', 'id']
        canonical = canonical_user(self.configuration, user_dict, limit_fields)

        expected = {
            'full_name': TEST_FULL_NAME,
            'email': TEST_EMAIL,
            'country': TEST_COUNTRY,
            'state': TEST_STATE,
            'organization': TEST_ORGANIZATION,
            'id': 123
        }
        self.assertEqual(canonical, expected)
        self.assertNotIn('extra_field', canonical)

    def test_canonical_user_with_peers_legacy(self):
        """Test canonical_user_with_peers with legacy peers list"""
        self.configuration.site_peers_explicit_fields = ['email', 'full_name']
        user_dict = {
            'full_name': TEST_FULL_NAME,
            'email': TEST_EMAIL,
            'peers': [
                '/C=DK/CN=Alice/emailAddress=alice@example.com',
                '/C=DK/CN=Bob/emailAddress=bob@example.com'
            ]
        }
        limit_fields = ['full_name', 'email']
        canonical = canonical_user_with_peers(
            self.configuration, user_dict, limit_fields)

        self.assertEqual(canonical['peers_email'],
                         'alice@example.com, bob@example.com')
        self.assertEqual(canonical['peers_full_name'], 'Alice, Bob')

    def test_canonical_user_with_peers_explicit(self):
        """Test canonical_user_with_peers with explicit peers fields"""
        self.configuration.site_peers_explicit_fields = ['email', 'full_name']
        user_dict = {
            'full_name': TEST_FULL_NAME,
            'email': TEST_EMAIL,
            'peers_email': 'custom@example.com',
            'peers_full_name': 'Custom Name',
            'peers': [
                '/C=DK/CN=Alice/emailAddress=alice@example.com',
                '/C=DK/CN=Bob/emailAddress=bob@example.com'
            ]
        }
        limit_fields = ['full_name', 'email']
        canonical = canonical_user_with_peers(
            self.configuration, user_dict, limit_fields)

        self.assertEqual(canonical['peers_email'], 'custom@example.com')
        self.assertEqual(canonical['peers_full_name'], 'Custom Name')

    def test_canonical_user_with_peers_mixed(self):
        """Test canonical_user_with_peers with mixed explicit and legacy peers"""
        self.configuration.site_peers_explicit_fields = [
            'email', 'organization']
        user_dict = {
            'full_name': TEST_FULL_NAME,
            'email': TEST_EMAIL,
            'peers_organization': TEST_ORGANIZATION,
            'peers': [
                '/C=DK/O=Legacy Org/CN=Alice/emailAddress=alice@example.com',
                '/C=DK/CN=Bob/emailAddress=bob@example.com'
            ]
        }
        limit_fields = ['full_name', 'email', 'organization']
        canonical = canonical_user_with_peers(
            self.configuration, user_dict, limit_fields)

        # Explicit field should be preserved
        self.assertEqual(canonical['peers_organization'], 'Test Org')
        # Legacy peers should be converted for email
        self.assertEqual(canonical['peers_email'],
                         'alice@example.com, bob@example.com')

    def test_canonical_user_with_peers_empty(self):
        """Test canonical_user_with_peers with no peers data"""
        self.configuration.site_peers_explicit_fields = ['email']
        user_dict = {
            'full_name': TEST_FULL_NAME,
            'email': TEST_EMAIL
        }
        limit_fields = ['full_name', 'email']
        canonical = canonical_user_with_peers(
            self.configuration, user_dict, limit_fields)

        self.assertNotIn('peers_email', canonical)
        self.assertNotIn('peers', canonical)

    def test_canonical_user_with_peers_no_explicit_fields(self):
        """Test canonical_user_with_peers with no peer fields configured"""
        self.configuration.site_peers_explicit_fields = []
        user_dict = {
            'full_name': TEST_FULL_NAME,
            'email': 'john@example.com',
            'peers': [
                '/C=DK/CN=Alice/emailAddress=alice@example.com'
            ]
        }
        limit_fields = ['full_name', 'email']
        canonical = canonical_user_with_peers(
            self.configuration, user_dict, limit_fields)

        # Should not create any peer fields
        self.assertNotIn('peers_email', canonical)
        self.assertNotIn('peers_full_name', canonical)

    def test_canonical_user_with_peers_special_chars(self):
        """Test canonical_user_with_peers handles special characters in DNs"""
        self.configuration.site_peers_explicit_fields = ['full_name']
        user_dict = {
            'full_name': TEST_FULL_NAME,
            'peers': [
                '/C=DK/CN=Jérôme Müller',
                '/C=DK/CN=O‘‘Reilly',
                '/C=DK/CN=Alice "Ace" Smith'
            ]
        }
        limit_fields = ['full_name']
        canonical = canonical_user_with_peers(
            self.configuration, user_dict, limit_fields)

        self.assertEqual(canonical['peers_full_name'],
                         'Jérôme Müller, O‘‘Reilly, Alice "Ace" Smith')

    def test_canonical_user_unicode_name(self):
        """Test canonical_user with unicode characters in full_name."""
        # Using a name that title() might mess up without unicode conversion
        user_dict = {'full_name': u'josé de la vega'}
        limit_fields = ['full_name']
        canonical = canonical_user(self.configuration, user_dict, limit_fields)
        self.assertEqual(canonical['full_name'], u'José De La Vega')

    def test_canonical_user_empty_input(self):
        """Test canonical_user with empty inputs."""
        self.assertEqual(canonical_user(self.configuration, {}, []), {})
        self.assertEqual(canonical_user(self.configuration, {'a': 1}, []), {})
        self.assertEqual(canonical_user(self.configuration, {}, ['a']), {})

    def test_generate_https_urls_single_method_cgi(self):
        """Test generate_https_urls with a single method and cgi-bin."""
        self.configuration.site_login_methods = ['migcert']
        template = "%(auto_base)s/%(auto_bin)s/script.py"
        expected = "https://mig.cert/cgi-bin/script.py"
        result = generate_https_urls(self.configuration, template, {})
        self.assertEqual(result, expected)

    def test_generate_https_urls_single_method_wsgi(self):
        """Test generate_https_urls with a single method and wsgi-bin."""
        self.configuration.site_enable_wsgi = True
        self.configuration.site_login_methods = ['migcert']
        template = "%(auto_base)s/%(auto_bin)s/script.py"
        expected = "https://mig.cert/wsgi-bin/script.py"
        result = generate_https_urls(self.configuration, template, {})
        self.assertEqual(result, expected)

    def test_generate_https_urls_multiple_methods(self):
        """Test generate_https_urls with multiple methods."""
        template = "%(auto_base)s/%(auto_bin)s/script.py"
        self.configuration.site_login_methods = ['migcert', 'extoidc']
        result = generate_https_urls(self.configuration, template, {})
        expected_url1 = "https://mig.cert/cgi-bin/script.py"
        expected_url2 = "https://ext.oidc/cgi-bin/script.py"
        expected_note = """
(The URL depends on whether you log in with OpenID or a user certificate -
just use the one that looks most familiar or try them in turn)"""
        expected_result = "%s\nor\n%s%s" % (expected_url1, expected_url2,
                                            expected_note)
        self.assertEqual(result, expected_result)

    def test_generate_https_urls_with_helper_dict(self):
        """Test generate_https_urls with a helper_dict."""
        self.configuration.site_login_methods = ['extoid']
        template = "%(auto_base)s/%(auto_bin)s/%(script)s"
        helper = {'script': 'login.py'}
        result = generate_https_urls(self.configuration, template, helper)
        self.assertEqual(result, "https://ext.oid/cgi-bin/login.py")

    def test_generate_https_urls_method_enabled_but_url_missing(self):
        """Test that methods with no configured URL are skipped."""
        self.configuration.migserver_https_ext_cert_url = ""  # URL is missing
        self.configuration.site_login_methods = ['migcert', 'extcert']
        template = "%(auto_base)s/%(auto_bin)s/script.py"
        result = generate_https_urls(self.configuration, template, {})
        self.assertEqual(result, "https://mig.cert/cgi-bin/script.py")

    def test_generate_https_urls_no_methods_enabled(self):
        """Test generate_https_urls with no login methods enabled."""
        self.configuration.site_login_methods = []
        template = "%(auto_base)s/%(auto_bin)s/script.py"
        result = generate_https_urls(self.configuration, template, {})
        self.assertEqual(result, "")

    def test_generate_https_urls_respects_order(self):
        """Test that the order of site_login_methods is respected."""
        self.configuration.site_login_methods = ['extoidc', 'migcert']
        template = "%(auto_base)s/%(auto_bin)s/script.py"
        result = generate_https_urls(self.configuration, template, {})
        expected_url1 = "https://ext.oidc/cgi-bin/script.py"
        expected_url2 = "https://mig.cert/cgi-bin/script.py"
        expected_note = """
(The URL depends on whether you log in with OpenID or a user certificate -
just use the one that looks most familiar or try them in turn)"""
        expected_result = "%s\nor\n%s%s" % (expected_url1, expected_url2,
                                            expected_note)
        self.assertEqual(result, expected_result)

    def test_generate_https_urls_avoids_duplicates(self):
        """Test that duplicate URLs are not generated."""
        self.configuration.site_login_methods = [
            'migcert', 'extoidc', 'migcert']
        template = "%(auto_base)s/%(auto_bin)s/script.py"
        result = generate_https_urls(self.configuration, template, {})
        expected_url1 = "https://mig.cert/cgi-bin/script.py"
        expected_url2 = "https://ext.oidc/cgi-bin/script.py"
        expected_note = """
(The URL depends on whether you log in with OpenID or a user certificate -
just use the one that looks most familiar or try them in turn)"""
        expected_result = "%s\nor\n%s%s" % (expected_url1, expected_url2,
                                            expected_note)
        self.assertEqual(result, expected_result)

    def test_auth_type_description_all(self):
        """Test auth_type_description returns full dict when requested"""
        from mig.shared.defaults import keyword_all
        result = auth_type_description(self.configuration, keyword_all)
        expected_keys = ['migoid', 'migoidc', 'migcert', 'extoid', 'extoidc',
                         'extcert']
        self.assertEqual(sorted(result.keys()), sorted(expected_keys))

    def test_auth_type_description_individual(self):
        """Test auth_type_description returns expected strings for each type"""
        from mig.shared.defaults import AUTH_CERTIFICATE, AUTH_OPENID_CONNECT, \
            AUTH_OPENID_V2

        # Setup titles in configuration
        self.configuration.user_mig_oid_title = "MiG OpenID"
        self.configuration.user_mig_cert_title = "MiG Certificate"
        self.configuration.user_ext_oid_title = "External OpenID"
        self.configuration.user_ext_cert_title = "External Certificate"

        test_cases = [
            ('migoid', 'MiG OpenID %s' % AUTH_OPENID_V2),
            ('migoidc', 'MiG OpenID %s' % AUTH_OPENID_CONNECT),
            ('migcert', 'MiG Certificate %s' % AUTH_CERTIFICATE),
            ('extoid', 'External OpenID %s' % AUTH_OPENID_V2),
            ('extoidc', 'External OpenID %s' % AUTH_OPENID_CONNECT),
            ('extcert', 'External Certificate %s' % AUTH_CERTIFICATE),
        ]

        for (auth_type, expected) in test_cases:
            result = auth_type_description(self.configuration, auth_type)
            self.assertEqual(result, expected)

    def test_auth_type_description_unknown(self):
        """Test auth_type_description returns 'UNKNOWN' for invalid types"""
        self.assertEqual(auth_type_description(self.configuration, 'invalid'),
                         'UNKNOWN')
        self.assertEqual(auth_type_description(
            self.configuration, ''), 'UNKNOWN')
        self.assertEqual(auth_type_description(
            self.configuration, None), 'UNKNOWN')

    def test_auth_type_description_empty_titles(self):
        """Test auth_type_description handles empty titles in configuration"""
        from mig.shared.defaults import AUTH_CERTIFICATE, AUTH_OPENID_CONNECT, \
            AUTH_OPENID_V2

        self.configuration.user_mig_oid_title = ""
        self.configuration.user_mig_cert_title = ""
        self.configuration.user_ext_oid_title = ""
        self.configuration.user_ext_cert_title = ""

        test_cases = [
            ('migoid', ' %s' % AUTH_OPENID_V2),
            ('migoidc', ' %s' % AUTH_OPENID_CONNECT),
            ('migcert', ' %s' % AUTH_CERTIFICATE),
            ('extoid', ' %s' % AUTH_OPENID_V2),
            ('extoidc', ' %s' % AUTH_OPENID_CONNECT),
            ('extcert', ' %s' % AUTH_CERTIFICATE),
        ]

        for (auth_type, expected) in test_cases:
            result = auth_type_description(self.configuration, auth_type)
            self.assertEqual(result, expected)

    def test_allow_script_gdp_enabled_anonymous_allowed(self):
        """Test allow_script with GDP enabled, anonymous user, and script
        allowed."""
        self.configuration.site_enable_gdp = True
        script_name = valid_gdp_anon_scripts[0] if valid_gdp_anon_scripts \
            else 'allowed_script.py'  # Use a valid script or a default
        if not valid_gdp_anon_scripts:
            print("WARNING: valid_gdp_anon_scripts is empty.  Using "
                  "'allowed_script.py' which may cause a test failure.")
        allow, msg = allow_script(self.configuration, script_name, None)
        self.assertTrue(allow)
        self.assertEqual(msg, "")

    def test_allow_script_gdp_enabled_anonymous_disallowed(self):
        """Test allow_script with GDP enabled, anonymous user, and script
        disallowed."""
        self.configuration.site_enable_gdp = True
        script_name = 'disallowed_script.py'
        # Ensure the script is not in valid_gdp_anon_scripts
        if script_name in valid_gdp_anon_scripts:
            valid_gdp_anon_scripts.remove(script_name)
        allow, msg = allow_script(self.configuration, script_name, None)
        self.assertFalse(allow)
        self.assertEqual(msg, "anonoymous access to functionality disabled "
                         "by site configuration!")

    def test_allow_script_gdp_enabled_authenticated_allowed(self):
        """Test allow_script with GDP enabled, authenticated user, and script
        allowed."""
        self.configuration.site_enable_gdp = True
        script_name = valid_gdp_auth_scripts[0] if valid_gdp_auth_scripts \
            else valid_gdp_anon_scripts[0] if valid_gdp_anon_scripts \
            else 'allowed_script.py'
        if not valid_gdp_auth_scripts and not valid_gdp_anon_scripts:
            print("WARNING: valid_gdp_auth_scripts and "
                  "valid_gdp_anon_scripts are empty.  Using "
                  "'allowed_script.py' which may cause a test failure.")

        allow, msg = allow_script(
            self.configuration, script_name, 'test_client')
        self.assertTrue(allow)
        self.assertEqual(msg, "")

    def test_allow_script_gdp_enabled_authenticated_disallowed(self):
        """Test allow_script with GDP enabled, authenticated user, and script
        disallowed."""
        self.configuration.site_enable_gdp = True
        script_name = 'disallowed_script.py'

        # Ensure the script is not in valid_gdp_auth_scripts or
        # valid_gdp_anon_scripts
        if script_name in valid_gdp_auth_scripts:
            valid_gdp_auth_scripts.remove(script_name)
        if script_name in valid_gdp_anon_scripts:
            valid_gdp_anon_scripts.remove(script_name)

        allow, msg = allow_script(
            self.configuration, script_name, 'test_client')
        self.assertFalse(allow)
        self.assertEqual(msg, "all access to functionality disabled by site "
                         "configuration!")

    def test_allow_script_gdp_disabled(self):
        """Test allow_script with GDP disabled."""
        self.configuration.site_enable_gdp = False
        allow, msg = allow_script(self.configuration, 'any_script.py',
                                  'test_client')
        self.assertTrue(allow)
        self.assertEqual(msg, "")

    def test_allow_script_gdp_disabled_anonymous(self):
        """Test allow_script with GDP disabled and anonymous user."""
        self.configuration.site_enable_gdp = False
        allow, msg = allow_script(self.configuration, 'any_script.py', None)
        self.assertTrue(allow)
        self.assertEqual(msg, "")

    def test_requested_page_normal(self):
        """Test requested_page with basic environment"""
        fake_env = {
            'SCRIPT_NAME': '/cgi-bin/home.py',
            'REQUEST_URI': '/cgi-bin/home.py'
        }
        self.assertEqual(requested_page(fake_env), '/cgi-bin/home.py')

    def test_requested_page_name_only(self):
        """Test requested_page with name_only argument"""
        fake_env = {
            'BACKEND_NAME': 'search.py',
            'PATH_INFO': '/cgi-bin/search.py/path'
        }
        result = requested_page(fake_env, name_only=True, fallback='fallback')
        self.assertEqual(result, 'search.py')

    def test_requested_page_strip_extension(self):
        """Test requested_page with strip_ext argument"""
        fake_env = {'REQUEST_URI': '/cgi-bin/file.py?query=val'}
        result = requested_page(fake_env, strip_ext=True)
        self.assertEqual(result, '/cgi-bin/file')

    def test_requested_page_priority(self):
        """Test environment variable priority order"""
        _init_env = {
            'BACKEND_NAME': 'backend.py',
            'SCRIPT_URL': '/cgi-bin/script_url.py',
            'SCRIPT_URI': 'https://host/cgi-bin/script_uri.py',
            'PATH_INFO': '/cgi-bin/path_info.py',
            'REQUEST_URI': '/cgi-bin/req_uri.py'
        }

        priority_order = ['BACKEND_NAME', 'SCRIPT_URL', 'SCRIPT_URI',
                          'PATH_INFO', 'REQUEST_URI']

        for var in priority_order:
            # Reset fake_env each time
            fake_env = dict([pair for pair in _init_env.items()])
            current_env = {var: fake_env[var]}
            if var != 'SCRIPT_URI':
                expected = fake_env[var]
            else:
                expected = 'https://host/cgi-bin/script_uri.py'
            result = requested_page(current_env)
            self.assertEqual(result, expected,
                             "failed priority for %s" % var)

            # Remove higher priority variables one by one
            for higher_var in priority_order[:priority_order.index(var)]:
                del fake_env[higher_var]
            result = requested_page(fake_env)
            self.assertEqual(result, fake_env[var],
                             "failed fallthrough to %s" % var)

    def test_requested_page_unsafe_filter(self):
        """Test unsafe character filtering"""
        test_cases = [
            ('/cgi-bin/unsafe<script>.py', '/cgi-bin/unsafescript.py'),
            ('/path/with#hash', '/path/withhash'),
            ('/evil/alert("xss")', '/evil/alertxss')
        ]
        for (input_val, expected) in test_cases:
            fake_env = {'REQUEST_URI': input_val}
            result = requested_page(fake_env)
            self.assertEqual(result, expected,
                             "failed filtering for %s" % input_val)

    def test_requested_page_include_unsafe(self):
        """Test include_unsafe argument behavior"""
        dangerous = '/cgi-bin/unsafe<script>alert(1)</script>.py'
        fake_env = {'REQUEST_URI': dangerous}
        unsafe_result = requested_page(fake_env, include_unsafe=True)
        self.assertEqual(unsafe_result, dangerous)

        safe_result = requested_page(fake_env)
        self.assertNotEqual(safe_result, dangerous)

    def test_requested_page_query_stripping(self):
        """Test removal of query parameters"""
        test_input = '/cgi-bin/script.py?query=value&param=data'
        fake_env = {'REQUEST_URI': test_input}
        result = requested_page(fake_env)
        self.assertEqual(result, '/cgi-bin/script.py')

    def test_requested_page_fallback(self):
        """Test fallback to default"""
        fake_env = {}
        fallback = 'special.py'
        result = requested_page(fake_env, fallback=fallback)
        self.assertEqual(result, fallback)

    def test_requested_page_fallback_despite_os_environ_value(self):
        """Test fallback to default"""
        fake_env = {}
        fallback = 'special.py'
        os.environ['BACKEND_NAME'] = 'BOGUS'
        result = requested_page(fake_env, fallback=fallback)
        del os.environ['BACKEND_NAME']
        self.assertEqual(result, fallback)

    def test_requested_url_base_normal(self):
        """Test requested_url_base with basic complete URL"""
        fake_env = {'SCRIPT_URI': 'https://example.com/path/to/script.py'}
        result = requested_url_base(fake_env)
        expected = 'https://example.com'
        self.assertEqual(result, expected)

    def test_requested_url_base_custom_field(self):
        """Test requested_url_base with custom uri_field parameter"""
        fake_env = {'CUSTOM_FIELD_URI': 'http://server.org:8001/base/'}
        result = requested_url_base(fake_env, uri_field='CUSTOM_FIELD_URI')
        expected = 'http://server.org:8001'
        self.assertEqual(result, expected)

    # TODO: adjust tested function to bail out on missing uri_field
    @unittest.skipIf(True, "requires fix in tested function")
    def test_requested_url_base_missing(self):
        """Test requested_url_base when uri_field not present"""
        fake_env = {}
        result = requested_url_base(fake_env)
        self.assertEqual(result, '')

    def test_requested_url_base_safe_filter(self):
        """Test unsafe character filtering in url base"""
        test_url = 'https://user:pass@evil.com/<script>malicious</script>'
        fake_env = {'SCRIPT_URI': test_url}
        safe_result = requested_url_base(fake_env)
        expected_safe = 'https://user:passevil.com'
        self.assertEqual(safe_result, expected_safe)

    def test_requested_url_base_include_unsafe(self):
        """Test include_unsafe argument behavior"""
        test_url = 'http://[::1]?<markup>'
        fake_env = {'SCRIPT_URI': test_url}
        unsafe_result = requested_url_base(fake_env, include_unsafe=True)
        self.assertEqual(unsafe_result, 'http://[::1]?<markup>')

        safe_result = requested_url_base(fake_env, include_unsafe=False)
        self.assertEqual(safe_result, 'http://::1markup')
        safe_result = requested_url_base(fake_env)
        self.assertEqual(safe_result, 'http://::1markup')

    def test_requested_url_base_split_valid_edge_cases(self):
        """Test URL base splitting on valid edge cases"""
        test_cases = [
            ('https://site.com', 'https://site.com'),
            ('http://a/single/slash', 'http://a'),
            ('file:///absolute/path', 'file://'),
            ('invalid.proto://double/slash', 'invalid.proto://double')
        ]
        for (input_url, expected) in test_cases:
            fake_env = {'SCRIPT_URI': input_url}
            result = requested_url_base(fake_env)
            self.assertEqual(result, expected,
                             "failed for %s" % input_url)

    # TODO: adjust function to bail out on invalid URLs and enable next
    @unittest.skipIf(True, "requires fix in tested function")
    def test_requested_url_base_split_invalid_edge_cases(self):
        """Test URL base splitting on invalid edge cases"""
        test_cases = [
            ('', ''),
            ('/', '/'),
            ('/single', '/single'),
            ('/double/slash', '/double/slash'),
            ('invalid.proto:/1st/2nd/slash', 'invalid.proto:/1st/2nd/slash'),
            ('invalid.proto://double/slash', 'invalid.proto://double')
        ]
        for (input_url, expected) in test_cases:
            fake_env = {'SCRIPT_URI': input_url}
            try:
                result = requested_url_base(fake_env)
            except ValueError:
                result = False
            self.assertFalse(result, "allowed invalid %s" % input_url)

    # TODO: adjust tested function to bail out on missing URL prefix
    @unittest.skipIf(True, "requires fix in tested function")
    def test_requested_url_base_relative_path(self):
        """Test relative paths in URL"""
        fake_env = {'SCRIPT_URI': '/cgi-bin/script.py'}
        try:
            result = requested_url_base(fake_env)
        except ValueError:
            result = False
        self.assertFalse(result, "allowed relative path")

    # TODO: adjust tested function to allow unicode chars / domains?
    @unittest.skipIf(True, "requires fix in tested function")
    def test_requested_url_base_special_chars(self):
        """Test handling of special characters in URL"""
        test_url = 'http://üñîçøðê.net/path'
        fake_env = {'SCRIPT_URI': test_url}
        result = requested_url_base(fake_env)
        self.assertEqual(result, 'http://üñîçøðê.net')

    def test_verify_local_url_direct_match(self):
        """Test verify_local_url with direct match to known site URL"""
        test_url = "https://mig.cert/cgi-bin/home.py"
        self.configuration.migserver_https_mig_cert_url = "https://mig.cert"
        self.assertTrue(verify_local_url(self.configuration, test_url))

    def test_verify_local_url_subpath_match(self):
        """Test verify_local_url with subpath under valid domain"""
        test_url = "https://mig.oid/wsgi-bin/login.py"
        self.configuration.migserver_https_mig_oid_url = "https://mig.oid"
        self.assertTrue(verify_local_url(self.configuration, test_url))

    def test_verify_local_url_public_alias(self):
        """Test verify_local_url with public alias domain"""
        self.configuration.migserver_public_alias_url = "https://grid.example.org"
        test_url = "https://grid.example.org/cgi-bin/file.py"
        self.assertTrue(verify_local_url(self.configuration, test_url))

    def test_verify_local_url_absolute_path(self):
        """Test verify_local_url with absolute path"""
        test_url = "/cgi-bin/script.py"
        self.assertTrue(verify_local_url(self.configuration, test_url))

    def test_verify_local_url_relative_path(self):
        """Test verify_local_url with relative path"""
        test_url = "subdir/script.py"
        with self.assertLogs(level='ERROR') as log_capture:
            status = verify_local_url(self.configuration, test_url)
        self.assertFalse(status)
        self.assertTrue(any('request verification failed' in msg for msg in
                            log_capture.output))

    def test_verify_local_url_external_domain(self):
        """Test verify_local_url rejects external domains"""
        test_url = "https://evil.com/malicious.py"
        with self.assertLogs(level='ERROR') as log_capture:
            status = verify_local_url(self.configuration, test_url)
        self.assertFalse(status)
        self.assertTrue(any('request verification failed' in msg for msg in
                            log_capture.output))

    def test_verify_local_url_invalid_url(self):
        """Test verify_local_url rejects invalid/malformed URLs"""
        test_url = "javascript:alert('xss')"
        with self.assertLogs(level='ERROR') as log_capture:
            status = verify_local_url(self.configuration, test_url)
        self.assertFalse(status)
        self.assertTrue(any('request verification failed' in msg for msg in
                            log_capture.output))

    def test_verify_local_url_missing_https(self):
        """Test verify_local_url with HTTP when only HTTPS supported"""
        test_url = "http://mig.cert/cgi-bin/home.py"
        self.configuration.migserver_https_mig_cert_url = "https://mig.cert"
        with self.assertLogs(level='ERROR') as log_capture:
            status = verify_local_url(self.configuration, test_url)
        self.assertFalse(status)
        self.assertTrue(any('request verification failed' in msg for msg in
                            log_capture.output))

    def test_verify_local_url_different_port(self):
        """Test verify_local_url rejects same domain with different port"""
        self.configuration.migserver_https_ext_cert_url = "https://ext.cert:443"
        test_url = "https://ext.cert:444/cgi-bin/file.py"
        with self.assertLogs(level='ERROR') as log_capture:
            status = verify_local_url(self.configuration, test_url)
        self.assertFalse(status)
        self.assertTrue(any('request verification failed' in msg for msg in
                            log_capture.output))

    def test_invisible_path_file(self):
        """Test invisible_path detects names in invisible files"""
        invisible_filename = '.htaccess'
        visible_filename = 'visible.txt'

        # Test with invisible filename
        self.assertTrue(invisible_path('/some/path/%s' % invisible_filename))
        self.assertTrue(invisible_path(invisible_filename))
        self.assertTrue(invisible_path(invisible_filename, True))

        # Test with visible filename
        self.assertFalse(invisible_path(visible_filename))
        self.assertFalse(invisible_path('/some/path/%s' % visible_filename))

    def test_invisible_path_dir(self):
        """Test invisible_path detects paths in invisible dir"""
        invisible_dirname = '.vgridscm'
        visible_dirname = 'somedir'

        # Test different forms of invisible directory path
        self.assertTrue(invisible_path(invisible_dirname))
        self.assertTrue(invisible_path('/%s' % invisible_dirname))
        self.assertTrue(invisible_path('/parent/%s' % invisible_dirname))
        self.assertTrue(invisible_path('%s/sub' % invisible_dirname))
        self.assertTrue(invisible_path('/%s/file' % invisible_dirname))

        # Test visible directory
        self.assertFalse(invisible_path(visible_dirname))
        self.assertFalse(invisible_path('/%s' % visible_dirname))
        self.assertFalse(invisible_path('/parent/%s' % visible_dirname))

    def test_invisible_path_vgrid_exception(self):
        """Test allow_vgrid_scripts excludes valid vgrid xgi scripts"""
        invisible_dirname = '.vgridscm'
        vgrid_script = '.vgridscm/cgi-bin/hgweb.cgi'

        test_patterns = [
            '/%s/%s' % (invisible_dirname, vgrid_script),
            '/root/%s/sub/%s' % (invisible_dirname, vgrid_script),
            '/%s/prefix%ssuffix' % (invisible_dirname, vgrid_script),
            '/%s/similar_script.py' % invisible_dirname,
            '/path/to/%s' % vgrid_script

        ]
        test_expects = [False, False, False, True, False]

        test_iter = zip(test_patterns, test_expects)
        for (i, (path, expected)) in enumerate(test_iter):
            self.assertEqual(
                invisible_path(path, allow_vgrid_scripts=True),
                expected,
                "test case %d: path %r should %sbe invisible with scripts"
                % (i, path, "" if expected else "not ")
            )

            # Should still be invisible without exception flag
            expect_no_exception = True if invisible_dirname in path else False
            self.assertEqual(
                invisible_path(path, allow_vgrid_scripts=False),
                expect_no_exception,
                "test case %d: path %r should %sbe invisible without scripts"
                % (i, path, "" if expect_no_exception else "not ")
            )

    def test_invisible_path_edge_cases(self):
        """Test invisible_path handles edge cases"""
        from mig.shared.defaults import _user_invisible_dirs
        invisible_dirname = _user_invisible_dirs[0]

        # Empty path
        self.assertFalse(invisible_path(''))
        self.assertFalse(invisible_path('', allow_vgrid_scripts=True))

        # Root path
        self.assertFalse(invisible_path('/'))

        # Path that only contains invisible directory substring
        substring_path = '/prefix%ssuffix/file' % invisible_dirname
        self.assertFalse(invisible_path(substring_path))

    def test_client_alias(self):
        """Test client_alias transforms and encodes IDs"""
        result = client_alias(TEST_USER_ID)
        # Verify base64 urlsafe encoding
        self.assertEqual(result, TEST_CLIENT_ALIAS, "failed alias client id")

    def test_expand_openid_alias(self):
        """Test expand_openid_alias resolves symlinks to real IDs"""
        user_home = self.temppath(TEST_USER_DIR, ensure_dir=True)

        # Create symlink
        link_path = os.path.join(user_home, TEST_ALIAS)
        os.symlink(TEST_USER_DIR, link_path)

        # Set config and test
        self.configuration.user_home = user_home
        resolved = expand_openid_alias(TEST_ALIAS, self.configuration)
        self.assertEqual(resolved, TEST_USER_ID)

    def test_get_short_id_basic(self):
        """Test get_short_id without GDPR features"""
        alias_field = "email"
        result = get_short_id(self.configuration, TEST_USER_ID, alias_field)
        self.assertEqual(result, TEST_ALIAS)

    def test_get_short_id_with_gdp(self):
        """Test get_short_id includes GDPR project info when enabled"""
        self.configuration.site_enable_gdp = True
        alias_field = "email"
        result = get_short_id(self.configuration, GDP_USER_ID, alias_field)
        self.assertEqual(result, GDP_ALIAS)

    def test_get_user_id_x509_format(self):
        """Test get_user_id returns DN for X509 format"""
        self.configuration.site_user_id_format = "X509"
        user = {'distinguished_name': TEST_USER_ID}
        result = get_user_id(self.configuration, user)
        self.assertEqual(result, TEST_USER_ID)

    def test_get_user_id_uuid_format(self):
        """Test get_user_id returns UUID when configured"""
        self.configuration.site_user_id_format = "UUID"
        user = {'unique_id': "123e4567-e89b-12d3-a456-426614174000"}
        result = get_user_id(self.configuration, user)
        self.assertEqual(result, "123e4567-e89b-12d3-a456-426614174000")

    def test_get_client_id(self):
        """Test get_client_id extracts DN from user dict"""
        test_dn = "/C=US/CN=Alice"
        user = {'distinguished_name': test_dn, 'other': 'field'}
        result = get_client_id(user)
        self.assertEqual(result, test_dn)

    def test_hexlify_unhexlify_roundtrip(self):
        """Test hexlify/unhexlify round-trip conversion"""
        test_str = "secret_value"
        hexed = hexlify(test_str)
        self.assertEqual(hexed, "7365637265745f76616c7565")
        unhexed = unhexlify(hexed)
        self.assertEqual(unhexed, test_str)

    def test_is_gdp_user_detection(self):
        """Test is_gdp_user detects GDP project presence"""
        self.assertTrue(is_gdp_user(
            self.configuration,
            "/GDP_PROJ=12345"
        ))
        self.assertFalse(is_gdp_user(
            self.configuration,
            "/CN=Regular User"
        ))

    def test_invisible_file_detection(self):
        """Test invisible_file detects hidden system files"""
        for forbidden in [".htaccess"]:
            self.assertTrue(invisible_file(forbidden))
        for allowed in ["readme.txt", "data.csv"]:
            self.assertFalse(invisible_file(allowed))

    def test_invisible_dir_detection(self):
        """Test invisible_dir detects protected directories"""
        for forbidden in [".vgridscm", ".vgridtracker"]:
            self.assertTrue(invisible_dir(forbidden))
        for allowed in ["public_files", "shared"]:
            self.assertFalse(invisible_dir(allowed))

    def test_requested_backend_extraction(self):
        """Test requested_backend extracts backend name from environ"""
        test_env = {
            'BACKEND_NAME': '/cgi-bin/fileman.py',
            'PATH_TRANSLATED': '/wsgi-bin/fileman.py'
        }
        result = requested_backend(test_env)
        self.assertEqual(result, "fileman")

    def test_pretty_format_user(self):
        """Test pretty_format_user hides email and formats nicely"""
        test_dn = "/C=DK/CN=Alice/O=Org/emailAddress=alice@example.com"
        result = pretty_format_user(test_dn)
        self.assertIn("Alice, Org", result)
        self.assertIn("email hidden", result)

    def test_string_snippet_shortening(self):
        """Test string_snippet shortens long strings with markers"""
        long_str = "abcdefghijklmnopqrstuvwxyz12345"
        result = string_snippet(long_str, 16)
        self.assertEqual(result, "abcdef .. z12345")

    def test_get_xgi_bin_wsgi_vs_cgi(self):
        """Test get_xgi_bin returns correct script bin based on config"""
        # Test WSGI enabled
        self.configuration.site_enable_wsgi = True
        self.assertEqual(get_xgi_bin(self.configuration), 'wsgi-bin')

        # Test WSGI disabled
        self.configuration.site_enable_wsgi = False
        self.assertEqual(get_xgi_bin(self.configuration), 'cgi-bin')

        # Test legacy force
        self.assertEqual(get_xgi_bin(self.configuration, force_legacy=True),
                         'cgi-bin')

    def test_valid_dir_input(self):
        """Test valid_dir_input prevents path traversal attempts"""
        base = "/allowed"
        test_cases = [
            ("safe_dir", True),
            ("sub/safe", True),
            ("../illegal", False),
            ("/absolute", False),
        ]
        for (relative_path, expected) in test_cases:
            self.assertEqual(
                valid_dir_input(base, relative_path),
                expected,
                "failed for %s" % relative_path
            )

    def test_user_base_dir(self):
        """Test user_base_dir formats paths with correct trailing slash"""
        result = user_base_dir(self.configuration, TEST_USER_ID)
        self.assertTrue(result.startswith(self.configuration.user_home))
        self.assertTrue(result.endswith(os.sep))

    def test_brief_list(self):
        """Test brief_list helper function for shortening long lists"""

        # Empty list should remain empty
        self.assertEqual(brief_list([]), [])

        # List smaller than max_entries remains unchanged
        short_list = [1, 2, 3]
        self.assertEqual(brief_list(short_list, 5), short_list)

        # List exactly at max_entries remains unchanged
        exact_list = list(range(10))
        self.assertEqual(brief_list(exact_list), exact_list)

        # List longer than max_entries gets shortened
        long_list = list(range(15))
        expected_long = [0, 1, 2, 3, 4, ' ... shortened ... ', 10, 11, 12,
                         13, 14]
        self.assertEqual(brief_list(long_list), expected_long)

        # Custom max_entries with odd number
        custom_odd_list = list(range(10))
        expected_odd = [0, 1, 2, 3, ' ... shortened ... ', 6, 7, 8, 9]
        self.assertEqual(brief_list(custom_odd_list, 9), expected_odd)

        # Range objects should be handled properly
        input_range = range(20)
        expected_range = [0, 1, 2, 3, 4, ' ... shortened ... ', 15, 16, 17,
                          18, 19]
        self.assertEqual(brief_list(input_range), expected_range)

        # Edge case - max_entries=2
        self.assertEqual(brief_list([1, 2, 3, 4], 2),
                         [1, ' ... shortened ... ', 4])

        # Very small max_entries
        self.assertEqual(brief_list([1, 2, 3, 4], 3),
                         [1, ' ... shortened ... ', 4])

        # Non-integer input
        str_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        expected_str = ['a', 'b', 'c', ' ... shortened ... ', 'e', 'f', 'g']
        self.assertEqual(brief_list(str_list, 7), str_list)  # At max_entries

    # TODO: fix tested function to handle these and enable test
    @unittest.skipIf(True, "requires fix in tested function")
    def test_brief_list_edge_cases(self):
        """Test brief_list helper function for compact list on edge cases"""
        # Edge case - max_entries=1
        self.assertEqual(brief_list([1, 2, 3], 1), [' ... shortened ... '])

        # Edge case - even short number of max_entries
        str_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        self.assertEqual(brief_list(str_list, 6),
                         ['a', 'b', ' ... shortened ... ', 'f', 'g'])


class TestMigSharedBase__legacy(MigTestCase):
    """Run mig.shared.base legacy self-test"""

    # TODO: migrate all legacy self-check functionality into the above?
    def test_existing_main(self):
        """Run built-in self-tests and check output"""
        def raise_on_error_exit(exit_code):
            if exit_code != 0:
                if raise_on_error_exit.last_print is not None:
                    identifying_message = raise_on_error_exit.last_print
                else:
                    identifying_message = 'unknown'
                raise AssertionError(
                    'failure in unittest/testcore: %s' %
                    (identifying_message,))
        raise_on_error_exit.last_print = None

        def record_last_print(value):
            """Keep track of printed output"""
            raise_on_error_exit.last_print = value

        legacy_main(_exit=raise_on_error_exit, _print=record_last_print)
