# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_tlsserver - unit test of the corresponding mig shared module
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

"""Unit tests for the migrid module pointed to in the filename"""

import os
import unittest

try:
    import OpenSSL
except ImportError:
    OpenSSL = None

# Imports of the code under test
from mig.shared.tlsserver import hardened_openssl_context, \
    hardened_ssl_context, ssl
# Imports required for the unit test wrapping
from mig.shared.defaults import STRONG_TLS_CIPHERS, STRONG_TLS_LEGACY_CIPHERS, \
    STRONG_TLS_CURVES
# Imports required for the unit tests themselves
from tests.support import MigTestCase, TEST_DATA_DIR

# IMPORTANT: BOGUS key + self-signed certs in TEST_DATA_DIR are ONLY for tests!
TEST_KEY_FILE = "testkey.pem"
TEST_KEY_PATH = os.path.join(TEST_DATA_DIR, TEST_KEY_FILE)
TEST_CERT_FILE = "testcert.pem"
TEST_CERT_PATH = os.path.join(TEST_DATA_DIR, TEST_CERT_FILE)
# TEST_CACERT_FILE = "testcacert.pem"
# TEST_CACERT_PATH = os.path.join(TEST_DATA_DIR, TEST_CACERT_FILE)
TEST_CACERT_PATH = TEST_CACERT_FILE = None
TEST_DHPARAMS_FILE = "testdhparams.pem"
TEST_DHPARAMS_PATH = os.path.join(TEST_DATA_DIR, TEST_DHPARAMS_FILE)


