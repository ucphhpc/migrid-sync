# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# validation - input validation for peers API
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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Input validation for peers API."""

import datetime

from mig.lib.peers.parsing import EXTRA_PEER_FIELDS, EXTRA_PEER_FIELDS_TYPE
from mig.lib.peers.permissions import peers_permit_allowed
from mig.lib.reqinfo import unlistify_dict
from mig.shared.base import distinguished_name_to_user
from mig.shared.defaults import peers_expire_max_days, peers_expire_min_days
from mig.shared.safeinput import (
    REJECT_UNSET,
    valid_boolean,
    valid_date,
    valid_distinguished_name,
    valid_peer_expire_optional,
    valid_peer_kind,
    valid_peer_label,
    valid_peers_csvlines,
    validated_input,
)

PEER_DN_TYPE_MAP = {"peer": valid_distinguished_name}
PEER_EXPIRE_TYPE_MAP = {"expire": valid_date}
PEER_NOTIFY_TYPE_MAP = {"invite_on_email": valid_boolean}
PEER_CSVLINES_TYPE_MAP = {
    "csvlines": valid_peers_csvlines,
}


def validate_input_peer_distinguished_name(peer):
    """Validates that the peer has a valid structure and only allowed characters

    peer: {"peer": peer_dn}
    """
    signature = {"peer": REJECT_UNSET}
    accepted, rejected = validated_input(
        peer, signature, type_override=PEER_DN_TYPE_MAP, list_wrap=True
    )
    return unlistify_dict(accepted), unlistify_dict(rejected)


def validate_input_peers_distinguished_names(peers):
    """Validates the input of a list of peers

    peers: [{"peer": peer_dn}]
    """
    peer_validations = []
    for peer in peers:
        accepted, rejected = validate_input_peer_distinguished_name(peer)
        peer_validation_results = {
            "accepted": accepted,
            "rejected": rejected,
        }
        peer_validations.append(peer_validation_results)
    return peer_validations


def validate_peer_expire(expire):
    """Validates that the peer expire value has a valid structure and only allowed characters

    expire: {"expire": expire}
    """
    signature = {"expire": REJECT_UNSET}
    accepted, rejected = validated_input(
        expire, signature, type_override=PEER_EXPIRE_TYPE_MAP, list_wrap=True
    )
    return unlistify_dict(accepted), unlistify_dict(rejected)


def validate_peer_invite_on_email(invite_on_email):
    """Validates that the notify value has a valid structure and only allowed characters

    invite_on_email: {"invite_on_email": invite_on_email}
    """
    signature = {"invite_on_email": REJECT_UNSET}
    accepted, rejected = validated_input(
        invite_on_email,
        signature,
        type_override=PEER_NOTIFY_TYPE_MAP,
        list_wrap=True,
    )
    return unlistify_dict(accepted), unlistify_dict(rejected)


def validate_peers_import_fields(import_args):
    """Validates the input of a peer import

    import_args: {"label": label, "kind": kind, "expire": expire}
    """
    signature = {
        "label": [""],
        "kind": [""],
        "expire": EXTRA_PEER_FIELDS["expire"],
    }
    accepted, rejected = validated_input(
        import_args,
        signature,
        type_override=EXTRA_PEER_FIELDS_TYPE,
        list_wrap=True,
    )
    return unlistify_dict(accepted), unlistify_dict(rejected)


def validate_peers_update_fields(update_args):
    """Validates the input of a peer update

    update_args: {"label": label, "kind": kind, "expire": expire}
    """
    # During an update these are optional
    signature = {"label": [""], "kind": [""], "expire": [""]}

    accepted, rejected = validated_input(
        update_args,
        signature,
        type_override={
            "label": valid_peer_label,
            "kind": valid_peer_kind,
            "expire": valid_peer_expire_optional,
        },
        list_wrap=True,
    )
    return unlistify_dict(accepted), unlistify_dict(rejected)


def validate_peers_csvlines(csvlines):
    """Validates that the csvlines have a valid structure and only allowed characters

    csvlines: {"csvlines": csvlines}
    """
    signature = {"csvlines": REJECT_UNSET}
    accepted, rejected = validated_input(
        csvlines,
        signature,
        type_override=PEER_CSVLINES_TYPE_MAP,
        list_wrap=True,
    )
    return accepted, rejected


def check_peers_permit(configuration, client_id):
    """Check if the requesting client is permitted to manage peers.

    Returns True if permitted, False otherwise.
    """
    user_dict = distinguished_name_to_user(client_id)
    return peers_permit_allowed(configuration, user_dict)


def validate_peer_expire_value(expire_date):
    try:
        expire = datetime.datetime.strptime(expire_date, "%Y-%m-%d")
    except ValueError:
        return False, "incorrect expire format given, expected YYYY-MM-DD"
    now = datetime.datetime.now()

    if now + datetime.timedelta(days=peers_expire_min_days) > expire:
        return (
            False,
            "the specified expire must be at least %s days ahead of today!"
            % peers_expire_min_days,
        )
    if now + datetime.timedelta(days=peers_expire_max_days) < expire:
        return (
            False,
            "the specified expire is too far in the future, must be within %s days!"
            % peers_expire_max_days,
        )
    return True, "specified expire is valid!"
