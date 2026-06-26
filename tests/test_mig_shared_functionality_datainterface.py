
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
from collections import namedtuple
from datetime import date, timedelta
import importlib
import os
import shutil
import sys
import unittest

from tests.support import MIG_BASE, PY2, TEST_DATA_DIR, MigTestCase, testmain, \
    temppath, ensure_dirs_exist
from tests.support.fixturesupp import FixtureAssertMixin, fixturepath
from tests.support.picklesupp import PickleAssertMixin
from tests.support.usersupp import UserAssertMixin
from tests.support.wsgisupp import WsgiAssertMixin
from envhelp.makeconfig import _ensure_dirs_needed_for_userdb

from mig.shared.base import client_id_dir
from mig.shared.configuration import Configuration
from mig.shared.functionality.datainterface import _main as submain


def _only_output_objects(output_objects, with_object_type=None):
    return [o for o in output_objects if o['object_type'] == with_object_type]


class MigSharedFunctionalityDatainterface__generic(MigTestCase,
                                                   WsgiAssertMixin):
    """Tests of end to end generic behaviour of datainterface"""

    TEST_CLIENT_ID = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        self._provision_test_user(self, self.TEST_CLIENT_ID)

    def test_wsgi_nonexistent_route(self):
        request_body = {
            'type': '__nonexistent',
            'operation': 'create',
            'content': 'insert me',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 404)

        self.assertIn('error', json_response)
        self.assertEqual(json_response['error'], 'the speficied route package handler was not found')


