# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_accountstate - unit test of the corresponding mig shared module
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

"""Unit tests for the mig shared accountstate module"""

import time

from mig.shared.accountstate import (
    default_account_valid_days,
    default_account_expire,
)
from mig.shared.defaults import (
    AUTH_CERTIFICATE,
    AUTH_OPENID_V2,
    AUTH_OPENID_CONNECT,
    AUTH_GENERIC,
)

from tests.support import MigTestCase


class TestMigSharedAccountstate__default_account_valid_days(MigTestCase):
    """Coverage of accountstate default_account_valid_days function."""

    def _provide_configuration(self):
        return "testconfig"

    def test_returns_cert_valid_days_for_certificate_auth(self):
        """Test that cert_valid_days is returned for AUTH_CERTIFICATE."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        result = default_account_valid_days(configuration, AUTH_CERTIFICATE)
        self.assertEqual(result, 365)

    def test_returns_oid_valid_days_for_openid_v2_auth(self):
        """Test that oid_valid_days is returned for AUTH_OPENID_V2."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        result = default_account_valid_days(configuration, AUTH_OPENID_V2)
        self.assertEqual(result, 30)

    def test_returns_oidc_valid_days_for_openid_connect_auth(self):
        """Test that oidc_valid_days is returned for AUTH_OPENID_CONNECT."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        result = default_account_valid_days(configuration, AUTH_OPENID_CONNECT)
        self.assertEqual(result, 30)

    def test_returns_generic_valid_days_for_generic_auth(self):
        """Test that generic_valid_days is returned for AUTH_GENERIC."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        result = default_account_valid_days(configuration, AUTH_GENERIC)
        self.assertEqual(result, 14)

    def test_returns_generic_valid_days_for_unknown_auth_type(self):
        """Test that generic_valid_days is fallback for unknown auth type."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        result = default_account_valid_days(configuration, "UNKNOWN_AUTH_TYPE")
        self.assertEqual(result, 14)


class TestMigSharedAccountstate__default_account_expire(MigTestCase):
    """Coverage of accountstate default_account_expire function."""

    def _provide_configuration(self):
        return "testconfig"

    def test_calculates_expire_from_valid_days(self):
        """Test that expire is calculated correctly from valid days."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        start_time = time.time()
        result = default_account_expire(configuration, AUTH_CERTIFICATE,
                                        start_time=start_time)
        expected = int(start_time + 365 * 24 * 60 * 60)
        self.assertEqual(result, expected)

    def test_calculates_expire_for_openid_v2(self):
        """Test expire calculation for AUTH_OPENID_V2."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        start_time = time.time()
        result = default_account_expire(configuration, AUTH_OPENID_V2,
                                        start_time=start_time)
        expected = int(start_time + 30 * 24 * 60 * 60)
        self.assertEqual(result, expected)

    def test_calculates_expire_for_openid_connect(self):
        """Test expire calculation for AUTH_OPENID_CONNECT."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        start_time = time.time()
        result = default_account_expire(configuration, AUTH_OPENID_CONNECT,
                                        start_time=start_time)
        expected = int(start_time + 30 * 24 * 60 * 60)
        self.assertEqual(result, expected)

    def test_calculates_expire_for_generic_auth(self):
        """Test expire calculation for AUTH_GENERIC."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        start_time = time.time()
        result = default_account_expire(configuration, AUTH_GENERIC,
                                        start_time=start_time)
        expected = int(start_time + 14 * 24 * 60 * 60)
        self.assertEqual(result, expected)

    def test_uses_current_time_if_start_time_not_provided(self):
        """Test that current time is used when start_time is not provided."""
        configuration = self.configuration
        configuration.cert_valid_days = 365
        configuration.oid_valid_days = 30
        configuration.oidc_valid_days = 30
        configuration.generic_valid_days = 14

        before = int(time.time())
        result = default_account_expire(configuration, AUTH_CERTIFICATE)
        after = int(time.time())

        # Result should be between before + 365 days and after + 365 days
        min_expected = before + 365 * 24 * 60 * 60
        max_expected = after + 365 * 24 * 60 * 60
        self.assertTrue(min_expected <= result <= max_expected)


if __name__ == "__main__":
    from tests.support import testmain
    testmain()
