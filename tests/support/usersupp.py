# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# usersupp - user related helpers for unit tests
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
# -- END_HEADER ---
#

"""User related details within the test support library."""

from collections import namedtuple
import datetime
import errno
import os
import tempfile
import pickle

from mig.shared.base import client_id_dir, distinguished_name_to_user

from tests.support.fixturesupp import _PreparedFixture, apply_named_hints


TEST_USER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
TEST_PEER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=peer@example.com'
TEST_PENDING_PEER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Pending Peer User/emailAddress=pending_peer@example.com'
OTHER_USER_DN = '/C=DK/ST=NA/L=NA/O=Other Org/OU=NA/CN=Other User/emailAddress=other@example.com'
NO_SUCH_USER_DN = '/C=DK/ST=NA/L=NA/O=No Such Org/OU=NA/CN=No Such User/emailAddress=nosuchuser@example.com'

_FIXTURE_NAME_BY_USER_DN = {
    TEST_USER_DN: 'MiG-users.db--example'
}

_FIXTURE_NAME_BY_PENDING_PEER_DN = {
    TEST_PENDING_PEER_DN: 'pending_peers--single'
}


_PendingUserInfo = namedtuple('_PendingUserInfo', [
    'reqid',
    'user_dn',
    'user_dict'
])


def _make_peers_path(configuration, user_dn):
    user_settings_dir = configuration.user_settings
    user_dir_name = client_id_dir(user_dn)
    return os.path.join(user_settings_dir, user_dir_name, 'peers')


def _make_pending_peers_path(configuration, user_dn):
    user_settings_dir = configuration.user_settings
    user_dir_name = client_id_dir(user_dn)
    return os.path.join(user_settings_dir, user_dir_name, 'pending_peers')


