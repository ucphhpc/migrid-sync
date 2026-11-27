#
# --- BEGIN_HEADER ---
#
# test_mig_lib_users_repository - user repository unit tests
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

"""Unit tests for mig.lib.users.repository."""

import fcntl
import os
from datetime import datetime
from typing import Any

from mig.lib.users.repository import UserRepository, UserSearchFilter
from mig.lib.users.user import User
from mig.shared.defaults import user_db_filename
from mig.shared.pwcrypto import make_hash, scramble_password
from mig.shared.serial import dump, load
from tests.support import MigTestCase

TEST_SALT = "12345678"
TEST_PASSWORD = "password"
TEST_PASSWORD_SCRAMBLE = str(scramble_password(TEST_SALT, TEST_PASSWORD))
TEST_PASSWORD_HASH = make_hash(TEST_PASSWORD)


test_user = User(
    country="DK",
    email="external@example.com",
    created=datetime(2020, 1, 1, 12, 0, 0),
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


class UserRepositoryTestCase(MigTestCase):
    """Common functionality for account request repository test case classes."""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self) -> None:
        os.mkdir(self.configuration.user_db_home)
        dump({}, self._db_path)

    @property
    def _db_path(self) -> str:
        """Returns the path of the user DB file"""
        return os.path.join(self.configuration.user_db_home, user_db_filename)


class TestReadAll(UserRepositoryTestCase):
    """Unit tests for UserRepository.read_all."""
    
    def test_returns_all_saved_users(self) -> None:
        repo = UserRepository(self.configuration)
        users: list[User] = []
        for i in [1, 2, 3]:
            user = test_user.copy()
            user.email = "external_%d@example.com" % i
            repo.save(user)
            users.append(user)

        actual = repo.read_all()

        expected = {user.distinguished_name: user for user in users}
        self.assertEqual(actual, expected)


class TestUserSearchFilter(UserRepositoryTestCase):
    """Unit tests for UserSearchFilter."""

    def test_includes_user_with_email(self) -> None:
        user = test_user.copy()
        search_filter = UserSearchFilter(email="external@example.com")

        actual = search_filter.include(user)

        self.assertTrue(actual)

    def test_does_not_include_user_with_different_email(self) -> None:
        user = test_user.copy()
        search_filter = UserSearchFilter(email="another@example.com")

        actual = search_filter.include(user)

        self.assertFalse(actual)


class TestSearch(UserRepositoryTestCase):
    """Unit tests for UserRepository.search."""

    def test_only_includes_users_matching_filter(self) -> None:
        repo = UserRepository(self.configuration)
        users: list[User] = []
        for i in [1, 2, 3]:
            user = test_user.copy()
            user.email = "external_%d@example.com" % i
            repo.save(user)
            users.append(user)

        actual = repo.search(UserSearchFilter(email="external_1@example.com"))

        expected = [users[0]]
        self.assertEqual(actual, expected)

    def test_only_uses_search_in_if_provided(self) -> None:
        repo = UserRepository(self.configuration)
        users: list[User] = []
        for i in [1, 2, 3]:
            user = test_user.copy()
            user.email = "external_%d@example.com" % i
            repo.save(user)
            users.append(user)

        search_in_user = test_user.copy()
        search_in_user.email = "user@search-in.com"
        search_in = [search_in_user]

        actual = repo.search(
            UserSearchFilter(email="user@search-in.com"), search_in=search_in
        )

        expected = [search_in_user]
        self.assertEqual(actual, expected)


class TestLockDB(UserRepositoryTestCase):
    """Unit tests for UserRepository._lock_user_db."""

    def test_cannot_acquire_exclusive_lock_after_exclusively_locked(self):
        repo = UserRepository(self.configuration)
        lock_path = "%s.lock" % repo._user_db_path

        with repo._lock_user_db(exclusive=True):
            with open(lock_path, "w+") as lock_handle:
                with self.assertRaises(IOError):
                    fcntl.flock(
                        lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                    )

    def test_cannot_acquire_exclusive_lock_after_nonexclusively_locked(self):
        repo = UserRepository(self.configuration)
        lock_path = "%s.lock" % repo._user_db_path

        with repo._lock_user_db(exclusive=False):
            with open(lock_path, "w+") as lock_handle:
                with self.assertRaises(IOError):
                    fcntl.flock(
                        lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                    )
