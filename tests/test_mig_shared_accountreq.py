# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_accountreq - unit test of the corresponding mig lib module
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Unit tests for the migrid module pointed to in the filename"""

import datetime
import os
import pickle
import sys
import unittest

from tests.support import MigTestCase, testmain, fixturefile, ensure_dirs_exist

import mig.shared.accountreq as accountreq
from mig.shared.base import canonical_user, fill_distinguished_name
from mig.shared.defaults import keyword_auto


class MigSharedAccountreq__peers(MigTestCase):
    """Unit tests for peers related functions within the accountreq module"""

    TEST_PEER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=peer@example.com'
    TEST_USER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'

    @property
    def user_settings_dir(self):
        return self.configuration.user_settings

    @property
    def user_pending_dir(self):
        return self.configuration.user_pending

    def _load_saved_peer(self, absolute_path):
        self.assertPathWithin(absolute_path, start=self.user_pending_dir)
        with open(absolute_path, 'rb') as pickle_file:
            value = pickle.load(pickle_file)

        def _string_if_bytes(value):
            if isinstance(value, bytes):
                return str(value, 'utf8')
            else:
                return value
        return {_string_if_bytes(x): _string_if_bytes(y) for x, y in value.items()}

    def _peer_dict_from_fixture(self):
        fixture_data, _ = fixturefile("peer_user_dict", fixture_format="json")
        assert fixture_data["distinguished_name"] == self.TEST_PEER_DN
        return fixture_data

    def _record_peer_acceptance(self, test_client_dir_name, peer_distinguished_name):
        """Fabricate a peer acceptance record in a particular user settings dir.
        """

        test_user_accepted_peers_file = os.path.join(
            self.user_settings_dir, test_client_dir_name, "peers")
        expire_tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        with open(test_user_accepted_peers_file, "wb") as test_user_accepted_peers:
            pickle.dump({peer_distinguished_name:
                         {'expire': str(expire_tomorrow)}},
                        test_user_accepted_peers)

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        ensure_dirs_exist(self.configuration.user_cache)
        ensure_dirs_exist(self.configuration.user_pending)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.mrsl_files_dir)
        ensure_dirs_exist(self.configuration.resource_pending)

    def test_a_new_peer(self):
        # precondition
        self.assertDirEmpty(self.configuration.user_pending)
        request_dict = self._peer_dict_from_fixture()

        success, _ = accountreq.save_account_request(self.configuration,
                                                     request_dict)

        # check that we have an output directory now
        absolute_files = self.assertDirNotEmpty(self.user_pending_dir)
        self.assertEqual(len(absolute_files), 1)
        # check the saved peer
        peer_user_dict = self._load_saved_peer(absolute_files[0])
        self.assertEqual(peer_user_dict, request_dict)

    def test_listing_peers(self):
        # precondition
        self.assertDirEmpty(self.user_pending_dir)
        request_dict = self._peer_dict_from_fixture()
        accountreq.save_account_request(self.configuration, request_dict)

        success, listing = accountreq.list_account_reqs(self.configuration)

        self.assertTrue(success)
        self.assertEqual(len(listing), 1)
        # check the fabricated peer was listed
        # sadly listing returns _relative_ dirs
        peer_temp_file_name = listing[0]
        peer_pickle_file = os.path.join(self.user_pending_dir,
                                        peer_temp_file_name)
        peer_pickle = self._load_saved_peer(peer_pickle_file)
        self.assertEqual(peer_pickle['distinguished_name'], self.TEST_PEER_DN)

    def test_peer_acceptance(self):
        test_client_dir = self._provision_test_user(self, self.TEST_USER_DN)
        test_client_dir_name = os.path.basename(test_client_dir)
        self._record_peer_acceptance(test_client_dir_name, self.TEST_PEER_DN)
        self.assertDirEmpty(self.user_pending_dir)
        request_dict = self._peer_dict_from_fixture()
        success, req_path = accountreq.save_account_request(self.configuration,
                                                            request_dict)
        arranged_req_id = os.path.basename(req_path)

        success, message = accountreq.accept_account_req(arranged_req_id,
                                                         self.configuration,
                                                         keyword_auto)

        self.assertTrue(success)

    def test_signup_prefilter_email_accept(self):
        accept = ['john@doe.org', 'a@b.c.org', 'a@ku.dk.com',
                  'a@sci.ku.dk.org', 'a@diku.dk', 'a@nbi.dk']
        self.configuration.site_signup_prefilter = [
            ('email', r'^.+(?<!(@|\.)ku\.dk)$')]
        for addr in accept:
            user = {'email': addr}
            check = accountreq.signup_prefilter_allowed(self.configuration,
                                                        user)
            self.assertTrue(check)

    def test_signup_prefilter_email_reject(self):
        reject = ['john.doe@science.ku.dk', 'abc123@ku.dk',
                  'john.doe@a.b.c.ku.dk']
        self.configuration.site_signup_prefilter = [
            ('email', r'.+(?<!(@|\.)ku\.dk)$')]
        for addr in reject:
            user = {'email': addr}
            check = accountreq.signup_prefilter_allowed(self.configuration,
                                                        user)
            self.assertFalse(check)

            print("check %r: %s" % (addr, check))

    def test_peers_prefilter_email_accept(self):
        accept = ['john.doe@science.ku.dk', 'abc123@ku.dk',
                  'john.doe@a.b.c.ku.dk']
        self.configuration.site_peers_prefilter = [
            ('peers_email', r'^.+@([a-z0-9]+\.)*ku\.dk$')]
        for addr in accept:
            user = {'peers_email': addr}
            check = accountreq.peers_prefilter_allowed(self.configuration,
                                                       user)
            self.assertTrue(check)

    def test_signup_prefilter_email_reject(self):
        reject = ['john@doe.org', 'a@b.c.org', 'a@ku.dk.com',
                  'a@sci.ku.dk.org']
        self.configuration.site_peers_prefilter = [
            ('peers_email', r'^.+@([a-z0-9]+\.)*ku\.dk$')]
        for addr in reject:
            user = {'peers_email': addr}
            check = accountreq.peers_prefilter_allowed(self.configuration,
                                                       user)
            self.assertFalse(check)


if __name__ == '__main__':
    testmain()
