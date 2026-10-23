#
# --- BEGIN_HEADER ---
#
#
# api - API route handlers for account request management
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

"""API route handlers for account request management."""

from __future__ import annotations

from typing import Any, TypedDict

from mig.lib.accountreqs import AccountRequestRepository
from mig.lib.accountreqs.permissions import check_account_requests_permit
from mig.lib.peers.storage import (
    add_pending_peers_to_client,
    list_peers_accepted,
    list_peers_requested,
)
from mig.lib.reqinfo import _RequestInfo
from mig.lib.users.repository import UserRepository, UserSearchFilter


class HandlerExitResponse(TypedDict):
    """A definition of the non-data part of the JSON response."""

    status: int
    message: str | None
    error: str | None


HandlerResponse = tuple[HandlerExitResponse, dict[str, Any]]


def _create_handler_response(
    status: int,
    message: str | None = None,
    error: str | None = None,
    **response_data: Any,
) -> HandlerResponse:
    """Utility function to format request handler JSON response.

    :param status: An HTTP status code.
    :param message: A message to return in the response.
    :param error: An error to return in the response.
    :param response_data: Key-value arguments that will be available in the
        response object under the 'data' key.
    """
    return (
        {"status": status, "message": message, "error": error},
        response_data,
    )


def get_summary(
    configuration: object, request_info: _RequestInfo
) -> HandlerResponse:
    """
    Request handler: GET /accountreqs/summary
    """
    if not check_account_requests_permit(configuration, request_info.client_id):
        return _create_handler_response(
            403, error="you are not permitted to manage peers"
        )

    # TODO: dependency injection
    accreq_repo = AccountRequestRepository(configuration)
    user_repo = UserRepository(configuration)

    invalid_peer_contact = 0
    requested = 0
    peer_pending = 0
    peer_accepted = 0

    all_users = list(user_repo.read_all().values())
    for accreq in accreq_repo.read_all():
        peer_contacts = user_repo.search(
            UserSearchFilter(accreq.peers_email), all_users
        )

        # no valid peer contact found
        if not peer_contacts:
            invalid_peer_contact += 1
            continue

        # TODO: consider multiple peer contacts
        peer_contact = peer_contacts[0]

        # this account request is in the peer pending state
        peers_pending = list_peers_requested(
            configuration, peer_contact.distinguished_name
        )
        pending_peer_dns = [pending["distinguished_name"] for pending in peers_pending]  # type: ignore
        if accreq.distinguished_name in pending_peer_dns:
            peer_pending += 1
            continue

        # this account request is in the peer accepted state
        if accreq.distinguished_name in list_peers_accepted(  # type: ignore
            configuration, peer_contact.distinguished_name
        ):
            peer_accepted += 1
            continue

        # the account request is in the requested state
        requested += 1

    summary = {
        "invalid_peer_contact": invalid_peer_contact,
        "requested": requested,
        "peer_pending": peer_pending,
        "peer_accepted": peer_accepted,
    }
    return _create_handler_response(200, summary=summary)


def post_forward(
    configuration: object, request_info: _RequestInfo
) -> HandlerResponse:
    """
    Request handler: POST /accountreqs/forward
    """
    if not check_account_requests_permit(configuration, request_info.client_id):
        return _create_handler_response(
            403, error="you are not permitted to manage peers"
        )

    # TODO: dependency injection
    accreq_repo = AccountRequestRepository(configuration)
    user_repo = UserRepository(configuration)

    accreq_ids = request_info.arg_value("account_request_ids", list)

    errors: dict[str, str] = {}
    successes: list[str] = []
    for accreq_id in accreq_ids:
        accreq = accreq_repo.read(accreq_id)
        if accreq is None:
            errors[accreq_id] = "account request not found"
            continue

        peer_contacts = user_repo.search(UserSearchFilter(accreq.peers_email))
        if not peer_contacts:
            errors[accreq_id] = "no valid peer contact found"

        # TODO: handle more peer contacts
        peer_contact = peer_contacts[0]

        if not add_pending_peers_to_client(
            configuration,
            peer_contact.distinguished_name,
            [(accreq.distinguished_name, accreq.to_dict())],
        ):
            errors[accreq_id] = (
                "error occurred adding pending peer to peer contact"
            )
        successes.append(accreq_id)

    return _create_handler_response(
        400 if errors else 200, errors=errors, successes=successes
    )


HANDLERS_BY_PACKAGE = {
    "accountrequests": {
        "GET /summary": get_summary,
        "POST /forward": post_forward,
    },
}

NORMALIZE_INPUTS_BY_PACKAGE = {"account_requests": {}}
