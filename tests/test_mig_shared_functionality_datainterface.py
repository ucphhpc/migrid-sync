# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_cat - unit test of the corresponding mig module
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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
from datetime import date, datetime, timedelta

from envhelp.makeconfig import _ensure_dirs_needed_for_userdb
from mig.shared.defaults import peers_expire_min_days
from tests.support import MigTestCase, testmain
from tests.support.fixturesupp import FixtureAssertMixin, fixturepath
from tests.support.picklesupp import PickleAssertMixin
from tests.support.usersupp import UserAssertMixin
from tests.support.wsgisupp import WsgiAssertMixin


def _only_output_objects(output_objects, with_object_type=None):
    return [o for o in output_objects if o["object_type"] == with_object_type]


class MigSharedFunctionalityDatainterface__generic(
    MigTestCase, WsgiAssertMixin
):
    """Tests of end to end generic behaviour of datainterface"""

    TEST_CLIENT_ID = "/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com"

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self._provision_test_user(self, self.TEST_CLIENT_ID)

    def test_wsgi_nonexistent_route(self):
        request_body = {
            "type": "__nonexistent",
            "operation": "create",
            "content": "insert me",
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 404)

        self.assertIn("error", json_response)
        self.assertEqual(
            json_response["error"],
            "the specified route package handler was not found",
        )