class UserAssertMixin:
    """
    A series of support functions concerned with user state.
    """

    @staticmethod
    def _provision_user_db_dir(testcase):
        """
        Ensure the directories needed for the creation of a user db exist.
        """

        # ensure the location for the user db that will include our test user
        conf_user_db_home = testcase.configuration.user_db_home
        os.makedirs(conf_user_db_home, exist_ok=True)

        user_db_file = os.path.join(conf_user_db_home, 'MiG-users.db')
        if os.path.exists(user_db_file):
            raise AssertionError('a user database file already exists')

        # allow new user registration to function
        os.makedirs(testcase.configuration.user_pending, exist_ok=True)

        # create the directory containing the user modified mark file
        os.makedirs(testcase.configuration.mig_system_files, exist_ok=True)

        return conf_user_db_home

    @staticmethod
    def _provision_user_db_empty(testcase):
        """
        Ensure an empty user db exists.
        """

        conf_user_db_home = UserAssertMixin._provision_user_db_dir(testcase)
        user_db_file = os.path.join(conf_user_db_home, 'MiG-users.db')

        with open(user_db_file, 'wb') as dbfile:
            pickle.dump({}, dbfile)

    @staticmethod
    def _provision_test_user_return_dict(testcase, distinguished_name):
        """
        Fabricate a test user on demand.

        This function will create a single user using the data contained in
        a particular fixture.
        """

        conf_user_db_home = UserAssertMixin._provision_user_db_dir(testcase)

        try:
            fixture_relpath = _FIXTURE_NAME_BY_USER_DN[distinguished_name]
        except KeyError:
            raise AssertionError(
                'supplied test user is not known as a fixture')

        # note: this is a non-standard direct use of fixture preparation due
        #       to this being bootstrap code and should not be used elsewhere
        prepared_fixture = _PreparedFixture.from_relpath(testcase,
                                                         fixture_relpath,
                                                         fixture_format='json'
                                                         )
        # write out the user database fixture containing the user
        prepared_fixture.write_to_dir(conf_user_db_home,
                                      output_format='pickle')

        created_dirs_tuple = UserAssertMixin._provision_test_user_dirs(
            testcase, distinguished_name)

        return {
            'user_dir': created_dirs_tuple[0],
            'user_settings_dir': created_dirs_tuple[1],
        }

    @staticmethod
    def _provision_test_user(testcase, distinguished_name):
        return UserAssertMixin._provision_test_user_return_dict(
            testcase,
            distinguished_name
        )['user_dir']

    @staticmethod
    def _provision_test_user_dirs(testcase, distinguished_name):
        """
        Creates the on-disk directories for a particular test user.
        """

        self = testcase

        # NOTE: we basically need all the dirs in _USERADM_PATH_KEYS list.
        conf_user_home = os.path.normpath(self.configuration.user_home)
        test_client_dir_name = client_id_dir(distinguished_name)

        # create the test user home directory
        test_user_dir = os.path.join(conf_user_home, test_client_dir_name)
        os.makedirs(test_user_dir)

        # create the test user settings directory
        conf_user_settings = os.path.normpath(self.configuration.user_settings)
        test_user_settings_dir = os.path.join(conf_user_settings,
                                              test_client_dir_name)
        os.makedirs(test_user_settings_dir)

        # create an empty user settings file
        test_user_settings_file = os.path.join(test_user_settings_dir,
                                               'settings')
        with open(test_user_settings_file, 'wb') as outfile:
            pickle.dump({}, outfile)

        # TODO: clean up old _ensure_dirs_exist calls in tests to create these.
        # create the test user cache, resource pending and mrsl files sub dirs
        for sub in (self.configuration.user_cache,
                    self.configuration.resource_pending,
                    self.configuration.mrsl_files_dir):
            conf_user_sub = os.path.normpath(sub)
            test_user_sub_dir = os.path.join(conf_user_sub,
                                             test_client_dir_name)
            os.makedirs(test_user_sub_dir)

        return test_user_dir, test_user_settings_dir

    @staticmethod
    def _provision_test_users(testcase, *distinguished_names):
        """
        Fabricate multiple users on demand.

        This method specifically allows the creation of a user database
        containing a series of users. In contrast to the one-shot method,
        this does not require the users to be declared as fixtures. This
        involves a trade-off: it makes the tests less free-standing, in
        that the user db will be populated from arbitrary data and thus
        the test dependent upon this is less strongly assured, but if
        (as is the expectation) the basic operations are validated with
        "independent" data i.e. contained within fixtures as opposed to
        generated by logic that extended tests will need.
        """

        conf_user_db_home = UserAssertMixin._provision_user_db_dir(testcase)

        users_by_dn = {}

        for distinguished_name in distinguished_names:
            user_dict = distinguished_name_to_user(distinguished_name)
            users_by_dn[distinguished_name] = user_dict

        # write out all the users we have assembled by populating an empty
        # fixture with their data but using a known fixture name and thus one
        # suitably hinted so a production format pickle file ends up on-disk
        prepared_fixture = _PreparedFixture.from_relpath(testcase, 'MiG-users.db--example', fixture_format='json')
        prepared_fixture.fixture_data = users_by_dn
        prepared_fixture.write_to_dir(conf_user_db_home,
                                      output_format='pickle')

        for distinguished_name in distinguished_names:
            UserAssertMixin._provision_test_user_dirs(testcase,
                                                      distinguished_name)

    @staticmethod
    def _provision_test_pending_user(testcase, distinguished_names, against_user_dn):
        self = testcase

        against_user_email = distinguished_name_to_user(against_user_dn)['email']

        user_pending_dir = self.configuration.user_pending

        req_ids = []

        for distinguished_name in distinguished_names:
            user_dict = distinguished_name_to_user(distinguished_name)

            test_peer_dict = apply_named_hints(user_dict,
                'convert_dict_strings_to_bytes_kv'
            )
            # peers _must_ have a comment
            test_peer_dict['comment'] = against_user_email

            handle, tmpfile_abs = tempfile.mkstemp('', 'tmp', user_pending_dir)
            tmpfile_name = os.path.basename(tmpfile_abs)

            with open(handle, 'wb') as tmpfile:
                pickle.dump(test_peer_dict, tmpfile)
                req_ids.append(tmpfile_name)

        return req_ids

    @staticmethod
    def _provision_user_peers_empty(user_settings_dir):
        peers_path = os.path.join(user_settings_dir, "peers")
        with open(peers_path, 'wb') as outfile:
            pickle.dump({}, outfile)

    @staticmethod
    def _provision_user_peers_pending_empty(user_settings_dir):
        pending_peers_path = os.path.join(user_settings_dir, "pending_peers")
        with open(pending_peers_path, 'wb') as outfile:
            pickle.dump({}, outfile)

    @staticmethod
    def _provision_peer_user(self, distinguished_names, against_user_dn):
        assert hasattr(self, "test_user_settings_dir")
        assert self.test_user_settings_dir is not None

        peers_fixture = self.prepareFixtureAssert('peers--single', fixture_format='json')
        against_user_email = distinguished_name_to_user(against_user_dn)['email']

        for distinguished_name in distinguished_names:
            assert distinguished_name in peers_fixture.fixture_data
            peer_dict = peers_fixture.fixture_data[distinguished_name]
            assert peer_dict['comment'] == against_user_email

        peers_fixture.write_to_dir(self.test_user_settings_dir, output_format='pickle')

    @staticmethod
    def _provision_pending_peer(self, distinguished_names, against_user_dn):
        assert hasattr(self, "test_user_settings_dir")
        assert self.test_user_settings_dir is not None

        fixture = self.prepareFixtureAssert('pending_peers--single', fixture_format='json')
        against_user_email = distinguished_name_to_user(against_user_dn)['email']

        all_fixture_pending_peers = fixture.fixture_data

        for distinguished_name in distinguished_names:
            assert distinguished_name in all_fixture_pending_peers
            peer_dict = all_fixture_pending_peers[distinguished_name]
            assert peer_dict['comment'] == against_user_email

        fixture.write_to_dir(self.test_user_settings_dir, output_format='pickle')

    def _record_peer(self, fixture_relpath, against_user_dn):
        """Fabricate a peer record against a particular user.
        """

        prepared = _PreparedFixture.from_relpath(
            self,
            fixture_relpath,
            fixture_format='json'
        )

        # belt and braces fixture content check
        fixture_data = prepared.fixture_data
        assert isinstance(fixture_data, dict)
        assert TEST_PEER_DN in fixture_data

        user_dir_name = client_id_dir(against_user_dn)
        user_settings_dir = os.path.join(self.configuration.user_settings, user_dir_name)

        # Now write a peers file against the supplied user
        prepared.write_to_dir(user_settings_dir, output_format='pickle')

    def _record_pending_peer(self, distinguished_name, against_user_dn):
        """Fabricate a peer pending record against a particular user.
        """

        try:
            fixture_relpath = _FIXTURE_NAME_BY_PENDING_PEER_DN[distinguished_name]
        except KeyError:
            raise AssertionError("unknown DN for record pending peer")

        prepared = _PreparedFixture.from_relpath(
            self,
            fixture_relpath,
            fixture_format='json'
        )

        # belt and braces fixture content check
        pending_peer_dict = prepared.fixture_data[distinguished_name]
        assert pending_peer_dict["distinguished_name"] == distinguished_name

        user_dir_name = client_id_dir(against_user_dn)
        user_settings_dir = os.path.join(self.configuration.user_settings, user_dir_name)
        prepared.write_to_dir(user_settings_dir, 'pickle')

    def assertUserPeers(self, user_dn):
        peers_file_path = _make_peers_path(self.configuration, user_dn)
        return self.assertPickledFile(peers_file_path, apply_hints=['convert_dict_bytes_to_strings_kv', 'pairs_to_dict'])

    def assertUserPendingPeers(self, user_dn, as_native=False):
        pending_peers_file_path = _make_pending_peers_path(self.configuration, user_dn)
        pending_peers_hints = ['pairs_to_dict', 'convert_dict_bytes_to_strings_kv']
        return self.assertPickledFile(pending_peers_file_path, apply_hints=pending_peers_hints)

    def retrievePendingUsers(self):
        pending_user_dir = self.configuration.user_pending

        pending_users_info_by_dn = {}

        for pending_user_file_name in os.listdir(pending_user_dir):
            pending_user_file_path = os.path.join(pending_user_dir, pending_user_file_name)
            user_dict = self.assertPickledFile(pending_user_file_path, apply_hints=['convert_dict_bytes_to_strings_kv'])
            distinguished_name = user_dict['distinguished_name']

            pending_users_info_by_dn[distinguished_name] = _PendingUserInfo(
                pending_user_file_name,  # reqid
                distinguished_name, # dn
                user_dict,
            )

        return pending_users_info_by_dn
