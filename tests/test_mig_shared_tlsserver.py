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

# Imports of the code under test
from mig.shared.tlsserver import hardened_ssl_context, ssl
# Imports required for the unit test wrapping
from mig.shared.defaults import STRONG_TLS_CIPHERS, STRONG_TLS_LEGACY_CIPHERS, \
    STRONG_TLS_CURVES
# Imports required for the unit tests themselves
from tests.support import MigTestCase

TEST_KEY_FILE = "testkey.pem"
TEST_CERT_FILE = "testcert.pem"
TEST_CACERT_FILE = "testcacert.pem"
TEST_DHPARAMS_FILE = "testdhparams.pem"
# IMPORTANT: this is a BOGUS key + self-signed cert, ONLY ever use for testing!
TEST_HOST_KEY = """-----BEGIN PRIVATE KEY-----
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
Q+9V137S6RHzVn2s58Ta5ECTyD2oQw==
-----END PRIVATE KEY-----"""
TEST_HOST_CERT = """-----BEGIN CERTIFICATE-----
MIIF7zCCA9egAwIBAgIUPoT2V+/Y/5RnBQtwYkA9VLSyfYYwDQYJKoZIhvcNAQEL
BQAwgYYxCzAJBgNVBAYTAlhYMRIwEAYDVQQIDAlTdGF0ZU5hbWUxETAPBgNVBAcM
CENpdHlOYW1lMRQwEgYDVQQKDAtDb21wYW55TmFtZTEbMBkGA1UECwwSQ29tcGFu
eVNlY3Rpb25OYW1lMR0wGwYDVQQDDBRDb21tb25OYW1lT3JIb3N0bmFtZTAeFw0y
NjAzMTYxODI2MzlaFw0zNjAzMTMxODI2MzlaMIGGMQswCQYDVQQGEwJYWDESMBAG
A1UECAwJU3RhdGVOYW1lMREwDwYDVQQHDAhDaXR5TmFtZTEUMBIGA1UECgwLQ29t
cGFueU5hbWUxGzAZBgNVBAsMEkNvbXBhbnlTZWN0aW9uTmFtZTEdMBsGA1UEAwwU
Q29tbW9uTmFtZU9ySG9zdG5hbWUwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIK
AoICAQCWcP0X6VRv06tOKgD+gjvj0Cq8OQDJFHaQlOiXz90bjhc9ECtA/sj/3RUW
imy3kppRkO40Adrdz2AZUa6h/WDVcCvMDYpLSlERcZFRLnWWMFRj2xoRvOhJr/EF
TTuEgA4KFhQX48Kv6LzN2SEdLIFced90PL7oRBmyM2REwav4FvvT7Wv7dF5rW5w0
mev8qAOkQj8ky/DjMi2kxKPbH4q+Jlj8SC6MB4hFvbhhHOMtyLhIUnl+b+OqfoNi
qU6omKN05VbPnp2zKSmxPSSGvZdoc2dvq+6dXqSPCoznO3sXhofTrbKaMs/qQ7Fr
7KVWdM9D7uQRt1Thhwf3H/UUOf+mmfPFuSX1KRogkHU5U1SxLaXQF/07sEqebiN/
vQ9GuRjpfkwq4Kif5Q0l2wq59K+GzcK4mhz/ky1cGNuhxI05VqIbKDyRYcIzh+uC
Dup2Lgvw6eFvBiglccte1fFKZChbp1QS41REha0+6z0ZtujachzkBr+42Ew65ngt
e3OAN50bHtt682z2pSvy4KrEfWxEym6iN6ygKPDWHLPP0T0bFN7Lu9AOVnnZJFVa
fz4XoB2IBukpHZdFIQ8K9MlGWwF7iZZQjatiHJzsIOAr28TkjY3P3PpdnZtCeBIf
9ywjvXr8TOC0jHKxlOxouU3DN9jDqbfXFdcIYDfsmz3z9SO4WQIDAQABo1MwUTAd
BgNVHQ4EFgQU0gUTveqi67vp3Folx6KDoZtWum4wHwYDVR0jBBgwFoAU0gUTveqi
67vp3Folx6KDoZtWum4wDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOC
AgEAIlZ1ONQcruIU7JZXryc3/0SwsiXsxqiS+Eg7Qx5Am6JdPL2tLeQ9DHDRJ1F1
/5JY7BU+fI+Hhe9XO3TArEmkSuJH2eEkMQcLQTP30nttvIO1haJn+6wf5nt4KNdy
qCywN/Om6n2kewNCEbDaSNm4S/dN+oCbdANobZmofawiDamb/MOG/leSNv8wN1GC
zCoFeH0rDf+ZAVN8xhqPe8+RPavT6BrWxBLjIR/52VwCrRiLLsCSt/WcdjYmOvSI
+s8qvaT4lrzS413+i7zDcNN+xPm7c1UP48myRTwT8a9hkn+0jwmL1CzYiW5kNuZx
HFuZ0gIelKc8IdFcOh5LWXS8b1Z4r+Vtx7WrcWmhJPoNTTtIm+IIF6ZyBtcrzVx5
ctTvs1KcIFeS4ROnXC3zfSvOeXtiIeuVbiDXtcESmsXiCe9qS/j7KPbyVfel2Bwh
kVmbvoxMYZQYxQB5kROEem5zMGjPSDvCxUGljlwhzFvGkXocnC9Q5Mi61sMkAlyg
UPrFPCy8BqR4ZvZTvjtxMF81ahq2t+fmj8QeG1o0mSnH/Q3lP7vn7xSjZTu5+ldc
haiaED1TUyXIyHyn/L+NJmbdcbfPebvrv7KYdtxTC9j47kwWdkSuWMEW1pMTPM9W
EthFXgjAdlUayA5VqbcWIdm/P4d5Wc5lgj2XlbcwREcktT4=
-----END CERTIFICATE-----"""


