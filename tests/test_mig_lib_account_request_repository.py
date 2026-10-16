import os
from datetime import datetime

from typing_extensions import override

from mig.lib.account_request import AccountRequest, AccountRequestRepository
from mig.shared.pwcrypto import make_hash, scramble_password
from mig.shared.serial import load
from tests.support import MigTestCase

TEST_SALT = "12345678"
TEST_PASSWORD = "password"
TEST_PASSWORD_SCRAMBLE = str(scramble_password(TEST_SALT, TEST_PASSWORD))
TEST_PASSWORD_HASH = make_hash(TEST_PASSWORD)


test_account_request = AccountRequest(
    comment="A comment",
    country="DK",
    created=datetime(2020, 1, 1, 12, 0, 0),
    distinguished_name="/C=DK/ST=NA/L=Copenhagen/O=Organization/OU=Unit/CN=Full Name/emailAddress=external@example.com",
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


class AccountRequestRepositoryTestCase(MigTestCase):
    """Common functionality for account request repository test case classes."""

    @override
    def _provide_configuration(self):
        return "testconfig"

    @override
    def before_each(self) -> None:
        os.mkdir(self.configuration.user_pending)

    def _path(self, accreq_id: str) -> str:
        """Returns the path of an account request file."""
        return os.path.join(self.configuration.user_pending, accreq_id)


class TestSave(AccountRequestRepositoryTestCase):

    def test_creates_file_at_expected_path(self) -> None:
        repository = AccountRequestRepository(self.configuration)

        accreq = test_account_request.copy()
        actual_id = repository.save(accreq)
        actual_path = self._path(actual_id)

        self.assertPathWithin(actual_path, self.configuration.user_pending)
        self.assertFileExists(actual_path)

    def test_creates_file_with_expected_pickled_content(self) -> None:
        repository = AccountRequestRepository(self.configuration)

        accreq = test_account_request.copy()
        actual_id = repository.save(accreq)
        actual_path = self._path(actual_id)

        self.assertFileExists(actual_path)
        actual_loaded_content = load(actual_path)
        self.assertEqual(actual_loaded_content, accreq.to_dict())


class TestRemove(AccountRequestRepositoryTestCase):

    def test_raises_exception_for_nonexisting(self) -> None:
        repository = AccountRequestRepository(self.configuration)
        with self.assertRaises(FileNotFoundError):
            repository.remove("nonexisting-id")

    def test_removes_saved_account_request(self) -> None:
        repository = AccountRequestRepository(self.configuration)
        accreq = test_account_request.copy()
        actual_id = repository.save(accreq)
        actual_path = self._path(actual_id)

        repository.remove(actual_id)

        self.assertFileNotExist(actual_path)

    def test_not_idempotent(self) -> None:
        repository = AccountRequestRepository(self.configuration)
        accreq = test_account_request.copy()
        actual_id = repository.save(accreq)
        actual_path = self._path(actual_id)

        repository.remove(actual_id)
        with self.assertRaises(FileNotFoundError):
            repository.remove(actual_id)


class TestReadAll(AccountRequestRepositoryTestCase):

    def test_return_empty_list_if_no_account_requests(self) -> None:
        repository = AccountRequestRepository(self.configuration)

        actual = repository.read_all()

        self.assertEqual(actual, [])

    def test_saved_account_requests(self) -> None:
        repository = AccountRequestRepository(self.configuration)

        # prepare some account requests
        expected = []
        for i in range(3):
            accreq = test_account_request.copy()
            accreq.email = "external{}@example.com".format(i + 1)
            accreq.fill_distinguished_name()
            repository.save(accreq)
            expected.append(accreq)

        actual = repository.read_all()
        self.assertEqual(sorted(actual, key=lambda req: req.email), expected)