class MigSharedTlsServer(MigTestCase):
    """Unit tests for tlsserver related helper functions using proper TLS"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def test_hardened_ssl_context_options_default_without_dhparams(self):
        """Test SSL context options are set correctly without DH params"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            dhparamsfile=None,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )

        # Verify options are set
        expected_options = (
            getattr(ssl, 'OP_NO_SSLv2', 0x1000000) |
            getattr(ssl, 'OP_NO_SSLv3', 0x2000000) |
            getattr(ssl, 'OP_NO_TLSv1', 0x4000000) |
            getattr(ssl, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(ssl, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(ssl, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(ssl, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = context.options
        self.assertEqual(options & expected_options, expected_options)
        # Verify that the minimum TLS version is enforced
        minimum_version = context.minimum_version
        self.assertEqual(minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_hardened_ssl_context_options_default(self):
        """Test SSL context options are set correctly"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )

        # Verify options are set
        expected_options = (
            getattr(ssl, 'OP_NO_SSLv2', 0x1000000) |
            getattr(ssl, 'OP_NO_SSLv3', 0x2000000) |
            getattr(ssl, 'OP_NO_TLSv1', 0x4000000) |
            getattr(ssl, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(ssl, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(ssl, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(ssl, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = context.options
        self.assertEqual(options & expected_options, expected_options)
        # Verify that the minimum TLS version is enforced
        minimum_version = context.minimum_version
        self.assertEqual(minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_hardened_ssl_context_options_tls1_3_only(self):
        """Test SSL context options are set correctly with TLS 1.3 only"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=False,
            allow_renegotiation=False
        )

        # Verify options are set
        expected_options = (
            getattr(ssl, 'OP_NO_SSLv2', 0x1000000) |
            getattr(ssl, 'OP_NO_SSLv3', 0x2000000) |
            getattr(ssl, 'OP_NO_TLSv1', 0x4000000) |
            getattr(ssl, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(ssl, 'OP_NO_TLSv1_2', 0x8000000) |
            getattr(ssl, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(ssl, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(ssl, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = context.options
        self.assertEqual(options & expected_options, expected_options)
        # Verify that the minimum TLS version is enforced
        minimum_version = context.minimum_version
        self.assertEqual(minimum_version, ssl.TLSVersion.TLSv1_3)

    def test_hardened_ssl_context_options_fail_reneg(self):
        """Test SSL context options fail when different"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=True
        )

        # Verify options are set
        expected_options = (
            getattr(ssl, 'OP_NO_SSLv2', 0x1000000) |
            getattr(ssl, 'OP_NO_SSLv3', 0x2000000) |
            getattr(ssl, 'OP_NO_TLSv1', 0x4000000) |
            getattr(ssl, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(ssl, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(ssl, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(ssl, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = context.options
        self.assertNotEqual(options & expected_options, expected_options)

    def test_hardened_ssl_context_options_fail_tls1_2(self):
        """Test SSL context options fail when conflicting"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )

        # Verify options are set
        expected_options = (
            getattr(ssl, 'OP_NO_SSLv2', 0x1000000) |
            getattr(ssl, 'OP_NO_SSLv3', 0x2000000) |
            getattr(ssl, 'OP_NO_TLSv1', 0x4000000) |
            getattr(ssl, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(ssl, 'OP_NO_TLSv1_2', 0x8000000) |
            getattr(ssl, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(ssl, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(ssl, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = context.options
        self.assertNotEqual(options & expected_options, expected_options)
        # Verify that the minimum TLS version is still enforced
        minimum_version = context.minimum_version
        self.assertEqual(minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_hardened_ssl_context_ciphers(self):
        """Test SSL context ciphers are set correctly"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )
        # NOTE: this may be too platform specific
        expected_start = "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:"
        expected_end = ":DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384"
        ciphers = ':'.join([spec['name'] for spec in context.get_ciphers()])
        self.assertTrue(ciphers.startswith(expected_start))
        self.assertTrue(ciphers.endswith(expected_end))

    def test_hardened_ssl_context_legacy_ciphers(self):
        """Test SSL context legacy ciphers are set correctly"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_LEGACY_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )
        # NOTE: this may be too platform specific
        expected_start = "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:"
        expected_end = ":CAMELLIA256-SHA256:CAMELLIA128-SHA256"
        ciphers = ':'.join([spec['name'] for spec in context.get_ciphers()])
        self.assertTrue(ciphers.startswith(expected_start))
        self.assertTrue(ciphers.endswith(expected_end))

    @unittest.skipIf(OpenSSL is None, "pyOpenSSL is required for openssl test")
    def test_hardened_openssl_context_options_default_without_dhparams(self):
        """Test OpenSSL context options are set correctly without DH params"""
        config = self.configuration
        config.logger = self.logger
        SSL = OpenSSL.SSL

        context = hardened_openssl_context(
            config,
            OpenSSL,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            cacertfile=TEST_CACERT_PATH,
            dhparamsfile=None,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )

        # Verify options are set
        expected_options = (
            getattr(SSL, 'OP_NO_SSLv2', 0x1000000) |
            getattr(SSL, 'OP_NO_SSLv3', 0x2000000) |
            getattr(SSL, 'OP_NO_TLSv1', 0x4000000) |
            getattr(SSL, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(SSL, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(SSL, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(SSL, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(SSL, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(SSL, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = getattr(context, '_options', None)
        self.assertEqual(options & expected_options, expected_options)
        # Verify that the minimum TLS version is enforced
        minimum_version = getattr(context, '_minimum_version', None)
        self.assertEqual(minimum_version, SSL.TLS1_2_VERSION)

    @unittest.skipIf(OpenSSL is None, "pyOpenSSL is required for openssl test")
    def test_hardened_openssl_context_options_default(self):
        """Test OpenSSL context options are set correctly"""
        config = self.configuration
        config.logger = self.logger
        SSL = OpenSSL.SSL

        context = hardened_openssl_context(
            config,
            OpenSSL,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            cacertfile=TEST_CACERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )

        # Verify options are set
        expected_options = (
            getattr(SSL, 'OP_NO_SSLv2', 0x1000000) |
            getattr(SSL, 'OP_NO_SSLv3', 0x2000000) |
            getattr(SSL, 'OP_NO_TLSv1', 0x4000000) |
            getattr(SSL, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(SSL, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(SSL, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(SSL, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(SSL, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(SSL, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = getattr(context, '_options', None)
        self.assertEqual(options & expected_options, expected_options)
        # Verify that the minimum TLS version is enforced
        minimum_version = getattr(context, '_minimum_version', None)
        self.assertEqual(minimum_version, SSL.TLS1_2_VERSION)

    @unittest.skipIf(OpenSSL is None, "pyOpenSSL is required for openssl test")
    def test_hardened_openssl_context_options_tls1_3_only(self):
        """Test OpenSSL context options are set correctly with TLS 1.3 only"""
        config = self.configuration
        config.logger = self.logger
        SSL = OpenSSL.SSL

        context = hardened_openssl_context(
            config,
            OpenSSL,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            cacertfile=TEST_CACERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=False,
            allow_renegotiation=False
        )

        # Verify options are set
        expected_options = (
            getattr(SSL, 'OP_NO_SSLv2', 0x1000000) |
            getattr(SSL, 'OP_NO_SSLv3', 0x2000000) |
            getattr(SSL, 'OP_NO_TLSv1', 0x4000000) |
            getattr(SSL, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(SSL, 'OP_NO_TLSv1_2', 0x8000000) |
            getattr(SSL, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(SSL, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(SSL, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(SSL, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(SSL, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = getattr(context, '_options', None)
        self.assertEqual(options & expected_options, expected_options)
        # Verify that the minimum TLS version is enforced
        minimum_version = getattr(context, '_minimum_version', None)
        self.assertEqual(minimum_version, SSL.TLS1_3_VERSION)

    @unittest.skipIf(OpenSSL is None, "pyOpenSSL is required for openssl test")
    def test_hardened_openssl_context_options_fail_reneg(self):
        """Test OpenSSL context options fail when different"""
        config = self.configuration
        config.logger = self.logger
        SSL = OpenSSL.SSL

        context = hardened_openssl_context(
            config,
            OpenSSL,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            cacertfile=TEST_CACERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=True
        )

        # Verify options are set
        expected_options = (
            getattr(SSL, 'OP_NO_SSLv2', 0x1000000) |
            getattr(SSL, 'OP_NO_SSLv3', 0x2000000) |
            getattr(SSL, 'OP_NO_TLSv1', 0x4000000) |
            getattr(SSL, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(SSL, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(SSL, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(SSL, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(SSL, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(SSL, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = getattr(context, '_options', None)
        self.assertNotEqual(options & expected_options, expected_options)

    @unittest.skipIf(OpenSSL is None, "pyOpenSSL is required for openssl test")
    def test_hardened_openssl_context_options_fail_tls1_2(self):
        """Test OpenSSL context options fail when conflicting"""
        config = self.configuration
        config.logger = self.logger
        SSL = OpenSSL.SSL

        context = hardened_openssl_context(
            config,
            OpenSSL,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            cacertfile=TEST_CACERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )

        # Verify options are set
        expected_options = (
            getattr(SSL, 'OP_NO_SSLv2', 0x1000000) |
            getattr(SSL, 'OP_NO_SSLv3', 0x2000000) |
            getattr(SSL, 'OP_NO_TLSv1', 0x4000000) |
            getattr(SSL, 'OP_NO_TLSv1_1', 0x10000000) |
            getattr(SSL, 'OP_NO_TLSv1_2', 0x8000000) |
            getattr(SSL, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(SSL, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(SSL, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(SSL, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(SSL, 'OP_NO_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        options = getattr(context, '_options', None)
        self.assertNotEqual(options & expected_options, expected_options)
        # Verify that the minimum TLS version is still enforced
        minimum_version = getattr(context, '_minimum_version', None)
        self.assertEqual(minimum_version, SSL.TLS1_2_VERSION)

    @unittest.skipIf(OpenSSL is None, "pyOpenSSL is required for openssl test")
    def test_hardened_openssl_context_ciphers(self):
        """Test OpenSSL context ciphers are set correctly"""
        config = self.configuration
        config.logger = self.logger
        SSL = OpenSSL.SSL

        context = hardened_openssl_context(
            config,
            OpenSSL,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            cacertfile=TEST_CACERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )
        # NOTE: this may be too platform specific
        expected_start = "ECDHE-ECDSA-AES128-GCM-SHA256:"
        expected_end = ":DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384"
        ciphers = getattr(context, '_ciphers', None)
        self.assertTrue(ciphers.startswith(expected_start))
        self.assertTrue(ciphers.endswith(expected_end))

    @unittest.skipIf(OpenSSL is None, "pyOpenSSL is required for openssl test")
    def test_hardened_openssl_context_legacy_ciphers(self):
        """Test OpenSSL context legacy ciphers are set correctly"""
        config = self.configuration
        config.logger = self.logger
        SSL = OpenSSL.SSL

        context = hardened_openssl_context(
            config,
            OpenSSL,
            TEST_KEY_PATH,
            TEST_CERT_PATH,
            cacertfile=TEST_CACERT_PATH,
            dhparamsfile=TEST_DHPARAMS_PATH,
            ciphers=STRONG_TLS_LEGACY_CIPHERS,
            curve_priority=STRONG_TLS_CURVES,
            allow_pre_tlsv13=True,
            allow_renegotiation=False
        )
        # NOTE: this may be too platform specific
        expected_start = "ECDHE-RSA-AES128-GCM-SHA256:"
        expected_end = ":DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES:CAMELLIA"
        ciphers = getattr(context, '_ciphers', None)
        self.assertTrue(ciphers.startswith(expected_start))
        self.assertTrue(ciphers.endswith(expected_end))
