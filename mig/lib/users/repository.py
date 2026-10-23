#
# --- BEGIN_HEADER ---
#
#
# repository - Functionality related to the account request repository.
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

"""Functionality related to the account request repository."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass

from mig.lib.users.user import User
from mig.shared.serial import dump, load
from mig.shared.userdb import default_db_path, lock_user_db, unlock_user_db

log = logging.getLogger(__name__)


@dataclass
class UserSearchFilter:
    """Responsible for filtering user records based on the specified fields."""

    email: str | None

    def include(self, user: User) -> bool:
        """Whether to include a specific user according to this filter.

        :param user: The user to decide inclusion for.
        :return: True if user should be included in search results, False
            otherwise.
        """

        if self.email and self.email != user.email:
            return False

        return True


class UserRepository:
    """Encapsulates logic related to reading and writing user objects from the
    user database.
    """

    def __init__(self, configuration: object) -> None:
        self._user_db_path = default_db_path(configuration)

    @contextmanager
    def _lock_user_db(self, exclusive: bool):
        """A context manager that locks the user database, when entered, and
        automatically unlocks the user database when exited.

        >>> with self._lock_user_db(exclusive=True):
        >>>    ... # do stuff while DB is locked
        >>> ... # outside the with-block, the user DB is unlocked again.
        """
        lock = lock_user_db(self._user_db_path, exclusive=exclusive)
        try:
            yield
        finally:
            unlock_user_db(lock)

    def save(self, user: User) -> None:
        """Saves the specified user record into the user database."""
        with self._lock_user_db(exclusive=True):
            user_db: dict[str, dict[str, Any]] = load(self._user_db_path)  # type: ignore
            user_db[user.distinguished_name] = user.to_dict()
            dump(user_db, self._user_db_path)
        log.info(
            "saved user record distinguished_name=%r",
            user.distinguished_name,
        )

    def read_all(self) -> dict[str, User]:
        """Reads all users from the user database.

        :return: All users as a dictionary, mapping distinguished names to user
            data dictionaries.
        """
        with self._lock_user_db(exclusive=False):
            userdb = load(self._user_db_path)

        result = {}
        for user_dn, user_data in userdb.items():  # type: ignore
            user = User.from_dict(user_data)
            if user:
                result[user_dn] = user

        log.info("read all users from user database count=%d", len(result))
        return result

    def search(
        self,
        search_filter: UserSearchFilter,
        search_in: list[User] | None = None,
    ) -> list[User]:
        """Searches for users matching the given filter.

        :param search_filter: The filter to use for filtering search results.
        :param search_in: Optionally search in this list of users rather than
            reading the whole user database. Useful for repeated searches.
        :return: All users that matched the search criteria.
        """
        result = []

        if not search_in:
            search_in = list(self.read_all().values())

        for user in search_in:
            if search_filter.include(user):
                result.append(user)

        log.info(
            "searched users found count=%d total=%d",
            len(result),
            len(search_in),
        )
        return result
