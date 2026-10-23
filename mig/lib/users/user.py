from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import logging
from typing import Any

from mig.shared.base import mask_creds
from mig.shared.defaults import gdp_distinguished_field

log = logging.getLogger(__name__)


@dataclass
class User:
    """A user record."""

    country: str
    email: str
    created: datetime | None
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

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary containing the data of the user
        record.
        """

        result = {
            "country": self.country,
            "created": self.created.timestamp() if self.created else None,
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User | None:
        """Create a user record from the given data dictionary.

        Returns None if an exception if the data is not valid.
        """
        try:
            return cls(
                country=data["country"],
                email=data["email"],
                created=(
                    datetime.fromtimestamp(data["created"])
                    if "created" in data
                    else None
                ),
                expire=(
                    datetime.fromtimestamp(data["expire"])
                    if "expire" in data
                    else None
                ),
                full_name=data["full_name"],
                locality=data["locality"],
                openid_names=data.get("openid_names", []),
                organization=data["organization"],
                organizational_unit=data["organizational_unit"],
                password=data.get("password", ""),
                password_hash=data.get("password_hash", ""),
                path=data.get("path", ""),
                peers_email=data.get("peers_email", ""),
                peers_full_name=data.get("peers_full_name", ""),
                state=data.get("state", ""),
            )
        except Exception as err:
            log.warning(
                "Error initializing user record: error=%r data=%r",
                err,
                mask_creds(data),
            )
            return None

    def copy(self) -> User:
        return User(**asdict(self))
