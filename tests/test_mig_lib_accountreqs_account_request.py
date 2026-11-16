#
# --- BEGIN_HEADER ---
#
# test_mig_lib_accountreqs_account_request - account requests record unit tests
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
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# --- END_HEADER ---
#

from datetime import datetime

from mig.lib.accountreqs import AccountRequest
from mig.shared.pwcrypto import make_hash, scramble_password
from tests.support import MigTestCase

TEST_SALT = "12345678"
TEST_PASSWORD = "password"
TEST_PASSWORD_SCRAMBLE = str(scramble_password(TEST_SALT, TEST_PASSWORD))
TEST_PASSWORD_HASH = make_hash(TEST_PASSWORD)

test_account_request = AccountRequest(
    comment="A comment",
    country="DK",
    created=datetime(2020, 1, 1, 12, 0, 0),
    email="external@example.com",
    expire=datetime(2021, 1, 1, 12, 0, 0),
    full_name="Full Name",
    locality="Copenhagen",
    openid_names=[],
    organization="Organization",
    organizational_unit="Unit",
    path="",
    password=TEST_PASSWORD_SCRAMBLE,
    password_hash=TEST_PASSWORD_HASH,
    peers_email="peer@unit.organization.edu",
    peers_full_name="Peer Contact Full Name",
    state="NA",
)


class TestToDict(MigTestCase):
    def test_returns_expected_dictionary(self) -> None:
        accreq = test_account_request.copy()

        actual = accreq.to_dict()
        expected = {
            "comment": "A comment",
            "country": "DK",
            "created": datetime(2020, 1, 1, 12, 0, 0).timestamp(),
            "distinguished_name": "/C=DK/ST=NA/L=Copenhagen/O=Organization/OU=Unit/CN=Full Name/emailAddress=external@example.com",
            "email": "external@example.com",
            "expire": datetime(2021, 1, 1, 12, 0, 0).timestamp(),
            "full_name": "Full Name",
            "locality": "Copenhagen",
            "openid_names": [],
            "organization": "Organization",
            "organizational_unit": "Unit",
            "path": "",
            "password": TEST_PASSWORD_SCRAMBLE,
            "password_hash": TEST_PASSWORD_HASH,
            "peers_email": "peer@unit.organization.edu",
            "peers_full_name": "Peer Contact Full Name",
            "state": "NA",
        }

        self.assertEqual(actual, expected)


class TestCopy(MigTestCase):
    def test_result_is_equal(self) -> None:
        actual = test_account_request.copy()
        self.assertEqual(actual, test_account_request)

    def test_result_is_not_same_id(self) -> None:
        actual = test_account_request.copy()
        self.assertNotEqual(id(actual), id(test_account_request))


class TestFromDict(MigTestCase):
    def test_returns_expected_account_request(self) -> None:
        actual = AccountRequest.from_dict(
            {
                "comment": "A comment",
                "country": "DK",
                "created": datetime(2020, 1, 1, 12, 0, 0).timestamp(),
                "distinguished_name": "/C=DK/ST=NA/L=Copenhagen/O=Organization/OU=Unit/CN=Full Name/emailAddress=external@example.com",
                "email": "external@example.com",
                "expire": datetime(2021, 1, 1, 12, 0, 0).timestamp(),
                "full_name": "Full Name",
                "locality": "Copenhagen",
                "openid_names": [],
                "organization": "Organization",
                "organizational_unit": "Unit",
                "path": "",
                "password": TEST_PASSWORD_SCRAMBLE,
                "password_hash": TEST_PASSWORD_HASH,
                "peers_email": "peer@unit.organization.edu",
                "peers_full_name": "Peer Contact Full Name",
                "state": "NA",
            }
        )

        expected = test_account_request.copy()
        self.assertEqual(actual, expected)

    def test_returns_none_if_missing_fields(self) -> None:
        actual = AccountRequest.from_dict(
            {
                "comment": "A comment",
                "country": "DK",
                "created": datetime(2020, 1, 1, 12, 0, 0).timestamp(),
                "distinguished_name": "/C=DK/ST=NA/L=Copenhagen/O=Organization/OU=Unit/CN=Full Name/emailAddress=external@example.com",
                "email": "external@example.com",
                "expire": datetime(2021, 1, 1, 12, 0, 0).timestamp(),
                "full_name": "Full Name",
                "locality": "Copenhagen",
                # "openid_names": [],  # Missing field
                "organization": "Organization",
                "organizational_unit": "Unit",
                "path": "",
                "password": TEST_PASSWORD_SCRAMBLE,
                "password_hash": TEST_PASSWORD_HASH,
                "peers_email": "peer@unit.organization.edu",
                "peers_full_name": "Peer Contact Full Name",
                "state": "NA",
            }
        )

        self.assertIsNone(actual)


class TestFillDistinguishedName(MigTestCase):
    def test_returns_updated_distinguished_name(self):
        accreq = test_account_request.copy()
        accreq.email = "anotheremail@example.com"

        actual = accreq.distinguished_name

        expected = "/C=DK/ST=NA/L=Copenhagen/O=Organization/OU=Unit/CN=Full Name/emailAddress=anotheremail@example.com"
        not_expected = "/C=DK/ST=NA/L=Copenhagen/O=Organization/OU=Unit/CN=Full Name/emailAddress=external@example.com"
        self.assertEqual(actual, expected)
        self.assertNotEqual(actual, not_expected)

    def test_returns_expected_distinguished_name(self) -> None:
        accreq = test_account_request.copy()

        actual = accreq.distinguished_name

        expected = "/C=DK/ST=NA/L=Copenhagen/O=Organization/OU=Unit/CN=Full Name/emailAddress=external@example.com"
        self.assertEqual(actual, expected)

    def test_returns_expected_with_gdp(self) -> None:
        accreq = test_account_request.copy()
        accreq.gdp = "gdpval"

        actual = accreq.distinguished_name

        expected = "/C=DK/ST=NA/L=Copenhagen/O=Organization/OU=Unit/CN=Full Name/emailAddress=external@example.com/GDP=gdpval"
        self.assertEqual(actual, expected)


class TestToMaskedDict(MigTestCase):
    def test_credentials_are_masked(self) -> None:
        accreq = test_account_request.copy()

        actual = accreq.to_masked_dict()

        expected = accreq.to_dict() | {
            "password": "**HIDDEN**",
            "password_hash": "**HIDDEN**",
        }
        self.assertEqual(actual, expected)
