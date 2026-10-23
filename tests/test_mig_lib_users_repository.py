import fcntl
import os
from datetime import datetime
from typing import Any, override

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

    @override
    def _provide_configuration(self):
        return "testconfig"

    @override
    def before_each(self) -> None:
        os.mkdir(self.configuration.user_db_home)
        dump({}, self._db_path)

    @property
    def _db_path(self) -> str:
        """Returns the path of the user DB file"""
        return os.path.join(self.configuration.user_db_home, user_db_filename)


class TestSave(UserRepositoryTestCase):

    def test_adds_expected_user_to_db(self) -> None:
        repo = UserRepository(self.configuration)
        user = test_user.copy()

        repo.save(user)
        user_db: dict[str, dict[str, Any]] = load(self._db_path)  # type: ignore
        actual = user_db[user.distinguished_name]

        expected = user.to_dict()
        self.assertEqual(actual, expected)


class TestReadAll(UserRepositoryTestCase):

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
