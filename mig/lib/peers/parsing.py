#
# --- BEGIN_HEADER ---
#
# parsing - parse peers from various formats
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

"""Parse peers from various formats."""

from builtins import zip

from mig.shared.base import (
    canonical_user,
    distinguished_name_to_user,
    fill_distinguished_name,
    fill_user,
)
from mig.shared.defaults import keyword_auto, peers_fields
from mig.shared.safeinput import (
    REJECT_UNSET,
    html_escape,
    valid_date,
    valid_peer_kind,
    valid_peer_label,
    validated_input,
)
from mig.shared.validstring import valid_email_addresses

BASIC_PEER_FIELDS = dict([(i, REJECT_UNSET) for i in peers_fields])
EXTRA_PEER_FIELDS_TYPE = {
    "expire": valid_date,
    "kind": valid_peer_kind,
    "label": valid_peer_label,
}
EXTRA_PEER_FIELDS = {
    "expire": REJECT_UNSET,
    "kind": REJECT_UNSET,
    "label": REJECT_UNSET,
}


def _unlistify_dict(thedict):
    """A module helper for converting a dictionary
    of lists to a dictionary of values.
    """
    return {key: value[0] for key, value in thedict.items()}


def _unlisty(thelist):
    """A module helper for extracting the first element of a list."""
    if isinstance(thelist, list):
        return thelist[0]
    return thelist


def _normalize_rejected_value(failure_detail):
    """
    Convert single rejected field value to an error string.

    The complexity here is necessary because different
    rejections cause different structures to be returned
    as values of rejected keys. Try to make something
    presentable in the UI from what we get.

    failure_detail: is expected to be either a list, a tuple
    or a string. The format is defined by how the value was rejected.
    """
    normalized_details = []
    if isinstance(failure_detail, list):
        # When the rejected structure is a list, the first element
        # is an error identifier, and the second is the error message.
        unlisted_failure = _unlisty(failure_detail)
        normalized_details.append(unlisted_failure[-1])
    elif isinstance(failure_detail, tuple) and len(failure_detail) == 2:
        # When the rejected structure is a tuple, the first element is the
        # input field key, and the second is a list with the error message.
        key = failure_detail[0]
        value = _unlisty(failure_detail[1])
        normalized_details.append(value)
    elif isinstance(failure_detail, str):
        normalized_details.append(failure_detail)
    else:
        normalized_details.append(
            "the field value was rejected for unknown reasons"
        )
    return " ".join(normalized_details)


def _normalize_rejected(rejected):
    """
    Make a dictionary of rejected fields uniform.
    """
    return {
        key: _normalize_rejected_value(value) for key, value in rejected.items()
    }


def peer_dict_from_fields(configuration, peer_fields_dict):
    """
    Creates a peer_dict from a simple dictionary containing fields
    and their values ensuring the validity of the key/value pairs.
    """

    rejected = {}
    basic_fields = {
        field_name: peer_fields_dict.get(field_name, "").strip()
        for field_name in BASIC_PEER_FIELDS.keys()
    }
    basic_accepted, basic_rejected = validated_input(
        basic_fields, BASIC_PEER_FIELDS, list_wrap=True
    )
    rejected.update(basic_rejected)
    # There is no choice but use list_wrap during validation - not doing
    # so leads to accepted containing arrays of the _characters_ within the
    # values. This is unfortunate. It means we get our input values back from
    # validation wrapped in arrays, so we need to undo that.
    peer_dict = _unlistify_dict(basic_accepted)

    # the only remaining fields should now be the extra fields
    extra_fields = {
        k: v for k, v in peer_fields_dict.items() if k not in BASIC_PEER_FIELDS
    }
    try:
        extra_accepted, extra_rejected = validated_input(
            extra_fields,
            EXTRA_PEER_FIELDS,
            EXTRA_PEER_FIELDS_TYPE,
            list_wrap=True,
        )
    except Exception as any_exc:
        # unfortunately validated_input itself is not safe against input
        # data that is not wrapped the way it expects - treat this an error
        extra_accepted = {}
        extra_rejected = {k: "invalid value" for k in EXTRA_PEER_FIELDS.keys()}
    rejected.update(extra_rejected)
    peer_dict.update(_unlistify_dict(extra_accepted))

    if rejected:
        errors = _normalize_rejected(rejected)
        return peer_dict, errors

    # nudge expire into a unix time
    peer_dict = fill_user(peer_dict)
    # This is required to match how client_id pending_peers are currently loaded
    combined_accepted_fields = list(basic_accepted.keys()) + list(
        extra_accepted.keys()
    )
    canonicaled_peer_dict = canonical_user(
        configuration, peer_dict, combined_accepted_fields
    )
    filled_canonicaled_peer_dict = fill_distinguished_name(
        canonicaled_peer_dict
    )
    return filled_canonicaled_peer_dict, None
