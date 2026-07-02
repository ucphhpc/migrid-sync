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

# Imports of the code under test
import mig.shared.accountreq as accountreq
# Imports required for the unit test wrapping
from mig.shared.base import canonical_user, distinguished_name_to_user, \
    fill_distinguished_name, get_client_id, client_id_dir
from mig.shared.defaults import keyword_auto
# Imports required for the unit tests themselves
from tests.support import MigTestCase, testmain, ensure_dirs_exist
from tests.support.fixturesupp import FixtureAssertMixin, _PreparedFixture
from tests.support.picklesupp import PickleAssertMixin
from tests.support.usersupp import UserAssertMixin, \
    TEST_USER_DN, TEST_PEER_DN, TEST_PENDING_PEER_DN


def make_fake_notify_user(*args):
    class FakeNotifyUser:
        def __init__(self):
            self.calls = []

        def __call__(self, *args):
            self.calls.append(args)
            return (True, [])

        @property
        def called_once(self):
            return len(self.calls) == 1

    return FakeNotifyUser()


class MigSharedAccountreq__peers_helpers(MigTestCase,
                                 FixtureAssertMixin,
                                 PickleAssertMixin,
                                 UserAssertMixin):
    """Unit tests for peers related functions within the accountreq module"""

    TEST_USER_DN = TEST_USER_DN

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        ensure_dirs_exist(self.configuration.user_cache)
        ensure_dirs_exist(self.configuration.user_pending)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.mrsl_files_dir)
        ensure_dirs_exist(self.configuration.resource_pending)
        ensure_dirs_exist(self.configuration.mig_system_files)

    def test_direct_addition_of_a_pending_peer(self):
        self.assertDirEmpty(self.configuration.user_pending)
        self._provision_test_user(self, self.TEST_USER_DN)
        pending_peers_fixture = self.prepareFixtureAssert('pending_peers--single', 'json')
        assert TEST_PENDING_PEER_DN in pending_peers_fixture.fixture_data
        peer_dict = pending_peers_fixture.fixture_data[TEST_PENDING_PEER_DN]
        assert peer_dict['distinguished_name'] == TEST_PENDING_PEER_DN

        success = accountreq.manage_pending_peers(
                                                self.configuration,
                                                self.TEST_USER_DN,
                                                "add",
                                                [(TEST_PENDING_PEER_DN, peer_dict)])

        self.assertTrue(success)
        actual_peers_dict = self.assertUserPendingPeers(self.TEST_USER_DN)
        self.assertEqual(len(actual_peers_dict), 1)
        pending_peers_fixture.assertAgainstFixture(actual_peers_dict)


class MigSharedAccountreq__peers_under_request(MigTestCase,
                                 FixtureAssertMixin,
                                 PickleAssertMixin,
                                 UserAssertMixin):

    TEST_PEER_DN = TEST_PEER_DN
    TEST_USER_DN = TEST_USER_DN

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        ensure_dirs_exist(self.configuration.user_pending)

    def _peer_dict_from_fixture(self):
        prepared_fixture = self.prepareFixtureAssert("peers--single", fixture_format="json")
        fixture_data = prepared_fixture.fixture_data
        assert isinstance(fixture_data, dict)
        assert self.TEST_PEER_DN in fixture_data
        return self.TEST_PEER_DN, fixture_data[self.TEST_PEER_DN]

    def test_attempt_to_accept_without_pending_user(self):
        self.assertDirEmpty(self.configuration.user_pending)
        self.logger.declare_expected_error(comparison='startswith',
                                           expectation='peer account request tmpNOEXIST extraction failed')

        success, message = accountreq.peer_account_req('tmpNOEXIST',
                                                 self.configuration,
                                                 self.TEST_USER_DN)

        self.assertFalse(success)
        self.assertTrue(message.startswith('peer account request tmpNOEXIST extraction failed'))

    def test_attempt_to_accept_without_target_user(self):
        self.assertDirEmpty(self.configuration.user_pending)
        self._provision_user_db_empty(self)
        req_id, = UserAssertMixin._provision_test_pending_user(self, [self.TEST_PEER_DN], self.TEST_USER_DN)
        _, request_dict = self._peer_dict_from_fixture()
        self.logger.declare_expected_error(comparison='startswith',
                                           expectation='no target users to request peer acceptance from')


        success, message = accountreq.peer_account_req(req_id,
                                                 self.configuration,
                                                 self.TEST_USER_DN,
                                                 request_dict)

        self.assertFalse(success)
        self.assertEqual(message, 'no valid target peer acceptance users')

    def test_valid_accept(self):
        self.assertDirEmpty(self.configuration.user_pending)
        self._provision_test_user(self, self.TEST_USER_DN)
        req_id, = self._provision_test_pending_user(self, [self.TEST_PEER_DN], self.TEST_USER_DN)
        _, request_dict = self._peer_dict_from_fixture()
        fake_notify_user = make_fake_notify_user()

        success, _ = accountreq.peer_account_req(req_id,
                                                 self.configuration,
                                                 self.TEST_USER_DN,
                                                 request_dict,
                                                 _notify_user=fake_notify_user)

        self.assertTrue(success)
        # check user_pending is unchanged
        absolute_files = self.assertDirNotEmpty(self.configuration.user_pending)
        self.assertEqual(len(absolute_files), 1)
        # check the peer was notified
        self.assertTrue(fake_notify_user.called_once)


