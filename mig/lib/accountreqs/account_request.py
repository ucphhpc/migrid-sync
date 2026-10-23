#
# --- BEGIN_HEADER ---
#
#
# account_request - Definition and logic of account request records.
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

"""Definition and logic of account request records."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mig.shared.base import mask_creds
from mig.shared.defaults import gdp_distinguished_field

log = logging.getLogger(__name__)


@dataclass
class AccountRequest:
    """An account request record."""

    comment: str
    country: str
    created: datetime
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
    gdp: str | None = None

    @property
    def distinguished_name(self) -> str:
        """Computes the distinguished_name based on the account request fields.

        Please note that MiG certificates get empty fields set to NA, so this
        is translated here, too.
        """

        dn = ""
        for key, val in [
            ("C", self.country),
            ("ST", self.state),
            ("L", self.locality),
            ("O", self.organization),
            ("OU", self.organizational_unit),
            ("CN", self.full_name),
            ("emailAddress", self.email),
        ]:
            dn += "/%s=%s" % (key, val or "NA")

        gdp = self.gdp
        if gdp:
            dn += "/%s=%s" % (gdp_distinguished_field, gdp)

        return dn

    def to_masked_dict(self) -> dict[str, Any]:
        """Returns a dictionary containing the data of the accoutn request, with
        sensitive fields (e.g. credentials) masked.
        """
        return mask_creds(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary containing the data of the account request
        record.
        """

        result = {
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

        if self.gdp:
            result["GDP"] = self.gdp

        return result

    def copy(self) -> AccountRequest:
        """Returns a copy of the account request."""
        if accreq := AccountRequest.from_dict(self.to_dict()):
            return accreq
        raise ValueError("error copying AccountRequest")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccountRequest | None:
        """Create an account request record from the given data dictionary.

        Returns None if the data is not valid.
        """
        try:
            return cls(
                comment=data["comment"],
                country=data["country"],
                created=datetime.fromtimestamp(data["created"]),
                email=data["email"],
                expire=(
                    datetime.fromtimestamp(data["expire"])
                    if "expire" in data
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
                gdp=data.get("GDP"),
            )
        except Exception as err:
            log.warning(
                "Error initializing account request: error=%r data=%r",
                err,
                mask_creds(data),
            )
            return None
