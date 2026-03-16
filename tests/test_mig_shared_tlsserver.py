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
from unittest.mock import patch, MagicMock

# PyOpenSSL is required for hardened_openssl_context tests
try:
    import OpenSSL
except ImportError:
    OpenSSL = None

# Imports of the code under test
from mig.shared.tlsserver import hardened_ssl_context, hardened_openssl_context, ssl
# Imports required for the unit test wrapping
from mig.shared.defaults import STRONG_TLS_CIPHERS, STRONG_TLS_LEGACY_CIPHERS, \
    STRONG_TLS_CURVES
# Imports required for the unit tests themselves
from tests.support import MigTestCase


class MigSharedTlsServer(MigTestCase):
    """Unit tests for tlsserver related helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def test_hardened_ssl_context_basic(self):
        """Test basic SSL context creation with default parameters"""
        with patch('mig.shared.tlsserver.ssl') as mock_ssl:
            mock_ssl.PROTOCOL_SSLv23 = 1
            mock_ssl.SSLContext = MagicMock()
            mock_ssl.SSLContext.return_value = MagicMock()
            mock_ssl.SSLContext.return_value.options = 0

            config = self.configuration
            config.logger = self.logger

            with self.assertLogs(level="INFO") as log_capture:
                context = hardened_ssl_context(
                    config,
                    'keyfile',
                    'certfile',
                    'dhparamsfile',
                    STRONG_TLS_CIPHERS,
                    STRONG_TLS_CURVES,
                    False,
                    True,
                    False
                )

                self.assertIsNotNone(context)
                mock_ssl.SSLContext.assert_called_once_with(1)
                mock_ssl.SSLContext.return_value.load_cert_chain.assert_called_once_with(
                    'certfile', 'keyfile'
                )
                self.assertTrue(
                    any("enforcing strong SSL/TLS connections" in msg
                        for msg in log_capture.output)
                )

    @unittest.skip("Fix this test and enable it")
    def test_hardened_ssl_context_options(self):
        """Test SSL context options are set correctly"""
        with patch('mig.shared.tlsserver.ssl') as mock_ssl:
            mock_ssl.PROTOCOL_SSLv23 = 1
            mock_ssl.SSLContext = MagicMock()
            mock_ssl.SSLContext.return_value = MagicMock()
            mock_ssl.SSLContext.return_value.options = 0

            config = self.configuration
            config.logger = self.logger

            context = hardened_ssl_context(
                config,
                'keyfile',
                'certfile',
                'dhparamsfile',
                STRONG_TLS_CIPHERS,
                STRONG_TLS_CURVES,
                False,
                True,
                False
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
                getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000)
            )
            # Verify the options were OR'd into the context
            mock_ssl.SSLContext.return_value.options |= expected_options
            self.assertEqual(
                mock_ssl.SSLContext.return_value.options, expected_options)

    def test_hardened_ssl_context_ciphers(self):
        """Test SSL context ciphers are set correctly"""
        with patch('mig.shared.tlsserver.ssl') as mock_ssl:
            mock_ssl.PROTOCOL_SSLv23 = 1
            mock_ssl.SSLContext = MagicMock()
            mock_ssl.SSLContext.return_value = MagicMock()
            mock_ssl.SSLContext.return_value.options = 0

            config = self.configuration
            config.logger = self.logger

            context = hardened_ssl_context(
                config,
                'keyfile',
                'certfile',
                'dhparamsfile',
                STRONG_TLS_CIPHERS,
                STRONG_TLS_CURVES,
                False,
                True,
                False
            )

            mock_ssl.SSLContext.return_value.set_ciphers.assert_called_once_with(
                STRONG_TLS_CIPHERS)

    def test_hardened_ssl_context_legacy_ciphers(self):
        """Test SSL context ciphers are set correctly"""
        with patch('mig.shared.tlsserver.ssl') as mock_ssl:
            mock_ssl.PROTOCOL_SSLv23 = 1
            mock_ssl.SSLContext = MagicMock()
            mock_ssl.SSLContext.return_value = MagicMock()
            mock_ssl.SSLContext.return_value.options = 0

            config = self.configuration
            config.logger = self.logger

            context = hardened_ssl_context(
                config,
                'keyfile',
                'certfile',
                'dhparamsfile',
                STRONG_TLS_LEGACY_CIPHERS,
                STRONG_TLS_CURVES,
                False,
                True,
                False
            )

            mock_ssl.SSLContext.return_value.set_ciphers.assert_called_once_with(
                STRONG_TLS_LEGACY_CIPHERS)

    @unittest.skipIf(OpenSSL is None, "requires PyOpenSSL")
    def test_hardened_openssl_context_basic(self):
        """Test basic OpenSSL context creation with default parameters"""
        with patch('mig.shared.tlsserver.OpenSSL') as mock_openssl:
            mock_openssl.SSL = MagicMock()
            mock_openssl.SSL.SSLv23_METHOD = 1
            mock_openssl.SSL.Context = MagicMock()
            mock_openssl.SSL.Context.return_value = MagicMock()
            mock_openssl.SSL.Context.return_value.set_options = MagicMock()
            mock_openssl.crypto = MagicMock()

            config = self.configuration
            config.logger = self.logger

            with self.assertLogs(level="INFO") as log_capture:
                context = hardened_openssl_context(
                    config,
                    mock_openssl,
                    'keyfile',
                    'certfile',
                    'cacertfile',
                    'dhparamsfile',
                    STRONG_TLS_CIPHERS,
                    STRONG_TLS_CURVES,
                    False,
                    True,
                    False
                )

                self.assertIsNotNone(context)
                mock_openssl.SSL.Context.assert_called_once_with(1)
                mock_openssl.SSL.Context.return_value.use_certificate_chain_file.assert_called_once_with(
                    'certfile'
                )
                mock_openssl.SSL.Context.return_value.use_privatekey_file.assert_called_once_with(
                    'keyfile'
                )
                self.assertTrue(
                    any("enforcing strong SSL/TLS connections" in msg
                        for msg in log_capture.output)
                )

    @unittest.skipIf(OpenSSL is None, "requires PyOpenSSL")
    def test_hardened_openssl_context_options(self):
        """Test OpenSSL context options are set correctly"""
        with patch('mig.shared.tlsserver.OpenSSL') as mock_openssl:
            mock_openssl.SSL = MagicMock()
            mock_openssl.SSL.SSLv23_METHOD = 1
            mock_openssl.SSL.Context = MagicMock()
            mock_openssl.SSL.Context.return_value = MagicMock()
            mock_openssl.SSL.Context.return_value.set_options = MagicMock()
            mock_openssl.crypto = MagicMock()

            config = self.configuration
            config.logger = self.logger

            context = hardened_openssl_context(
                config,
                mock_openssl,
                'keyfile',
                'certfile',
                'cacertfile',
                'dhparamsfile',
                STRONG_TLS_CIPHERS,
                STRONG_TLS_CURVES,
                False,
                True,
                False
            )

            # Verify options are set
            expected_options = (
                getattr(mock_openssl.SSL, 'OP_NO_SSLv2', 0x1000000) |
                getattr(mock_openssl.SSL, 'OP_NO_SSLv3', 0x2000000) |
                getattr(mock_openssl.SSL, 'OP_NO_TLSv1', 0x4000000) |
                getattr(mock_openssl.SSL, 'OP_NO_TLSv1_1', 0x10000000) |
                getattr(mock_openssl.SSL, 'OP_NO_COMPRESSION', 0x20000) |
                getattr(mock_openssl.SSL, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
                getattr(mock_openssl.SSL, 'OP_SINGLE_ECDH_USE', 0x80000) |
                getattr(mock_openssl.SSL, 'OP_SINGLE_DH_USE', 0x100000)
            )
            mock_openssl.SSL.Context.return_value.set_options.assert_called_once_with(
                expected_options)

    @unittest.skipIf(OpenSSL is None, "requires PyOpenSSL")
    def test_hardened_openssl_context_ciphers(self):
        """Test OpenSSL context ciphers are set correctly"""
        with patch('mig.shared.tlsserver.OpenSSL') as mock_openssl:
            mock_openssl.SSL = MagicMock()
            mock_openssl.SSL.SSLv23_METHOD = 1
            mock_openssl.SSL.Context = MagicMock()
            mock_openssl.SSL.Context.return_value = MagicMock()
            mock_openssl.SSL.Context.return_value.set_options = MagicMock()
            mock_openssl.crypto = MagicMock()

            config = self.configuration
            config.logger = self.logger

            context = hardened_openssl_context(
                config,
                mock_openssl,
                'keyfile',
                'certfile',
                'cacertfile',
                'dhparamsfile',
                STRONG_TLS_CIPHERS,
                STRONG_TLS_CURVES,
                False,
                True,
                False
            )

            mock_openssl.SSL.Context.return_value.set_cipher_list.assert_called_once_with(
                STRONG_TLS_CIPHERS
            )

    @unittest.skipIf(OpenSSL is None, "requires PyOpenSSL")
    def test_hardened_openssl_context_cacertfile(self):
        """Test OpenSSL context handles cacertfile parameter"""
        with patch('mig.shared.tlsserver.OpenSSL') as mock_openssl:
            mock_openssl.SSL = MagicMock()
            mock_openssl.SSL.SSLv23_METHOD = 1
            mock_openssl.SSL.Context = MagicMock()
            mock_openssl.SSL.Context.return_value = MagicMock()
            mock_openssl.SSL.Context.return_value.set_options = MagicMock()
            mock_openssl.crypto = MagicMock()

            config = self.configuration
            config.logger = self.logger

            context = hardened_openssl_context(
                config,
                mock_openssl,
                'keyfile',
                'certfile',
                'cacertfile',
                'dhparamsfile',
                STRONG_TLS_CIPHERS,
                STRONG_TLS_CURVES,
                False,
                True,
                False
            )

            mock_openssl.SSL.Context.return_value.load_verify_locations.assert_called_once_with(
                'cacertfile'
            )

    @unittest.skipIf(OpenSSL is None, "requires PyOpenSSL")
    def test_hardened_openssl_context_dhparams(self):
        """Test OpenSSL context handles dhparamsfile parameter"""
        with patch('mig.shared.tlsserver.OpenSSL') as mock_openssl:
            mock_openssl.SSL = MagicMock()
            mock_openssl.SSL.SSLv23_METHOD = 1
            mock_openssl.SSL.Context = MagicMock()
            mock_openssl.SSL.Context.return_value = MagicMock()
            mock_openssl.SSL.Context.return_value.set_options = MagicMock()
            mock_openssl.crypto = MagicMock()

            config = self.configuration
            config.logger = self.logger

            context = hardened_openssl_context(
                config,
                mock_openssl,
                'keyfile',
                'certfile',
                'cacertfile',
                'dhparamsfile',
                STRONG_TLS_CIPHERS,
                STRONG_TLS_CURVES,
                False,
                True,
                False
            )

            mock_openssl.SSL.Context.return_value.load_tmp_dh.assert_called_once_with(
                'dhparamsfile'
            )
