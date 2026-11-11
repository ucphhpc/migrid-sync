from datetime import datetime
from typing import Any

from mig.lib.accountreqs import AccountRequest, AccountRequestRepository
from mig.lib.peers.storage import (
    add_accepted_peers_to_client,
    add_pending_peers_to_client,
    list_peers_requested,
)
from mig.shared.pwcrypto import make_hash, scramble_password
from tests.support import MigTestCase
from tests.support.usersupp import UserAssertMixin
from tests.support.wsgisupp import WsgiAssertMixin

TEST_SALT = "12345678"
TEST_PASSWORD = "password"
TEST_PASSWORD_SCRAMBLE = str(scramble_password(TEST_SALT, TEST_PASSWORD))
TEST_PASSWORD_HASH = make_hash(TEST_PASSWORD)
TEST_PEER_CONTACT_CLIENT_ID = "/C=DK/ST=NA/L=NA/O=Organization/OU=Unit/CN=Peer Contact Full Name/emailAddress=peer@unit.organization.edu"
TEST_ADMIN_CLIENT_ID = "/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=admin@example.com"
TEST_NONADMIN_CLIENT_ID = "/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=nonadmin@example.com"


test_account_request = AccountRequest(
    comment="A comment",
    country="DK",
    created=datetime(2020, 1, 1, 12, 0, 0),
    email="external@example.com",
    expire=datetime(2021, 1, 1, 12, 0, 0),
    full_name="Full Name",
    locality="NA",
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


class AccountRequestAPITestCase(MigTestCase, UserAssertMixin):

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        # We disable the csrf check this piece of testing
        # since we only care about functionality here
        self.configuration.site_csrf_protection = "MINIMAL"
        self.configuration.admin_list = [TEST_ADMIN_CLIENT_ID]
        self._provision_test_users(
            self,
            TEST_ADMIN_CLIENT_ID,
            TEST_PEER_CONTACT_CLIENT_ID,
            TEST_NONADMIN_CLIENT_ID,
        )


class TestPostForward(AccountRequestAPITestCase, WsgiAssertMixin):

    def _request_wsgi_post_forward(
        self, accreq_ids: list[str], mig_user_dn: str = TEST_ADMIN_CLIENT_ID
    ) -> Any:
        request_body = {
            "type": "accountrequests__forward",
            "operation": "create",
            "account_request_ids": accreq_ids,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=mig_user_dn,
        )
        return self.assertWsgiJsonResponse(prepared_wsgi)

    def test_permission_denied_when_not_on_admin_list(self) -> None:
        actual = self._request_wsgi_post_forward(
            [], mig_user_dn=TEST_NONADMIN_CLIENT_ID
        )
        expected = {
            "status": 403,
            "error": "you are not permitted to manage peers",
            "data": {},
        }

        self.assertEqual(actual, expected)

    def test_returns_expected_success(self) -> None:
        accreq_repo = AccountRequestRepository(self.configuration)
        accreq_forward = test_account_request.copy()
        accreq_id = accreq_repo.save(accreq_forward)

        json_response = self._request_wsgi_post_forward([accreq_id])

        status = json_response["status"]
        actual = json_response["data"]
        expected = {"errors": {}, "successes": [accreq_id]}
        self.assertEqual(status, 200)
        self.assertEqual(actual, expected)

    def test_adds_pending_peer_to_peer_contact(self) -> None:
        accreq_repo = AccountRequestRepository(self.configuration)
        accreq_forward = test_account_request.copy()
        accreq_id = accreq_repo.save(accreq_forward)

        json_response = self._request_wsgi_post_forward([accreq_id])
        actual = list_peers_requested(
            self.configuration, TEST_PEER_CONTACT_CLIENT_ID
        )

        expected = [accreq_forward.to_dict()]
        status = json_response["status"]
        self.assertEqual(status, 200)
        self.assertEqual(actual, expected)


class TestGetSummary(AccountRequestAPITestCase, WsgiAssertMixin):

    def _request_wsgi_get_summary(
        self, mig_user_dn: str = TEST_ADMIN_CLIENT_ID
    ) -> Any:
        request_body = {
            "type": "accountrequests__summary",
            "operation": "read",
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=mig_user_dn,
        )
        return self.assertWsgiJsonResponse(prepared_wsgi)

    def test_permission_denied_when_not_on_admin_list(self) -> None:
        actual = self._request_wsgi_get_summary(
            mig_user_dn=TEST_NONADMIN_CLIENT_ID
        )
        expected = {
            "status": 403,
            "error": "you are not permitted to manage peers",
            "data": {},
        }

        self.assertEqual(actual, expected)

    def test_returns_all_zeroes_if_no_account_requests_created(self):
        json_response = self._request_wsgi_get_summary()

        status = json_response["status"]
        actual = json_response["data"]
        expected = {
            "summary": {
                "invalid_peer_contact": 0,
                "requested": 0,
                "peer_pending": 0,
                "peer_accepted": 0,
            }
        }
        self.assertEqual(status, 200)
        self.assertEqual(actual, expected)

    def test_returns_expected_invalid_peer_contact(self):
        accreq_repo = AccountRequestRepository(self.configuration)
        accreq_peer_contact_invalid = test_account_request.copy()
        accreq_peer_contact_invalid.peers_email = (
            "invalid-peer-email@example.com"
        )
        accreq_peer_contact_invalid.email = "peer_contact_invalid@example.com"
        accreq_repo.save(accreq_peer_contact_invalid)

        json_response = self._request_wsgi_get_summary()

        status = json_response["status"]
        actual = json_response["data"]
        expected = {
            "summary": {
                "invalid_peer_contact": 1,
                "requested": 0,
                "peer_pending": 0,
                "peer_accepted": 0,
            }
        }
        self.assertEqual(status, 200)
        self.assertEqual(actual, expected)

    def test_returns_expected_requested(self):
        accreq_repo = AccountRequestRepository(self.configuration)
        # create an account request that should be left as requested
        accreq_requested = test_account_request.copy()
        accreq_requested.email = "accreq_requested@example.com"
        accreq_repo.save(accreq_requested)

        json_response = self._request_wsgi_get_summary()

        status = json_response["status"]
        actual = json_response["data"]
        expected = {
            "summary": {
                "invalid_peer_contact": 0,
                "requested": 1,
                "peer_pending": 0,
                "peer_accepted": 0,
            }
        }
        self.assertEqual(status, 200)
        self.assertEqual(actual, expected)

    def test_returns_expected_peer_pending(self):
        accreq_repo = AccountRequestRepository(self.configuration)
        # create an account request that should be set as peer pending
        accreq_peer_pending = test_account_request.copy()
        accreq_peer_pending.email = "peer_pending@example.com"
        accreq_repo.save(accreq_peer_pending)
        add_pending_peers_to_client(
            self.configuration,
            TEST_PEER_CONTACT_CLIENT_ID,
            [
                (
                    accreq_peer_pending.distinguished_name,
                    accreq_peer_pending.to_dict(),
                )
            ],
        )

        json_response = self._request_wsgi_get_summary()

        status = json_response["status"]
        actual = json_response["data"]
        expected = {
            "summary": {
                "invalid_peer_contact": 0,
                "requested": 0,
                "peer_pending": 1,
                "peer_accepted": 0,
            }
        }
        self.assertEqual(status, 200)
        self.assertEqual(actual, expected)

    def test_returns_expected_peer_accepted(self):
        accreq_repo = AccountRequestRepository(self.configuration)
        # create an account request that should be set as peer accepted
        accreq_peer_accepted = test_account_request.copy()
        accreq_peer_accepted.email = "accreq_peer_accepted@example.com"
        accreq_repo.save(accreq_peer_accepted)
        add_accepted_peers_to_client(
            self.configuration,
            TEST_PEER_CONTACT_CLIENT_ID,
            {
                accreq_peer_accepted.distinguished_name: accreq_peer_accepted.to_dict()
            },
        )

        json_response = self._request_wsgi_get_summary()

        status = json_response["status"]
        actual = json_response["data"]
        expected = {
            "summary": {
                "invalid_peer_contact": 0,
                "requested": 0,
                "peer_pending": 0,
                "peer_accepted": 1,
            }
        }
        self.assertEqual(status, 200)
        self.assertEqual(actual, expected)
