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

import datetime
import errno
import os
import pickle

from mig.shared.base import client_id_dir
from tests.support.fixturesupp import _PreparedFixture

TEST_USER_DN = "/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com"
OTHER_USER_DN = "/C=DK/ST=NA/L=NA/O=Other Org/OU=NA/CN=Other User/emailAddress=other@example.com"
NO_SUCH_USER_DN = "/C=DK/ST=NA/L=NA/O=No Such Org/OU=NA/CN=No Such User/emailAddress=nosuchuser@example.com"

_FIXTURE_NAME_BY_USER_DN = {TEST_USER_DN: "MiG-users.db--example"}


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

        user_db_file = os.path.join(conf_user_db_home, "MiG-users.db")
        if os.path.exists(user_db_file):
            raise AssertionError("a user database file already exists")

        return conf_user_db_home

    @staticmethod
    def _provision_test_user(testcase, distinguished_name):
        """
        Fabricate a test user on demand.

        This function will create a single user using the data contained in
        a particular fixture.
        """

        conf_user_db_home = UserAssertMixin._provision_user_db_dir(testcase)

        try:
            fixture_relpath = _FIXTURE_NAME_BY_USER_DN[distinguished_name]
        except KeyError:
            raise AssertionError("supplied test user is not known as a fixture")

        # note: this is a non-standard direct use of fixture preparation due
        #       to this being bootstrap code and should not be used elsewhere
        prepared_fixture = _PreparedFixture.from_relpath(
            testcase, fixture_relpath, fixture_format="json"
        )
        # write out the user database fixture containing the user
        prepared_fixture.write_to_dir(conf_user_db_home, output_format="pickle")

        test_user_dir = UserAssertMixin._provision_test_user_dirs(
            testcase, distinguished_name
        )

        return test_user_dir

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
        test_user_settings_dir = os.path.join(
            conf_user_settings, test_client_dir_name
        )
        os.makedirs(test_user_settings_dir)

        # create an empty user settings file
        test_user_settings_file = os.path.join(
            test_user_settings_dir, "settings"
        )
        with open(test_user_settings_file, "wb") as outfile:
            pickle.dump({}, outfile)

        # TODO: clean up old _ensure_dirs_exist calls in tests to create these.
        # create the test user cache, resource pending and mrsl files sub dirs
        for sub in (
            self.configuration.user_cache,
            self.configuration.resource_pending,
            self.configuration.mrsl_files_dir,
        ):
            conf_user_sub = os.path.normpath(sub)
            test_user_sub_dir = os.path.join(
                conf_user_sub, test_client_dir_name
            )
            os.makedirs(test_user_sub_dir)

        return test_user_dir

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

        # locally import this to isolate the test suite from this production
        # logic i.e. any test which does not create multiple users does inherit
        # a dependency simply by importing this file (as does the entire suite)
        from mig.shared.base import distinguished_name_to_user

        for distinguished_name in distinguished_names:
            user_dict = distinguished_name_to_user(distinguished_name)
            users_by_dn[distinguished_name] = user_dict

        # write out all the users we have assembled by populating an empty
        # fixture with their data but using a known fixture name and thus one
        # suitably hinted so a production format pickle file ends up on-disk
        prepared_fixture = _PreparedFixture(testcase, "MiG-users.db--example")
        prepared_fixture.fixture_data = users_by_dn
        prepared_fixture.write_to_dir(conf_user_db_home, output_format="pickle")

        for distinguished_name in distinguished_names:
            UserAssertMixin._provision_test_user_dirs(
                testcase, distinguished_name
            )