class MigSharedFunctionalityDatainterface__peers_wsgi(
    MigTestCase,
    WsgiAssertMixin,
    FixtureAssertMixin,
    PickleAssertMixin,
    UserAssertMixin,
):
    """Tests of the end to end peers behaviours of datainterface"""

    TEST_CLIENT_ID = "/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com"
    TEST_PEER_DN = "/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=peer@example.com"
    TEST_PENDING_PEER_DN = "/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Pending Peer User/emailAddress=pending_peer@example.com"

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        user_paths_dict = self._provision_test_user_return_dict(
            self,
            self.TEST_CLIENT_ID,
        )
        self.test_user_settings_dir = user_paths_dict["user_settings_dir"]

    def assertPendingUsers(self, expected_count=0):
        user_pending_entries = os.listdir(self.configuration.user_pending)
        self.assertEqual(len(user_pending_entries), expected_count)
        return user_pending_entries

    def test_peers_new_with_missing_fields(self):
        # Because the peer is not created, we can't assume that the peers db is created
        self._provision_user_peers_empty(self.test_user_settings_dir)
        test_accepted_peer = {
            "country": "DK",
            "email": "peer@example.com",
            "full_name": "Test User",
            "organization": "Test Org",
            "state": "NA",
        }

        request_body = {
            "type": "peers__new",
            "operation": "create",
            **test_accepted_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        self.assertIn("status", json_response)
        status = json_response["status"]
        self.assertEqual(status, 400)

        # check we failed creation -> missing expire, kind, label
        self.assertIn("data", json_response)
        self.assertIn("errors_map", json_response["data"])

        # check we failed creation
        errors_map = json_response["data"]["errors_map"]
        self.assertEqual(
            errors_map,
            {
                "0": {
                    "expire": "expire is required but missing",
                    "kind": "kind is required but missing",
                    "label": "label is required but missing",
                }
            },
        )

        # check nothing was saved
        peers = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertEqual(peers, {})
        self.assertPendingUsers(expected_count=0)

    def test_peers_new_with_invalid_fields(self):
        # Because the peer is not created, we can't assume that the peers db is created
        self._provision_user_peers_empty(self.test_user_settings_dir)
        test_accepted_peer = {
            "country": "DK",
            "email": "peer@example.com",
            "full_name": "Test User",
            "organization": "Test Org",
            "state": "NA",
            "label": "some_peer_label",
            "kind": "not_a_valid_kind",
            "expire": 1234,
        }

        request_body = {
            "type": "peers__new",
            "operation": "create",
            **test_accepted_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 400)

        # check we failed creation
        errors_map = json_response["data"]["errors_map"]
        self.assertEqual(
            errors_map,
            {
                "0": {
                    "expire": "shorter than minimum length (10)",
                    "kind": "invalid peer kind",
                }
            },
        )

        # check nothing was saved
        peers = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertEqual(peers, {})
        self.assertPendingUsers(expected_count=0)

    def test_peers_new_valid(self):
        # Minimum expire is 7 days
        date_expire_in_8_days = date.today() + timedelta(days=8)
        test_new_accepted_peer = {
            "country": "DK",
            "email": "peer@example.com",
            "full_name": "Test User",
            "label": "some_peer_label",
            "expire": date_expire_in_8_days.isoformat(),
            "organization": "Test Org",
            "kind": "project",
            "state": "NA",
        }

        request_body = {
            "type": "peers__new",
            "operation": "create",
            "invite_on_email": True,
            **test_new_accepted_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        # Validate that the peer invitation email and admin notification email
        # were sent
        fake_send_email = self.configuration.context_get("notifier").send_email
        self.assertEqual(fake_send_email.total_emails_sent(), 2)
        self.assertTrue(fake_send_email.email_was_sent_to("peer@example.com"))
        self.assertTrue(fake_send_email.email_was_sent_to("admin@example.com"))

    def test_peers_new_with_too_short_expire(self):
        date_expire_in_3_days = date.today() + timedelta(days=3)
        test_accepted_peer = {
            "country": "DK",
            "email": "peer@example.com",
            "full_name": "Test User",
            "label": "some_peer_label",
            "expire": date_expire_in_3_days.isoformat(),
            "organization": "Test Org",
            "kind": "project",
            "state": "NA",
        }

        request_body = {
            "type": "peers__new",
            "operation": "create",
            "invite_on_email": True,
            **test_accepted_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        self.assertIn("status", json_response)
        status = json_response["status"]
        self.assertEqual(status, 400)

        # check we failed creation due to expire being too short
        self.assertIn("data", json_response)
        self.assertIn("errors_map", json_response["data"])
        errors_map = json_response["data"]["errors_map"]
        self.assertIn("0", errors_map)
        self.assertIn("expire", errors_map["0"])
        self.assertIn(
            "the specified expire must be atleast", errors_map["0"]["expire"]
        )

        # check nothing was saved
        self.assertPendingUsers(expected_count=0)

    def test_peers_new_with_too_long_expire(self):
        date_expire_in_4000_days = date.today() + timedelta(days=4000)
        test_accepted_peer = {
            "country": "DK",
            "email": "peer@example.com",
            "full_name": "Test User",
            "label": "some_peer_label",
            "expire": date_expire_in_4000_days.isoformat(),
            "organization": "Test Org",
            "kind": "project",
            "state": "NA",
        }

        request_body = {
            "type": "peers__new",
            "operation": "create",
            "invite_on_email": True,
            **test_accepted_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        self.assertIn("status", json_response)
        status = json_response["status"]
        self.assertEqual(status, 400)

        # check we failed creation due to expire being too long
        self.assertIn("data", json_response)
        self.assertIn("errors_map", json_response["data"])
        errors_map = json_response["data"]["errors_map"]
        self.assertIn("0", errors_map)
        self.assertIn("expire", errors_map["0"])
        self.assertIn(
            "the specified expire is too far in the future",
            errors_map["0"]["expire"],
        )

        # check nothing was saved
        self.assertPendingUsers(expected_count=0)

    def test_peers_new_valid_on_disk(self):
        # We don't want to test email sending here
        # just the correctness of the datastructure
        self.configuration.context_get("notifier").send_email.forgive_email()

        self._provision_user_peers_empty(self.test_user_settings_dir)
        date_expire_in_8_days = date.today() + timedelta(days=8)
        test_new_accepted_peer = {
            "country": "DK",
            "email": "peer@example.com",
            "full_name": "Test User",
            "label": "some_peer_label",
            "expire": date_expire_in_8_days.isoformat(),
            "organization": "Test Org",
            "kind": "project",
            "state": "NA",
        }

        request_body = {
            "type": "peers__new",
            "operation": "create",
            "invite_on_email": True,
            **test_new_accepted_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        peers = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertEqual(len(peers), 1)
        self.assertIn(self.TEST_PEER_DN, peers)

        peer = peers[self.TEST_PEER_DN]
        self.assertEqual(peer["distinguished_name"], self.TEST_PEER_DN)
        self.assertEqual(peer["full_name"], test_new_accepted_peer["full_name"])
        self.assertEqual(
            peer["organization"], test_new_accepted_peer["organization"]
        )
        self.assertEqual(peer["email"], test_new_accepted_peer["email"])
        self.assertEqual(peer["country"], test_new_accepted_peer["country"])
        self.assertEqual(peer["state"], test_new_accepted_peer["state"])
        self.assertEqual(peer["label"], test_new_accepted_peer["label"])
        self.assertEqual(peer["kind"], test_new_accepted_peer["kind"])
        self.assertEqual(peer["expire"], test_new_accepted_peer["expire"])

    def test_peers_summary(self):
        self._provision_peer_user(
            self, [self.TEST_PEER_DN], self.TEST_CLIENT_ID
        )

        request_body = {
            "type": "peers__summary",
            "operation": "read",
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        data = json_response["data"]
        self.assertEqual(
            data,
            {
                "accepted_count": 1,
                "requested_count": 0,
            },
        )

    def test_peers_accepted_delete(self):
        self._provision_peer_user(
            self, [self.TEST_PEER_DN], self.TEST_CLIENT_ID
        )

        test_accepted_peer = {
            "peers": [self.TEST_PEER_DN],
        }

        request_body = {
            "type": "peers__accepted__delete",
            "operation": "delete",
            **test_accepted_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        data = json_response["data"]
        self.assertEqual(
            data,
            {
                "success_map": {
                    "0": True,
                }
            },
        )

        # now check that the peer was removed
        content = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertEqual(len(content), 0)

        # check the email was sent
        fake_send_email = self.configuration.context_get("notifier").send_email
        self.assertTrue(fake_send_email.called_once)
        self.assertTrue(fake_send_email.email_was_sent_to("admin@example.com"))

    def test_peers_accepted_delete_invalid_dn(self):
        test_accepted_peer = {
            "peers": ["foo/bar/baz"],
        }

        request_body = {
            "type": "peers__accepted__delete",
            "operation": "delete",
            **test_accepted_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        self.assertIn("status", json_response)
        status = json_response["status"]
        self.assertEqual(status, 400)

        self.assertIn("error", json_response)
        error = json_response["error"]
        self.assertIsNotNone(error)
        self.assertNotEqual(error, "")

    def test_peers_accepted_fetch(self):
        self._provision_peer_user(
            self, [self.TEST_PEER_DN], self.TEST_CLIENT_ID
        )

        payload = {
            "peer_dn": self.TEST_PEER_DN,
        }

        request_body = {
            "type": "peers__accepted__fetch",
            "operation": "create",
            **payload,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        data = json_response["data"]
        self.assertEqual(data["distinguished_name"], self.TEST_PEER_DN)

    def test_peers_accepted_import(self):
        date_expire_in_8_days = date.today() + timedelta(days=8)
        peers_csv = fixturepath("csv/peers-for-import.csv")
        with open(peers_csv) as f:
            content = f.read()
        request_body = {
            "type": "peers__accepted__import",
            "operation": "create",
            "label": "some_peer_label",
            "kind": "collaboration",
            "expire": date_expire_in_8_days.isoformat(),
            "csvtext": content,
            "invite_on_email": True,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        # now check that peers were created
        content = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertEqual(len(content), 3)

        # check email were sent to each invited peer
        fake_send_email = self.configuration.context_get("notifier").send_email
        self.assertEqual(fake_send_email.total_emails_sent(), 4)

    def test_peers_accepted_update(self):
        date_expire_in_min = (
            date.today()
            + timedelta(days=peers_expire_min_days)
            + timedelta(days=1)
        )
        self._provision_peer_user(
            self, [self.TEST_PEER_DN], self.TEST_CLIENT_ID
        )

        new_label = "update_peer_label"
        new_expire = date_expire_in_min.isoformat()
        new_kind = ""
        payload = {
            "peer_dn": self.TEST_PEER_DN,
            "label": new_label,
            "kind": "",
            "expire": new_expire,
        }

        request_body = {
            "type": "peers__accepted__update",
            "operation": "create",
            **payload,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        # validate that the accepted peer was updated
        peers = self.assertUserPeers(self.TEST_CLIENT_ID)
        peer = peers.get(self.TEST_PEER_DN, None)
        self.assertIsNotNone(peer)

        self.assertEqual(peer["distinguished_name"], self.TEST_PEER_DN)
        self.assertIn("label", peer)
        self.assertEqual(peer["label"], new_label)
        self.assertIn("kind", peer)
        self.assertEqual(peer["kind"], new_kind)
        self.assertIn("expire", peer)
        self.assertEqual(peer["expire"], new_expire)

        # check emails were sent
        fake_send_email = self.configuration.context_get("notifier").send_email
        self.assertTrue(fake_send_email.email_was_sent_to("admin@example.com"))

    def test_peers_send_invitation_valid(self):
        self._provision_peer_user(
            self, [self.TEST_PEER_DN], self.TEST_CLIENT_ID
        )

        request_body = {
            "type": "peers__send_invitation",
            "operation": "create",
            "peers": [self.TEST_PEER_DN],
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)
        self.assertIn("peer_invitations", json_response["data"])
        self.assertTrue(
            json_response["data"]["peer_invitations"][self.TEST_PEER_DN]
        )

        fake_send_email = self.configuration.context_get("notifier").send_email
        self.assertEqual(fake_send_email.total_emails_sent(), 1)
        self.assertTrue(fake_send_email.email_was_sent_to("peer@example.com"))

    def test_peers_send_invitation_invalid_dn(self):
        request_body = {
            "type": "peers__send_invitation",
            "operation": "create",
            "peers": ["foo/bar/baz"],
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 400)
        self.assertIn("error", json_response)
        self.assertTrue(len(json_response["error"]) > 0)

    def test_peers_send_invitation_nonexistent_peer(self):
        non_existent_dn = "/C=DK/ST=NA/L=NA/O=Nonexistent/OU=NA/CN=Nonexistent Peer/emailAddress=nonexistent@example.com"

        request_body = {
            "type": "peers__send_invitation",
            "operation": "create",
            "peers": [non_existent_dn],
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 400)
        self.assertIn("error", json_response)
        self.assertTrue(len(json_response["error"]) > 0)

    def test_peers_send_invitation_multiple_peers(self):
        self._provision_peer_user(
            self, [self.TEST_PEER_DN], self.TEST_CLIENT_ID
        )

        request_body = {
            "type": "peers__send_invitation",
            "operation": "create",
            "peers": [self.TEST_PEER_DN],
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)
        self.assertIn("peer_invitations", json_response["data"])
        self.assertTrue(
            json_response["data"]["peer_invitations"][self.TEST_PEER_DN]
        )

        fake_send_email = self.configuration.context_get("notifier").send_email
        self.assertTrue(fake_send_email.email_was_sent_to("peer@example.com"))

    def test_peers_requsted_accept(self):
        _ensure_dirs_needed_for_userdb(self.configuration)
        self._record_pending_peer(
            self.TEST_PENDING_PEER_DN, self.TEST_CLIENT_ID
        )
        self.logger.declare_expected_error(
            comparison="startswith",
            expectation="expire '' could not be parsed into a valid date",
        )

        test_pending_peer = {
            "peers": [self.TEST_PENDING_PEER_DN],
        }

        request_body = {
            "type": "peers__requested__accept",
            "operation": "create",
            **test_pending_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        data = json_response["data"]
        self.assertEqual(data["success_map"], {"0": True})

        # now check that the peer was added
        user_peers = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertIn(self.TEST_PENDING_PEER_DN, user_peers)

        # check that the client pending peer is gone
        pending_peers = self.assertUserPendingPeers(self.TEST_CLIENT_ID)
        self.assertEqual(len(pending_peers), 0)

        # check emails were sent
        fake_send_email = self.configuration.context_get("notifier").send_email
        self.assertTrue(fake_send_email.email_was_sent_to("admin@example.com"))

    def test_peers_requested_accept_on_disk(self):
        # We don't want to test email sending here
        # just the correctness of the datastructure
        self.configuration.context_get("notifier").send_email.forgive_email()

        _ensure_dirs_needed_for_userdb(self.configuration)
        self._record_pending_peer(
            self.TEST_PENDING_PEER_DN, self.TEST_CLIENT_ID
        )
        self.logger.declare_expected_error(
            comparison="startswith",
            expectation="expire '' could not be parsed into a valid date",
        )
        # Assert that the pending_peers on disk is as expected
        user_pending_peers = self.assertUserPendingPeers(self.TEST_CLIENT_ID)
        self.assertIn(self.TEST_PENDING_PEER_DN, user_pending_peers)
        self.assertEqual(len(user_pending_peers), 1)
        pending_peer = user_pending_peers[self.TEST_PENDING_PEER_DN]

        test_pending_peer = {
            "peers": [self.TEST_PENDING_PEER_DN],
        }
        request_body = {
            "type": "peers__requested__accept",
            "operation": "create",
            **test_pending_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        user_peers = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertIn(self.TEST_PENDING_PEER_DN, user_peers)

        # Now validate that the peers entry matches the values
        # from the original pending_peer, with the caveat
        # that the expire field should be transformed
        # from an EPOCH value to a datetime timestamp ala YYYY-MM-DD
        accepted_peer = user_peers[self.TEST_PENDING_PEER_DN]

        old_expire_epoch = pending_peer.pop("expire")
        new_expire_dateformat = accepted_peer.pop("expire")
        self.assertDictEqual(pending_peer, accepted_peer)

        old_expire_dateformat = datetime.fromtimestamp(
            old_expire_epoch
        ).strftime("%Y-%m-%d")
        self.assertEqual(old_expire_dateformat, new_expire_dateformat)

    def test_peers_requested_delete(self):
        self._provision_pending_peer(
            self, [self.TEST_PENDING_PEER_DN], self.TEST_CLIENT_ID
        )

        test_pending_peer = {
            "peers": [self.TEST_PENDING_PEER_DN],
        }

        request_body = {
            "type": "peers__requested__delete",
            "operation": "delete",
            **test_pending_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(
            self.configuration,
            "http://localhost/datainterface.py",
            form=request_body,
            mig_user_dn=self.TEST_CLIENT_ID,
        )

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response["status"]
        self.assertEqual(status, 200)

        # now check that the peer was removed
        user_pending_peers = self.assertUserPendingPeers(self.TEST_CLIENT_ID)
        self.assertEqual(len(user_pending_peers), 0)

        # check the email was sent
        fake_send_email = self.configuration.context_get("notifier").send_email
        self.assertTrue(fake_send_email.called_once)
        self.assertTrue(fake_send_email.email_was_sent_to("admin@example.com"))


if __name__ == "__main__":
    testmain()
