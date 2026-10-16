"""Logic related to account request objects."""

from __future__ import annotations

import logging
import os
from typing import Any

from .account_request import AccountRequest
from mig.shared.accountreq import save_account_request
from mig.shared.fileio import unpickle

log = logging.getLogger(__name__)


class AccountRequestRepository:
    """Encapsulates logic related to reading and writing account request
    objects."""

    def __init__(self, configuration: Any) -> None:
        """Initialize an account request repository."""
        self._cfg = configuration

    def _path(self, accreq_id: str) -> str:
        """Returns the path to an account request file."""
        return os.path.join(self._cfg.user_pending, accreq_id)

    def save(self, accreq: AccountRequest) -> str:
        """Save the given account request."""
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
        `FileNotFoundError` if it does not exist."""
        try:
            os.remove(os.path.join(self._cfg.user_pending, accreq_id))
        except Exception:
            log.info("Error occurred removing account request %r", accreq_id)
            raise
        log.info("Removed account request %r", accreq_id)

    def read_all(self) -> list[AccountRequest]:
        """Read all account requests."""
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