class MigSharedAccountreq__peers_existing(MigTestCase,
                                          FixtureAssertMixin,
                                          UserAssertMixin):
    """Unit tests for peers related functions within the accountreq module"""

    TEST_PEER_DN = TEST_PEER_DN
    TEST_USER_DN = TEST_USER_DN
    TEST_PENDING_PEER_DN = TEST_PENDING_PEER_DN

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        ensure_dirs_exist(self.configuration.user_pending)
        self._provision_test_user(self, TEST_USER_DN)

    def test_listing_accepted_peers(self):
        self.assertDirEmpty(self.configuration.user_pending)
        self._record_peer('peers--single', against_user_dn=TEST_USER_DN)

        listing = accountreq.list_peers_accepted(self.configuration,
                                                          TEST_USER_DN)

        self.assertEqual(len(listing), 1)

    def test_listing_requested_peers(self):
        self.assertDirEmpty(self.configuration.user_pending)
        self._record_pending_peer(TEST_PENDING_PEER_DN, against_user_dn=TEST_USER_DN)

        listing = accountreq.list_peers_requested(self.configuration,
                                                          TEST_USER_DN)

        self.assertEqual(len(listing), 1)


class MigSharedAccountreq__users_pending(MigTestCase, FixtureAssertMixin):

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        ensure_dirs_exist(self.configuration.user_pending)

    def test_listing_pending_user_requests(self):
        self.assertDirEmpty(self.configuration.user_pending)
        pending_user_dir, = UserAssertMixin._provision_test_pending_user(self, [TEST_PEER_DN], TEST_USER_DN)
        success, listing = accountreq.list_account_reqs(self.configuration)

        self.assertTrue(success)
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0], pending_user_dir)


