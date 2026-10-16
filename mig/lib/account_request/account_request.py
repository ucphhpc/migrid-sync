"""Logic related to account request objects."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mig.shared.base import fill_distinguished_name, mask_creds

log = logging.getLogger(__name__)


@dataclass
class AccountRequest:
    """An account request record."""

    comment: str
    country: str
    created: datetime
    distinguished_name: str
    email: str
    expire: datetime | None
    full_name: str
    locality: str
    openid_names: list[str]
    organization: str
    organizational_unit: str
    password: str
    password_hash: str
    path: str | None
    peers_full_name: str
    peers_email: str
    state: str

    def fill_distinguished_name(self) -> None:
        """Fill distinguished_name field from other fields if not already set.

        Please note that MiG certificates get empty fields set to NA, so this
        is translated here, too.
        """
        self.distinguished_name = fill_distinguished_name(self.to_dict())[
            "distinguished_name"
        ]

    def to_masked_dict(self) -> dict[str, Any]:
        """Returns a dictionary containing the data of the accoutn request, with
        sensitive fields (e.g. credentials) masked.
        """
        return mask_creds(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary containing the data of the account request
        record.
        """

        return {
            "comment": self.comment,
            "country": self.country,
            "created": self.created.timestamp(),
            "distinguished_name": self.distinguished_name,
            "email": self.email,
            "expire": self.expire.timestamp() if self.expire else None,
            "full_name": self.full_name,
            "locality": self.locality,
            "openid_names": self.openid_names,
            "organization": self.organization,
            "organizational_unit": self.organizational_unit,
            "password": self.password,
            "password_hash": self.password_hash,
            "peers_email": self.peers_email,
            "peers_full_name": self.peers_full_name,
            "state": self.state,
            "path": self.path,
        }

    def copy(self) -> AccountRequest:
        """Returns a copy of the account request."""
        if accreq := AccountRequest.from_dict(self.to_dict()):
            return accreq
        raise ValueError("error copying AccountRequest")

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AccountRequest | None:
        """Create an account request record from the given data dictionary.

        Returns None if an exception if the data is not valid.
        """
        try:
            return AccountRequest(
                comment=data["comment"],
                country=data["country"],
                created=datetime.fromtimestamp(data["created"]),
                distinguished_name=data["distinguished_name"],
                email=data["email"],
                expire=(
                    datetime.fromtimestamp(data["expire"])
                    if data["expire"]
                    else None
                ),
                full_name=data["full_name"],
                locality=data["locality"],
                openid_names=data["openid_names"],
                organization=data["organization"],
                organizational_unit=data["organizational_unit"],
                password=data["password"],
                password_hash=data["password_hash"],
                path=data["path"],
                peers_email=data["peers_email"],
                peers_full_name=data["peers_full_name"],
                state=data["state"],
            )
        except Exception as err:
            log.warning(
                "Error initializing account request: error=%r data=%r",
                err,
                mask_creds(data),
            )
            return None
