#
# --- BEGIN_HEADER ---
#
#
# repository - Functionality related to the account request repository
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
import os
from typing import Any

from mig.shared.accountreq import save_account_request
from mig.shared.fileio import unpickle
from mig.shared.serial import load

from .account_request import AccountRequest

log = logging.getLogger(__name__)


class AccountRequestRepository:
    """Encapsulates logic related to reading and writing account request
    objects.
    """

    def __init__(self, configuration: Any) -> None:
        """Initialize an account request repository.

        :param configuration: A reference to the configuration object.
        """
        self._cfg = configuration
        self._initialize_directory()

    def _initialize_directory(self) -> None:
        try:
            os.mkdir(self._cfg.user_pending)
        except FileExistsError:
            pass

    def _path(self, accreq_id: str) -> str:
        """Returns the path to an account request file.

        :param accreq_id: The ID of the account request.
        """
        return os.path.join(self._cfg.user_pending, accreq_id)

    def read(self, accreq_id: str) -> AccountRequest | None:
        """Read the identified account request.

        :param accreq_id: The ID of the account request to read.
        """
        try:

            accreq_data = load(self._path(accreq_id))
        except FileNotFoundError:
            return None
        except Exception:
            log.exception("error occurred loading account request")
            return None

        return AccountRequest.from_dict(accreq_data)  # type: ignore

    def save(self, accreq: AccountRequest) -> str:
        """Save the given account request.

        :param accreq: The account request to save.
        """
        status, path_or_err = save_account_request(self._cfg, accreq.to_dict())
        if not status:
            log.warning(
                "Error occurred saving account request %r",
                accreq.to_masked_dict(),
            )
            raise Exception(path_or_err)
        log.info("Saved account request %r", accreq.to_masked_dict())
        return os.path.basename(path_or_err)

    def remove(self, accreq_id: str) -> None:
        """Removes the specified account request, if it exists. Raises
        `FileNotFoundError` if it does not exist.

        :param accreq_id: The ID of the account request to remove.
        """
        try:
            os.remove(os.path.join(self._cfg.user_pending, accreq_id))
        except Exception:
            log.info("Error occurred removing account request %r", accreq_id)
            raise
        log.info("Removed account request %r", accreq_id)

    def read_all(self) -> list[AccountRequest]:
        """Read all account requests.

        :return: All account requests.
        """
        try:
            accreq_ids = os.listdir(self._cfg.user_pending)
        except Exception as err:
            log.warning("Error occurred reading all account requests: %r", err)
            return []

        accreqs = []
        for accreq_id in accreq_ids:
            data = unpickle(self._path(accreq_id), log)
            accreq = AccountRequest.from_dict(data)  # type: ignore
            if accreq is not None:
                accreqs.append(accreq)

        log.info("Read all account requests count=%d", len(accreqs))
        return accreqs