class MigSharedTlsServer(MigTestCase):
    """Unit tests for tlsserver related helper functions using proper TLS"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    # TODO: move the key+cert e.g. to data/X with helper function to load them?
    def _prepare_key_cert(self, key_path, cert_path):
        """Save key and cert file for use in real ssl tests"""
        with open(key_path, 'w') as key_fd:
            key_fd.write(TEST_HOST_KEY)
        with open(cert_path, 'w') as cert_fd:
            cert_fd.write(TEST_HOST_CERT)

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        self._prepare_key_cert(TEST_KEY_FILE, TEST_CERT_FILE)

    def test_hardened_ssl_context_options_default(self):
        """Test SSL context options are set correctly"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_FILE,
            TEST_CERT_FILE,
            None,
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
            getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000) |
            getattr(ssl, 'OP_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        self.assertEqual(context.options & expected_options, expected_options)

    def test_hardened_ssl_context_options_tls1_1_only(self):
        """Test SSL context options are set correctly with TLS 1.1 only"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_FILE,
            TEST_CERT_FILE,
            None,
            STRONG_TLS_CIPHERS,
            STRONG_TLS_CURVES,
            True,
            False,
            False
        )

        # Verify options are set
        expected_options = (
            getattr(ssl, 'OP_NO_SSLv2', 0x1000000) |
            getattr(ssl, 'OP_NO_SSLv3', 0x2000000) |
            getattr(ssl, 'OP_NO_TLSv1_2', 0x8000000) |
            getattr(ssl, 'OP_NO_COMPRESSION', 0x20000) |
            getattr(ssl, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000) |
            getattr(ssl, 'OP_SINGLE_ECDH_USE', 0x80000) |
            getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000) |
            getattr(ssl, 'OP_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        self.assertEqual(context.options & expected_options, expected_options)

    def test_hardened_ssl_context_options_tls1_3_only(self):
        """Test SSL context options are set correctly with TLS 1.3 only"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_FILE,
            TEST_CERT_FILE,
            None,
            STRONG_TLS_CIPHERS,
            STRONG_TLS_CURVES,
            False,
            False,
            False
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
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000) |
            getattr(ssl, 'OP_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        self.assertEqual(context.options & expected_options, expected_options)

    def test_hardened_ssl_context_options_fail_reneg(self):
        """Test SSL context options fail when different"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_FILE,
            TEST_CERT_FILE,
            None,
            STRONG_TLS_CIPHERS,
            STRONG_TLS_CURVES,
            False,
            True,
            True
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
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000) |
            getattr(ssl, 'OP_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        self.assertNotEqual(
            context.options & expected_options, expected_options)

    def test_hardened_ssl_context_options_fail_tls1_1(self):
        """Test SSL context options fail when different"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_FILE,
            TEST_CERT_FILE,
            None,
            STRONG_TLS_CIPHERS,
            STRONG_TLS_CURVES,
            True,
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
            getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000) |
            getattr(ssl, 'OP_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        self.assertNotEqual(
            context.options & expected_options, expected_options)

    def test_hardened_ssl_context_options_fail_tls1_2(self):
        """Test SSL context options fail when different"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_FILE,
            TEST_CERT_FILE,
            None,
            STRONG_TLS_CIPHERS,
            STRONG_TLS_CURVES,
            True,
            False,
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
            getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000) |
            getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000) |
            getattr(ssl, 'OP_RENEGOTIATION', 0x40000000)
        )

        # Verify the options were OR'd into the context
        self.assertNotEqual(
            context.options & expected_options, expected_options)

    def test_hardened_ssl_context_ciphers(self):
        """Test SSL context ciphers are set correctly"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_FILE,
            TEST_CERT_FILE,
            None,
            STRONG_TLS_CIPHERS,
            STRONG_TLS_CURVES,
            False,
            True,
            False
        )
        # NOTE: this may be too platform specific
        expected_start = "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:"
        expected_end = ":DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384"
        result = ':'.join([spec['name'] for spec in context.get_ciphers()])
        self.assertTrue(result.startswith(expected_start))
        self.assertTrue(result.endswith(expected_end))

    def test_hardened_ssl_context_legacy_ciphers(self):
        """Test SSL context legacy ciphers are set correctly"""
        config = self.configuration
        config.logger = self.logger

        context = hardened_ssl_context(
            config,
            TEST_KEY_FILE,
            TEST_CERT_FILE,
            None,
            STRONG_TLS_LEGACY_CIPHERS,
            STRONG_TLS_CURVES,
            False,
            True,
            False
        )
        # NOTE: this may be too platform specific
        expected_start = "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:"
        expected_end = ":CAMELLIA256-SHA256:CAMELLIA128-SHA256"
        result = ':'.join([spec['name'] for spec in context.get_ciphers()])
        self.assertTrue(result.startswith(expected_start))
        self.assertTrue(result.endswith(expected_end))