class MigSharedFunctionalityDatainterface__peers_wsgi(MigTestCase,
                                                                  WsgiAssertMixin,
                                                                  FixtureAssertMixin,
                                                                  PickleAssertMixin,
                                                                  UserAssertMixin):
    """Tests of the end to end peers behaviours of datainterface"""

    TEST_CLIENT_ID = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
    TEST_PEER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=peer@example.com'
    TEST_PENDING_PEER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Pending Peer User/emailAddress=pending_peer@example.com'

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        user_paths_dict = self._provision_test_user_return_dict(self, self.TEST_CLIENT_ID, )
        self.test_user_settings_dir = user_paths_dict['user_settings_dir']

    def assertPendingUsers(self, expected_count=0):
        user_pending_entries = os.listdir(self.configuration.user_pending)
        self.assertEqual(len(user_pending_entries), expected_count)
        return user_pending_entries

    def test_peers_new_with_missing_fields(self):
        test_pending_peer = {
            "country": "DK",
            "email": "pending_peer@example.com",
            "full_name": "Pending Peer User",
            "organization": "Test Org",
            "state": "NA"
        }

        request_body = {
            'type': 'peers__new',
            'operation': 'create',
            **test_pending_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        self.assertIn("status", json_response)
        status = json_response['status']
        self.assertEqual(status, 400)

        # check we failed creation -> missing expire, kind, label
        self.assertIn("data", json_response)
        self.assertIn("errors_map", json_response["data"])

        # check we failed creation
        errors_map = json_response['data']['errors_map']
        self.assertEqual(errors_map, {
            '0': {
                'expire': 'expire is required but missing',
                'kind': 'kind is required but missing',
                'label': 'label is required but missing',
            }
        })

        # check nothing was saved
        self.assertPendingUsers(expected_count=0)

    def test_peers_new_with_invalid_fields(self):
        test_pending_peer = {
            "country": "DK",
            "email": "pending_peer@example.com",
            "full_name": "Pending Peer User",
            "organization": "Test Org",
            "state": "NA",
            "label": "some_peer_label",
            "kind": "not_a_valid_kind",
            "expire": 1234,
        }

        request_body = {
            'type': 'peers__new',
            'operation': 'create',
            **test_pending_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 400)

        # check we failed creation
        errors_map = json_response['data']['errors_map']
        self.assertEqual(errors_map, {
            '0': {
                'expire': 'shorter than minimum length (10)',
                'kind': 'invalid peer kind',
            }
        })

        # check nothing was saved
        self.assertPendingUsers(expected_count=0)

    def test_peers_new_valid(self):
        date_expire_in_1_day = date.today() + timedelta(days=1)
        test_pending_peer = {
            "country": "DK",
            "email": "pending_peer@example.com",
            "full_name": "Pending Peer User",
            "label": "some_peer_label",
            "expire": date_expire_in_1_day.isoformat(),
            "organization": "Test Org",
            "kind": "project",
            "state": "NA",
        }

        request_body = {
            'type': 'peers__new',
            'operation': 'create',
            "invite_on_email": True,
            **test_pending_peer,
        }
        pending_peers_fixture = self.prepareFixtureAssert('pending_peers--single', 'json')
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 200)

        user_pending_entries = self.assertPendingUsers(expected_count=1)
        user_pending_filename = user_pending_entries[0]
        user_pending_file = os.path.join(self.configuration.user_pending, user_pending_filename)
        actual = self.assertPickledFile(user_pending_file, apply_hints=['convert_dict_bytes_to_strings_kv'])

        actual_peers_tuples = self.assertUserPendingPeers(self.TEST_CLIENT_ID)
        pending_peers_fixture.assertAgainstFixture(actual_peers_tuples)

    def test_peers_summary(self):
        self._provision_peer_user(self, self.TEST_PEER_DN, against_user_dn=self.TEST_CLIENT_ID)
        self._provision_test_pending_user(self, self.TEST_PENDING_PEER_DN, against_user_dn=self.TEST_CLIENT_ID)

        request_body = {
            'type': 'peers__summary',
            'operation': 'read',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)


        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 200)

        data = json_response['data']
        self.assertEqual(data, {
            'accepted_count': 1,
            'requested_count': 0,
        })

    def test_peers_accepted_delete(self):
        self._provision_peer_user(self, self.TEST_PEER_DN, against_user_dn=self.TEST_CLIENT_ID)

        test_pending_peer = {
            "peers": [self.TEST_PEER_DN],
        }

        request_body = {
            'type': 'peers__accepted__delete',
            'operation': 'delete',
            **test_pending_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 200)

        data = json_response['data']
        self.assertEqual(data, {
            'success_map': {
                '0': True,
            }
        })

        # now check that the peer was removed
        content = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertEqual(len(content), 0)

        # check the email was sent
        fake_send_email = self.configuration.context_get('notifier').send_email
        self.assertTrue(fake_send_email.called_once)
        self.assertTrue(fake_send_email.email_was_sent_to('admin@example.com'))

    def test_peers_accepted_delete_invalid_dn(self):
        test_pending_peer = {
            "peers": ["foo/bar/baz"],
        }

        request_body = {
            'type': 'peers__accepted__delete',
            'operation': 'delete',
            **test_pending_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        self.assertIn('status', json_response)
        status = json_response['status']
        self.assertEqual(status, 400)

        self.assertIn('error', json_response)
        error = json_response['error']
        self.assertIsNotNone(error)
        self.assertNotEqual(error, "")        


    def test_peers_accepted_fetch(self):
        self._provision_peer_user(self, self.TEST_PEER_DN, against_user_dn=self.TEST_CLIENT_ID)

        payload = {
            "peer_dn": self.TEST_PEER_DN,
        }

        request_body = {
            'type': 'peers__accepted__fetch',
            'operation': 'create',
            **payload,
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 200)

        data = json_response['data']
        self.assertEqual(data['distinguished_name'], self.TEST_PEER_DN)

    def test_peers_accepted_import(self):
        date_expire_in_8_days = date.today() + timedelta(days=8)
        peers_csv = fixturepath("csv/peers-for-import.csv")
        with open(peers_csv) as f:
            content = f.read()
        request_body = {
            'type': 'peers__accepted__import',
            'operation': 'delete',
            'label': 'some_peer_label',
            'kind': 'collaboration',
            'expire': date_expire_in_8_days.isoformat(),
            'csvtext': content,
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 200)

        # now check that peers were created
        content = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertEqual(len(content), 3)

        # check email were sent
        fake_send_email = self.configuration.context_get('notifier').send_email
        self.assertEqual(fake_send_email.total_emails_sent(), 4)

    def test_peers_accepted_update(self):
        self._provision_peer_user(self, self.TEST_PEER_DN, against_user_dn=self.TEST_CLIENT_ID)

        payload = {
            "peer_dn": self.TEST_PEER_DN,
        }

        request_body = {
            'type': 'peers__accepted__update',
            'operation': 'create',
            **payload,
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 404)

    def test_peers_requsted_accept(self):
        _ensure_dirs_needed_for_userdb(self.configuration)
        self._provision_pending_peer(self, self.TEST_PENDING_PEER_DN, against_user_dn=self.TEST_CLIENT_ID)
        self.logger.declare_expected_error(comparison='startswith',
                                           expectation="expire '' could not be parsed into a valid date")

        test_pending_peer = {
            "peers": [self.TEST_PENDING_PEER_DN],
        }

        request_body = {
            'type': 'peers__requested__accept',
            'operation': 'delete',
            **test_pending_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 200)

        data = json_response['data']
        self.assertEqual(data['success_map'], {
            '0': True
        })

        # now check that the peer was added
        user_peers = self.assertUserPeers(self.TEST_CLIENT_ID)
        self.assertIn(self.TEST_PENDING_PEER_DN, user_peers)

        # check that the client pending peer is gone
        pending_peers = self.assertUserPendingPeers(self.TEST_CLIENT_ID)
        self.assertEqual(len(pending_peers), 0)

        # check emails were sent
        fake_send_email = self.configuration.context_get('notifier').send_email
        self.assertTrue(fake_send_email.email_was_sent_to('admin@example.com'))

    def test_peers_requested_delete(self):
        self._provision_pending_peer(self, self.TEST_PENDING_PEER_DN, against_user_dn=self.TEST_CLIENT_ID)

        test_pending_peer = {
            "peers": [self.TEST_PENDING_PEER_DN],
        }

        request_body = {
            'type': 'peers__requested__delete',
            'operation': 'delete',
            **test_pending_peer,
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/datainterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)


        json_response = self.assertWsgiJsonResponse(prepared_wsgi)

        status = json_response['status']
        self.assertEqual(status, 200)

        # now check that the peer was removed
        user_pending_peers = self.assertUserPendingPeers(self.TEST_CLIENT_ID)
        self.assertEqual(len(user_pending_peers), 0)

        # check the email was sent
        fake_send_email = self.configuration.context_get('notifier').send_email
        self.assertTrue(fake_send_email.called_once)
        self.assertTrue(fake_send_email.email_was_sent_to('admin@example.com'))


if __name__ == '__main__':
    testmain()