class MigSharedAccountreq__filters(MigTestCase, UserAssertMixin):
    """Unit tests for filter related functions within the accountreq module"""

    TEST_SERVICE = 'migoid'
    TEST_INTERNAL_DN = '/C=DK/ST=NA/L=NA/O=Local Org/OU=NA/CN=Test Name/emailAddress=test@local.org'
    TEST_EXTERNAL_DN = '/C=DK/ST=NA/L=NA/O=External Org/OU=NA/CN=Test User/emailAddress=test@external.org'
    TEST_USER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
    TEST_ADMIN_DN = '/C=DK/ST=NA/L=NA/O=DIKU/OU=NA/CN=Test Admin/emailAddress=siteadm@di.ku.dk'

    TEST_INT_PW = 'PW74deb6609F109f504d'
    TEST_EXT_PW = 'PW174db6509F109e1531'
    TEST_USER_PW = 'foobar'
    TEST_INT_PW_HASH = 'PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$epib2rEg/HYTQZFnCp7hmIGZ6rzHnViy'
    TEST_EXT_PW_HASH = 'PBKDF2$sha256$10000$MDAwMDAwMDAwMDAw$TQZFnCp7hmIGZ6ep2rEg/HYrzHnVyiib'
    TEST_USER_PW_HASH = 'PBKDF2$sha256$10000$/TkhLk4yMGf6XhaY$7HUeQ9iwCkE4YMQAaCd+ZdrN+y8EzkJH'

    TEST_INTERNAL_EMAILS = ['john.doe@science.ku.dk', 'abc123@ku.dk',
                            'john.doe@a.b.c.ku.dk']
    TEST_EXTERNAL_EMAILS = ['john@doe.org', 'a@b.c.org', 'a@ku.dk.com',
                            'a@sci.ku.dk.org', 'a@diku.dk', 'a@nbi.dk']
    TEST_EXTERNAL_EMAIL_PATTERN = r'^.+(?<!(@|\.)ku\.dk)$'
    TEST_INTERNAL_EMAIL_PATTERN = r'^.+@([a-z0-9]+\.)*ku\.dk$'
    INT_USER, EXT_USER, TEST_USER = {}, {}, {}

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        ensure_dirs_exist(self.configuration.user_cache)
        ensure_dirs_exist(self.configuration.user_pending)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.mrsl_files_dir)
        ensure_dirs_exist(self.configuration.resource_pending)
        self.INT_USER = distinguished_name_to_user(self.TEST_INTERNAL_DN)
        self.INT_USER['password_hash'] = self.TEST_INT_PW_HASH
        self.EXT_USER = distinguished_name_to_user(self.TEST_EXTERNAL_DN)
        self.EXT_USER['peers_email'] = self.INT_USER['email']
        self.EXT_USER['peers_full_name'] = self.INT_USER['full_name']
        self.EXT_USER['password_hash'] = self.TEST_EXT_PW_HASH
        self.TEST_USER = distinguished_name_to_user(self.TEST_USER_DN)
        self.EXT_USER['password_hash'] = self.TEST_USER_PW_HASH
        self.configuration.site_signup_prefilter = [
            ('email', self.TEST_EXTERNAL_EMAIL_PATTERN), ]
        self.configuration.site_peers_prefilter = [
            ('peers_email', self.TEST_INTERNAL_EMAIL_PATTERN), ]

    def test_signup_prefilter_email_accept(self):
        for addr in self.TEST_EXTERNAL_EMAILS:
            self.EXT_USER['email'] = addr
            check = accountreq.signup_prefilter_allowed(self.configuration,
                                                        self.EXT_USER)
            self.assertTrue(check)

    def test_signup_prefilter_email_reject(self):
        for addr in self.TEST_INTERNAL_EMAILS:
            self.EXT_USER['email'] = addr
            check = accountreq.signup_prefilter_allowed(self.configuration,
                                                        self.EXT_USER)
            self.assertFalse(check)

    def test_signup_prefilter_email_accept_site_admins(self):
        user = distinguished_name_to_user(self.TEST_ADMIN_DN)
        admin_list = [self.TEST_ADMIN_DN]
        self.configuration.site_signup_prefilter = [
            ('email', r'^.+(?<!(@|\.)ku\.dk)$')]
        check = accountreq.signup_prefilter_allowed(self.configuration, user)
        self.assertFalse(check)
        check = accountreq.signup_prefilter_allowed(self.configuration, user,
                                                    admin_list)
        self.assertTrue(check)

    def test_peers_prefilter_email_accept(self):
        for addr in self.TEST_INTERNAL_EMAILS:
            self.EXT_USER['peers_email'] = addr
            check = accountreq.peers_prefilter_allowed(self.configuration,
                                                       self.EXT_USER)
            self.assertTrue(check)

    def test_peers_prefilter_email_reject(self):
        for addr in self.TEST_EXTERNAL_EMAILS:
            self.EXT_USER['peers_email'] = addr
            check = accountreq.peers_prefilter_allowed(self.configuration,
                                                       self.EXT_USER)
            self.assertFalse(check)

    def test_early_validation_checks_valid_new_simple(self):
        self._provision_test_user(self, self.TEST_USER_DN)
        checked = accountreq.early_validation_checks(self.configuration,
                                                     self.EXT_USER,
                                                     self.TEST_SERVICE,
                                                     self.EXT_USER['email'],
                                                     self.TEST_EXT_PW)
        # print("DEBUG: early checks on valid simple req: %s" % checked)
        self.assertEqual(checked['invalid'], [], "early validation failed")

    def test_early_validation_checks_valid_new_peers(self):
        self._provision_test_user(self, self.TEST_USER_DN)
        self.configuration.site_enable_peers = True
        self.configuration.site_peers_explicit_fields = ['full_name', 'email']
        for addr in self.TEST_INTERNAL_EMAILS:
            self.EXT_USER['peers_email'] = addr
            checked = accountreq.early_validation_checks(self.configuration,
                                                         self.EXT_USER,
                                                         self.TEST_SERVICE,
                                                         self.EXT_USER['email'],
                                                         self.TEST_EXT_PW)
            # print("DEBUG: early checks on valid peers req: %s" % checked)
            self.assertEqual(checked['invalid'], [], "early validation failed")

    def test_early_validation_checks_valid_renew_existing(self):
        test_int_client_dir = self._provision_test_users(self,
                                                         self.TEST_USER_DN,
                                                         self.TEST_INTERNAL_DN)
        self.TEST_USER['peers_email'] = self.INT_USER['email']
        # TODO: sync password with saved hash and disable auth here
        self.TEST_USER['authorized'] = True
        checked = accountreq.early_validation_checks(self.configuration,
                                                     self.TEST_USER,
                                                     self.TEST_SERVICE,
                                                     self.TEST_USER['email'],
                                                     self.TEST_USER_PW)
        # print("DEBUG: early checks on valid renew req: %s" % checked)
        self.assertEqual(checked['invalid'], [], "early validation failed")

    def test_early_validation_checks_valid_renew_authorized(self):
        test_client_dir = self._provision_test_users(self,
                                                     self.TEST_USER_DN,
                                                     self.TEST_INTERNAL_DN)
        self.TEST_USER['peers_email'] = self.INT_USER['email']
        # Make sure password change is allowed if needed
        self.TEST_USER['authorized'] = True
        checked = accountreq.early_validation_checks(self.configuration,
                                                     self.TEST_USER,
                                                     self.TEST_SERVICE,
                                                     self.TEST_USER['email'],
                                                     self.TEST_USER_PW)
        # print("DEBUG: early checks on valid renew req: %s" % checked)
        self.assertEqual(checked['invalid'], [], "early validation failed")

    def test_early_validation_checks_invalid_new_simple(self):
        self._provision_test_user(self, self.TEST_USER_DN)
        self.EXT_USER['full_name'] = 'InvalidNameWithoutSpace'
        checked = accountreq.early_validation_checks(self.configuration,
                                                     self.EXT_USER,
                                                     self.TEST_SERVICE,
                                                     self.EXT_USER['email'],
                                                     self.TEST_INT_PW)
        # print("DEBUG: early checks on invalid simple req: %s" % checked)
        self.assertTrue(checked['invalid'], "early validation failed")

    def test_early_validation_checks_invalid_new_peers(self):
        self._provision_test_user(self, self.TEST_USER_DN)
        self.configuration.site_enable_peers = True
        self.configuration.site_peers_explicit_fields = ['full_name', 'email']
        self.EXT_USER['peers_full_name'] = self.INT_USER['full_name']
        self.EXT_USER['peers_email'] = ''
        checked = accountreq.early_validation_checks(self.configuration,
                                                     self.EXT_USER,
                                                     self.TEST_SERVICE,
                                                     self.EXT_USER['email'],
                                                     self.TEST_EXT_PW)
        # print("DEBUG: early checks on invalid peers req: %s" % checked)
        self.assertTrue(checked['invalid'], "early validation failed")

    def test_early_validation_checks_invalid_renew_collision(self):
        test_client_dir = self._provision_test_user(self,
                                                    self.TEST_USER_DN)
        test_client_dir_name = os.path.basename(test_client_dir)
        self.TEST_USER['organization'] = 'Invalid Changed Org'
        del self.TEST_USER['distinguished_name']
        self.TEST_USER = fill_distinguished_name(self.TEST_USER)
        checked = accountreq.early_validation_checks(self.configuration,
                                                     self.TEST_USER,
                                                     self.TEST_SERVICE,
                                                     self.TEST_USER['email'],
                                                     self.TEST_USER_PW)
        # print("DEBUG: early checks on invalid renew collision req: %s" % checked)
        self.assertTrue(checked['invalid'], "early validation failed")

    def test_early_validation_checks_invalid_renew_pw_change(self):
        test_client_dir = self._provision_test_user(self, self.TEST_USER_DN)
        test_client_dir_name = os.path.basename(test_client_dir)
        checked = accountreq.early_validation_checks(self.configuration,
                                                     self.TEST_USER,
                                                     self.TEST_SERVICE,
                                                     self.TEST_USER['email'],
                                                     self.TEST_USER_PW + 'N3w')
        # print("DEBUG: early checks on invalid renew pw change req: %s" % checked)
        self.assertTrue(checked['invalid'], "early validation failed")

    def test_early_validation_checks_invalid_renew_suspended(self):
        test_client_dir = self._provision_test_user(self, self.TEST_USER_DN)
        test_client_dir_name = os.path.basename(test_client_dir)
        # TODO: change existing user status to suspended! (currently fails on pw)
        self.TEST_USER['status'] = 'temporal'
        checked = accountreq.early_validation_checks(self.configuration,
                                                     self.TEST_USER,
                                                     self.TEST_SERVICE,
                                                     self.TEST_USER['email'],
                                                     self.TEST_USER_PW)
        # print("DEBUG: early checks on invalid renew suspended req: %s" % checked)
        self.assertTrue(checked['invalid'], "early validation failed")


if __name__ == '__main__':
    testmain()
