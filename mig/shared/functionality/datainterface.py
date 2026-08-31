# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# datainterface.py - structured data request and response endpoint
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
# -- END_HEADER ---

"""
datainterface is a functionality module intended to expose routes consuming
and returning data structures within constraints of the usually page-centric
MiGrid request/response model.

Dynamic web applications are usually structured around making inidividual
requests to a series of routes to request data or operations. This module
carefully provides a bridge allowing a series of routes to be exposed by MiG.

The primary constraints are an inability to make direct use of URL paths and
the only usable submission medium for structured data being a POST. We define
a json payload which encodes the route information. This is normalized upon an
incoming request and the corresponding route handler triggered with a simple
dictionary of args. This resembles flask or FastAPI in the Python world.

Note the above design takes some cues from the jsoninterface module but unlike
it, which is very specfic to workflows and was not desgined for extensibility,
the ability to easily extend the routes made avalable is a key feature here.
"""

from __future__ import absolute_import

import cgi
import datetime
import json
import os
import sys
from io import BytesIO

from mig.lib.reqinfo import (
    booleanify,
    coalesce_request,
    unconcatify,
    unlistify,
    unlistify_dict,
)
from mig.shared import accountreq, returnvalues
from mig.shared.base import extract_field, fill_user
from mig.shared.defaults import (
    keyword_auto,
    peers_expire_max_days,
    peers_expire_min_days,
    peers_fields,
)
from mig.shared.init import (
    find_entry,
    initialize_main_variables,
    make_start_entry,
)
from mig.shared.notification import send_email
from mig.shared.safeinput import (
    REJECT_UNSET,
    html_escape,
    valid_boolean,
    valid_date,
    valid_distinguished_name,
    valid_peer_kind,
    valid_peer_label,
    valid_peers_csvlines,
    validated_input,
)
from mig.shared.scriptinput import fieldstorage_to_dict
from mig.shared.url import urlencode

PEER_DN_TYPE_MAP = {"peer": valid_distinguished_name}
PEER_EXPIRE_TYPE_MAP = {"expire": valid_date}
PEER_NOTIFY_TYPE_MAP = {"invite_on_email": valid_boolean}
PEER_CSVLINES_TYPE_MAP = {
    "csvlines": valid_peers_csvlines,
}


# TODO, move the helper functions and the peers related handlers/normalizers
# into their own submodule
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
        "expire": accountreq.EXTRA_PEER_FIELDS["expire"],
    }
    accepted, rejected = validated_input(
        import_args,
        signature,
        type_override=accountreq.EXTRA_PEER_FIELDS_TYPE,
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
            "expire": valid_date,
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


def create_handler_response(status, message=None, **ui_response_kwargs):
    """
    A helper function to create route handler responses.
    """
    if message is None:
        message = "an unspecified error occurred"

    response = {"status": status, "message": message}, {**ui_response_kwargs}
    return response


def create_peers_notify_msg(
    header_title, header_action, header_from, body_identifer, peers
):
    """A helper funtion to create a peers notification mesage"""
    notify_header = "%s %s by %s" % (
        header_title,
        header_action,
        header_from,
    )

    notify_peers = [
        """
            "Peer: %s
            "Expire: %s
        """ % (peer_dn, peer_dict["expire"])
        for peer_dn, peer_dict in peers.items()
    ]
    notify_dict = {
        "action": header_action,
        "body_identifer": body_identifer,
        "peers": "".join(notify_peers),
    }
    notify_msg = """
        Received %(action)s from %(body_identifer)s

        Peers:
        %(peers)s
    """ % notify_dict

    return {"header": notify_header, "msg": notify_msg}


def create_peer_invitation_msg(
    configuration, client_name, client_email, peer_user, kind
):
    """Create an invitation email message (header + body) for a single peer.

    Returns a dict with 'header' and 'msg' keys containing the email header
    and body respectively.
    """
    _logger = configuration.logger
    short_title = configuration.short_title
    admin_email = configuration.admin_email
    email_header = "%s Invitation" % short_title

    peer_url = os.path.join(
        configuration.migserver_https_sid_url, "cgi-sid", "reqoid.py"
    )

    peer_req = {}
    for field in peers_fields:
        peer_req[field] = peer_user.get(field, "")

    for explicit_field in configuration.site_peers_explicit_fields:
        field_name = "peers_%s" % explicit_field
        if explicit_field == "full_name":
            peer_req[field_name] = client_name
        elif explicit_field == "email":
            peer_req[field_name] = client_email
        else:
            _logger.warning(
                "unhandled explicit peers field: %s" % explicit_field
            )
            continue

    peer_req["comment"] = "Invited by %s (%s) for %s purposes" % (
        client_name,
        client_email,
        kind,
    )
    peer_req["ro_fields"] = keyword_auto
    peer_url += "?%s" % urlencode(peer_req)

    peer_name = peer_user.get("full_name", "")
    email_msg_template = """Hi %%s,
This is an automatic email sent on behalf of %s who vouched for you to get a
user account on %s. You can accept the invitation by going to
%%s
entering a password of your choice and submitting the form.
If you do not want a user account you can safely ignore this email.

We would be grateful if you report any abuse of the invitation system to the
site administrators (%s).
""" % (client_name, short_title, admin_email)

    email_msg = email_msg_template % (peer_name, peer_url)
    return {"header": email_header, "msg": email_msg}


def validate_peer_expire_value(expire_date):
    try:
        expire = datetime.datetime.strptime(expire_date, "%Y-%m-%d")
    except ValueError:
        return False, "incorrect expire format given, expected YYYY-MM-DD"
    now = datetime.datetime.now()

    if now + datetime.timedelta(days=peers_expire_min_days) > expire:
        return (
            False,
            "the specified expire must be atleast %s days ahead of today!"
            % peers_expire_min_days,
        )
    if now + datetime.timedelta(days=peers_expire_max_days) < expire:
        return (
            False,
            "the specified expire is too far in the future, must be within %s days!"
            % peers_expire_max_days,
        )
    return True, "specified expire is valid!"


def main(client_id, user_arguments_dict, environ=None, configuration=None):
    """
    Main function used by front end.
    :param client_id: A MiG user.
    :param user_arguments_dict: A JSON message sent to the MiG. This will be
    parsed and if valid, the relevant API handler functions are called to
    generate meaningful output.
    """

    if environ is None:
        environ = os.environ

    # Ensure that the output format is in JSON
    user_arguments_dict["output_format"] = ["json"]
    user_arguments_dict.pop("__DELAYED_INPUT__", None)
    configuration, logger, output_objects, op_name = initialize_main_variables(
        client_id,
        configuration=configuration,
        op_title=False,
        op_header=False,
        op_menu=False,
    )

    # Now ensure output format above is applied by the WSGI wrappers
    start_entry = find_entry(output_objects, "start")
    start_entry["override_format"] = True

    return _main(
        configuration,
        logger,
        environ,
        op_name=op_name,
        output_objects=output_objects,
        client_id=client_id,
        user_arguments_dict=user_arguments_dict,
    )


def handle_GET_peers_summary(configuration, request_info):
    """
    Request handler: GET /peers/summary
    """

    accepted_peers = accountreq.list_peers_accepted(
        configuration, request_info.client_id
    )
    requested_peers = accountreq.list_peers_requested(
        configuration, request_info.client_id
    )

    return create_handler_response(
        200,
        accepted_count=len(accepted_peers),
        requested_count=len(requested_peers),
    )


def convert_POST_peers_send_invitation(request_data):
    """
    Data conversion: POST /peers/send_invitation
    """
    args = request_data
    # Align with the validate_input expectations for an input_dict
    peers = args.get("peers", [])
    args["peers"] = [{"peer": peer} for peer in peers]
    return args


def handle_POST_peers_send_invitation(configuration, request_info):
    """
    Request handler: POST /peers/send_invitation
    """
    peers = request_info.arg_value("peers", list)
    validations = validate_input_peers_distinguished_names(peers)

    validation_errors, validation_accepted = [], []
    for index, validation in enumerate(validations):
        if validation["rejected"]:
            validation_errors.append(validation["rejected"])
        if validation["accepted"]:
            validation_accepted.append(validation["accepted"])

    if validation_errors:
        return create_handler_response(
            400,
            error="failed to send invitations to peers, error: %s "
            % validation_errors,
        )

    # Client existing accepted peers
    accepted_peers = accountreq.list_peers_accepted(
        configuration, request_info.client_id
    )
    accepted_by_dn = {
        peer["distinguished_name"]: peer for peer in accepted_peers.values()
    }
    client_name = extract_field(request_info.client_id, "full_name")

    valid_client_peers_dn, invalid_client_peers_dn = {}, []
    for index, accepted in enumerate(validation_accepted):
        peer_dn = accepted["peer"]
        if peer_dn not in accepted_by_dn:
            invalid_client_peers_dn.append(peer_dn)
        else:
            peer_dict = accepted_by_dn[peer_dn]
            valid_client_peers_dn[peer_dn] = peer_dict

    if invalid_client_peers_dn:
        return create_handler_response(
            400,
            message="you tried to send invitations to peers that you dont have, namely: %s"
            % invalid_client_peers_dn,
        )

    peer_invitations = {}
    for peer_dn, peer_dict in valid_client_peers_dn.items():
        invite_msg = create_peer_invitation_msg(
            configuration,
            client_name,
            request_info.client_email,
            peer_dict,
            peer_dict.get("kind", ""),
        )
        invite_log_msg = (
            "Sending invitation: to: %s, header: %s, msg: %s, smtp_server: %s"
            % (
                peer_dict["email"],
                invite_msg["header"],
                invite_msg["msg"],
                configuration.smtp_server,
            )
        )
        configuration.logger.info(invite_log_msg)
        if not send_email(
            configuration,
            peer_dict["email"],
            invite_msg["header"],
            invite_msg["msg"],
        ):
            configuration.logger.warning(
                "failed to send invitation email to peer %s"
                % peer_dict.get("email", "")
            )
            peer_invitations[peer_dn] = False
        else:
            peer_invitations[peer_dn] = True

    return create_handler_response(200, peer_invitations=peer_invitations)


def convert_POST_peers_new(request_data):
    """
    Data conversion: POST /peers/new
    """
    args = unlistify_dict(request_data)
    # Optional field that will default to false
    args["invite_on_email"] = {
        "invite_on_email": booleanify(args.get("invite_on_email", "false"))
    }
    return args


def handle_POST_peers_new(configuration, request_info):
    """
    Request handler: POST /peers/new
    """

    fields_dict = request_info.args
    input_invite_on_email = fields_dict.pop("invite_on_email")
    accepted_invite, rejected_invite = validate_peer_invite_on_email(
        input_invite_on_email
    )
    if not accepted_invite or rejected_invite:
        return create_handler_response(
            400,
            message="failed to add a new peer, the recieved invite on email argument was rejected %s"
            % rejected_invite,
        )
    invite_on_email = accepted_invite.get("invite_on_email", False)

    success_map = {}
    errors_map = {}
    created_peers = {}
    for index, peer_fields_dict in enumerate([fields_dict]):
        # input validation
        peer_dict, errors = accountreq.peer_dict_from_fields(
            configuration, peer_fields_dict
        )
        if errors:
            success_map[index] = False
            errors_map[index] = errors
            continue

        # validate expire range (min/max days)
        valid_expire, expire_message = validate_peer_expire_value(
            peer_dict["expire"]
        )
        if not valid_expire:
            success_map[index] = False
            errors_map[index] = {"expire": expire_message}
            continue

        # comment field must contain the requesting peer
        peer_dict["comment"] = request_info.client_email

        already_exists, exists_msg = accountreq.peer_already_exists(
            configuration, request_info.client_id, peer_dict["email"]
        )
        if already_exists:
            success_map[index] = False
            errors_map[index] = {"email": exists_msg}
            continue

        peer_dn = peer_dict["distinguished_name"]
        peer_dict = fill_user(peer_dict)
        pending_peer_entry = {peer_dn: peer_dict}
        saved = accountreq.add_accepted_peers_to_client(
            configuration, request_info.client_id, pending_peer_entry
        )
        if not saved:
            # Atm, we are only creating one peer here,
            # so we can return early
            return create_handler_response(
                500,
                message="failed to save the submitted peer, please contact support for help with this.",
            )
        created_peers[peer_dn] = peer_dict
        success_map[index] = True

    if errors_map:
        return create_handler_response(400, errors_map=errors_map)

    if not created_peers:
        return create_handler_response(
            500,
            message="no errors were discovered, but the peer was not created, please contact support about this",
        )

    # Send email to peer about invitation
    client_name = extract_field(request_info.client_id, "full_name")
    if invite_on_email:
        for peer_dn, peer_dict in created_peers.items():
            invite_msg = create_peer_invitation_msg(
                configuration,
                client_name,
                request_info.client_email,
                peer_dict,
                peer_dict.get("kind", ""),
            )
            invite_log_msg = (
                "Sending invitation: to: %s, header: %s, msg: %s, smtp_server: %s"
                % (
                    peer_dict["email"],
                    invite_msg["header"],
                    invite_msg["msg"],
                    configuration.smtp_server,
                )
            )
            configuration.logger.info(invite_log_msg)
            if not send_email(
                configuration,
                peer_dict["email"],
                invite_msg["header"],
                invite_msg["msg"],
            ):
                configuration.logger.warning(
                    "failed to send invitation email to peer %s"
                    % peer_dict.get("email", "")
                )

    # notify admins about the succesful additions
    action = "peers_new"
    notify_dict = create_peers_notify_msg(
        configuration.short_title,
        action,
        client_name,
        request_info.client_id,
        created_peers,
    )

    if not send_email(
        configuration,
        configuration.admin_email,
        notify_dict["header"],
        notify_dict["msg"],
    ):
        configuration.logger.error(
            "failed to send notification to admins about the client %s creating new peers %s"
            % (request_info.client_id, "\n".join(created_peers))
        )

    return create_handler_response(200, success_map=success_map)


def convert_POST_peers_accepted_delete(request_data):
    """
    Data conversion: DELETE /peers/accepted/delete
    """
    args = request_data
    # Align with the validate_input expectations for an input_dict
    peers = args.get("peers", [])
    args["peers"] = [{"peer": peer} for peer in peers]
    return args


def handle_POST_peers_accepted_delete(configuration, request_info):
    """
    Request handler: DELETE /peers/accepted/delete
    """

    peers = request_info.arg_value("peers", list)
    validations = validate_input_peers_distinguished_names(peers)

    validation_errors, validation_accepted = [], []
    for index, validation in enumerate(validations):
        if validation["rejected"]:
            validation_errors.append(validation["rejected"])
        if validation["accepted"]:
            validation_accepted.append(validation["accepted"])

    if validation_errors:
        return create_handler_response(
            400,
            error="failed to remove accepted peers, error: %s "
            % validation_errors,
        )

    # Client existing accepted peers
    accepted_peers = accountreq.list_peers_accepted(
        configuration, request_info.client_id
    )
    accepted_by_dn = {
        peer["distinguished_name"]: peer for peer in accepted_peers.values()
    }

    valid_client_peers_dn, invalid_client_peers_dn = [], []
    for index, accepted in enumerate(validation_accepted):
        peer_dn = accepted["peer"]
        if peer_dn not in accepted_by_dn:
            invalid_client_peers_dn.append(peer_dn)
        else:
            valid_client_peers_dn.append(peer_dn)

    if invalid_client_peers_dn:
        return create_handler_response(
            400,
            message="invalid peers that you don't have were found in your delete request, namely: %s"
            % invalid_client_peers_dn,
        )

    success_map, errors_map = {}, {}
    peers_deleted = {}
    for index, peer_dn in enumerate(valid_client_peers_dn):
        peer_dict = accepted_by_dn[peer_dn]
        if not accountreq.remove_accepted_peers_from_client(
            configuration, request_info.client_id, [peer_dn]
        ):
            success_map[index] = False
            errors_map[index] = {
                "peer": "failed to remove the peer %s" % peer_dn
            }
            continue
        else:
            # For now we let the janitor clean the global user_pending
            # peers requests
            success_map[index] = True
            peers_deleted[peer_dn] = peer_dict

    if errors_map:
        return create_handler_response(
            400, success_map=success_map, errors_map=errors_map
        )

    # Construct an email that is sent to
    # the configuration.admin_email about the deleted
    # peers and their expiration date
    action = "peers_accepted_delete"
    client_name = extract_field(request_info.client_id, "full_name")
    notify_dict = create_peers_notify_msg(
        configuration.short_title,
        action,
        client_name,
        request_info.client_id,
        peers_deleted,
    )

    if not send_email(
        configuration,
        configuration.admin_email,
        notify_dict["header"],
        notify_dict["msg"],
    ):
        configuration.logger.error(
            "failed to send notification to admins about the client %s deleting the following accepted peers succesfully %s"
            % (request_info.client_id, "\n".join(peers_deleted.keys()))
        )
        # log this error so it is visible to admins, but since the client peers have been deleted, we return it as
        # an success to the client
    return create_handler_response(200, success_map=success_map)


def convert_POST_peers_accepted_fetch(request_data):
    """
    Data conversion: POST /peers/accepted/fetch
    """
    args = unlistify_dict(request_data)
    peer = unlistify(args.pop("peer_dn", ""))
    args["peer"] = {"peer": peer}
    return args


def handle_POST_peers_accepted_fetch(configuration, request_info):
    """
    Request handler: POST /peers/accepted/fetch
    """
    peer = request_info.args["peer"]
    accepted, rejected = validate_input_peer_distinguished_name(peer)

    if not accepted or rejected:
        return create_handler_response(
            400,
            message="failed to fetch the accepted with, recieved an incorrect peer argument %s"
            % rejected,
        )
    peer_dn = accepted["peer"]

    accepted_peers = accountreq.list_peers_accepted(
        configuration, request_info.client_id
    )
    accepted_by_dn = {
        peer["distinguished_name"]: peer for peer in accepted_peers.values()
    }

    if peer_dn not in accepted_by_dn:
        return create_handler_response(404, message="peer not found")
    fetched_peer = accepted_by_dn[peer_dn]
    return create_handler_response(200, **fetched_peer)


def convert_POST_peers_accepted_import(request_data):
    """
    Data conversion: POST /peers/accepted/import
    """
    args = unlistify_dict(request_data)
    args["csvlines"] = unconcatify(args.pop("csvtext", ""), "\n")
    # Optional field that will default to false
    args["invite_on_email"] = {
        "invite_on_email": booleanify(args.get("invite_on_email", "false"))
    }
    return args


def handle_POST_peers_accepted_import(configuration, request_info):
    """
    Request handler: POST /peers/accepted/import
    """
    args = request_info.args
    # Validate invite on email
    input_invite_on_email = args.pop("invite_on_email")
    accepted_invite, rejected_invite = validate_peer_invite_on_email(
        input_invite_on_email
    )
    if not accepted_invite or rejected_invite:
        return create_handler_response(
            400,
            message="failed to import peer(s), the recieved invite on email argument was rejected %s"
            % rejected_invite,
        )
    invite_on_email = accepted_invite.get("invite_on_email", False)

    # Validate the global peers args
    common_peers_args = {
        "label": args.pop("label", ""),
        "kind": args.pop("kind", ""),
        "expire": args.pop("expire", ""),
    }
    accepted_common, rejected_common = validate_peers_import_fields(
        common_peers_args
    )
    if not accepted_common or rejected_common:
        return create_handler_response(
            400,
            message="failed to import peer(s), the recieved import argument(s) was rejected %s"
            % rejected_common,
        )

    # Validate the peers import field
    csvlines = {"csvlines": args.pop("csvlines", [])}
    accepted_csvlines, rejected_csvlines = validate_peers_csvlines(csvlines)
    if not accepted_csvlines or rejected_csvlines:
        return create_handler_response(
            400,
            message="failed to import peer(s), the recieved peers csvlines argument(s) was rejected %s"
            % rejected_csvlines,
        )

    peers = accepted_csvlines.get("csvlines", [])
    parsed_peers, parse_err = accountreq.parse_peers(
        configuration, peers, "csvform"
    )
    if parse_err:
        return create_handler_response(
            400,
            message="failed to import the submitted peers, err %s" % parse_err,
        )

    if not parsed_peers:
        return create_handler_response(
            400,
            message="failed to find any peers in the submitted peers csvlines",
        )

    success_map, errors_map = {}, {}
    created_peers = {}
    for index, peer_fields_dict in enumerate(parsed_peers):
        # Assign global key-value args
        peer_fields_dict["label"] = accepted_common["label"]
        peer_fields_dict["kind"] = accepted_common["kind"]
        peer_fields_dict["expire"] = accepted_common["expire"]

        # input validation
        peer_dict, errors = accountreq.peer_dict_from_fields(
            configuration, peer_fields_dict
        )
        if errors:
            success_map[index] = False
            errors_map[index] = errors
            continue

        # validate expire range (min/max days)
        valid_expire, expire_message = validate_peer_expire_value(
            peer_dict["expire"]
        )
        if not valid_expire:
            success_map[index] = False
            errors_map[index] = {"expire": expire_message}
            continue

        # comment field must contain the requesting peer
        peer_dict["comment"] = request_info.client_email

        already_exists, exists_msg = accountreq.peer_already_exists(
            configuration, request_info.client_id, peer_dict["email"]
        )
        if already_exists:
            success_map[index] = False
            errors_map[index] = {"email": exists_msg}
            continue

        peer_dn = peer_dict["distinguished_name"]
        peer_dict = fill_user(peer_dict)
        pending_peer_entry = {peer_dn: peer_dict}
        saved = accountreq.add_accepted_peers_to_client(
            configuration, request_info.client_id, pending_peer_entry
        )
        if not saved:
            success_map[index] = False
            errors_map[index] = {
                "email": "failed to save the imported peer, please contact support for help with this."
            }
            continue

        created_peers[peer_dn] = peer_dict
        success_map[index] = True

        # validate that an identical existing requested/accepted peer does not exist already
    if errors_map:
        return create_handler_response(400, errors_map=errors_map)

    if not created_peers:
        return create_handler_response(
            500,
            message="no errors were discovered, but the peer was not created, please contact support about this",
        )

    # Send email to peer about invitation
    client_name = extract_field(request_info.client_id, "full_name")
    if invite_on_email:
        for peer_dn, peer_dict in created_peers.items():
            invite_msg = create_peer_invitation_msg(
                configuration,
                client_name,
                request_info.client_email,
                peer_dict,
                peer_dict.get("kind", ""),
            )
            invite_log_msg = (
                "Sending invitation: to: %s, header: %s, msg: %s, smtp_server: %s"
                % (
                    peer_dict["email"],
                    invite_msg["header"],
                    invite_msg["msg"],
                    configuration.smtp_server,
                )
            )
            configuration.logger.info(invite_log_msg)
            if not send_email(
                configuration,
                peer_dict["email"],
                invite_msg["header"],
                invite_msg["msg"],
            ):
                configuration.logger.warning(
                    "failed to send invitation email to peer %s"
                    % peer_dict.get("email", "")
                )

    # notify admins about the succesful import
    action = "peers_accepted_import"
    notify_dict = create_peers_notify_msg(
        configuration.short_title,
        action,
        client_name,
        request_info.client_id,
        created_peers,
    )

    if not send_email(
        configuration,
        configuration.admin_email,
        notify_dict["header"],
        notify_dict["msg"],
    ):
        configuration.logger.error(
            "failed to send notification to admins about the client %s importing new peers %s"
            % (request_info.client_id, "\n".join(created_peers))
        )
    return create_handler_response(200, success_map=success_map)


def convert_POST_peers_accepted_update(request_data):
    """
    Data conversion: POST /peers/accepted/update
    """
    args = unlistify_dict(request_data)
    peer = unlistify(args.pop("peer_dn", ""))
    args["peer"] = {"peer": peer}

    expire = unlistify(args.pop("expire", ""))
    args["expire"] = {"expire": expire}
    return args


def handle_POST_peers_accepted_update(configuration, request_info):
    """
    Request Handler: POST /peers/accepted/update
    """

    args = request_info.args

    input_peer = args["peer"]
    accepted, rejected = validate_input_peer_distinguished_name(input_peer)
    if rejected:
        return create_handler_response(
            400,
            message="failed to update the peer, recieved an incorrect peer argument %s"
            % rejected,
        )
    peer_dn = accepted["peer"]

    # Validate the global peers args
    common_update_args = {
        "label": args.pop("label", ""),
        "kind": args.pop("kind", ""),
        "expire": args.pop("expire", ""),
    }
    accepted_common, rejected_common = validate_peers_update_fields(
        common_update_args
    )
    if not accepted_common or rejected_common:
        return create_handler_response(
            400,
            message="failed to update peer, the recieved update argument(s) was rejected %s"
            % rejected_common,
        )

    label = accepted_common["label"]
    kind = accepted_common["kind"]
    expire = accepted_common["expire"]

    # validate expire range (min/max days)
    valid_expire, expire_message = validate_peer_expire_value(expire)
    if not valid_expire:
        return create_handler_response(
            400,
            message="an incorrect End Date value was recieved.",
            errors_map={"0": {"expire": expire_message}},
        )

    accepted_peers = accountreq.list_peers_accepted(
        configuration, request_info.client_id
    )
    accepted_by_dn = {
        peer["distinguished_name"]: peer for peer in accepted_peers.values()
    }
    if peer_dn not in accepted_by_dn:
        return create_handler_response(
            404, message="you don't have an accepted peer with those details"
        )

    # Update the underlying peer
    update_peer_dict = {
        peer_dn: {"label": label, "kind": kind, "expire": expire}
    }

    if not accountreq.update_peers_accepted(
        configuration, request_info.client_id, update_peer_dict
    ):
        return create_handler_response(
            400, message="failed to update the accepted peer %s" % peer_dn
        )

    updated_peers = accountreq.list_peers_accepted(
        configuration, request_info.client_id
    )

    peers_updated = {peer_dn: updated_peers[peer_dn]}

    # Notify admins about the changes
    action = "peers_accepted_update"
    client_name = extract_field(request_info.client_id, "full_name")

    notify_dict = create_peers_notify_msg(
        configuration.short_title,
        action,
        client_name,
        request_info.client_id,
        peers_updated,
    )
    if not send_email(
        configuration,
        configuration.admin_email,
        notify_dict["header"],
        notify_dict["msg"],
    ):
        configuration.logger.error(
            "failed to send notification to admins about the client %s updating the following accepted peers succesfully %s"
            % (request_info.client_id, "\n".join(peers_updated.keys()))
        )
    return create_handler_response(200)


def convert_POST_peers_requested_delete(request_data):
    """
    Data conversion: DELETE /peers/requested/delete
    """
    args = request_data
    # Align with the validate_input expectations for an input_dict
    peers = args.get("peers", [])
    args["peers"] = [{"peer": peer} for peer in peers]
    return args


def handle_POST_peers_requested_delete(configuration, request_info):
    """
    Request handler: DELETE /peers/requested/delete
    """

    peers = request_info.arg_value("peers", list)
    validations = validate_input_peers_distinguished_names(peers)
    validation_errors, validation_accepted = [], []
    for index, validation in enumerate(validations):
        if validation["rejected"]:
            validation_errors.append(validation["rejected"])
        if validation["accepted"]:
            validation_accepted.append(validation["accepted"])

    if validation_errors:
        return create_handler_response(
            400,
            error="failed to remove requested peers, error: %s "
            % validation_errors,
        )

    # Client existing requested peers
    requested_peers = accountreq.list_peers_requested(
        configuration, request_info.client_id
    )
    requested_by_dn = {
        peer["distinguished_name"]: peer for peer in requested_peers
    }

    valid_client_peers_dn, invalid_client_peers_dn = [], []
    for index, accepted in enumerate(validation_accepted):
        peer_dn = accepted["peer"]
        if peer_dn not in requested_by_dn:
            invalid_client_peers_dn.append(peer_dn)
        else:
            valid_client_peers_dn.append(peer_dn)

    if invalid_client_peers_dn:
        return create_handler_response(
            400,
            message="invalid peers that you don't have were found in your delete request, namely: %s"
            % invalid_client_peers_dn,
        )

    success_map, errors_map = {}, {}
    peers_deleted = {}

    # Client current pending peers
    current_requested_peers = dict(
        accountreq.load_peers_pending(configuration, request_info.client_id)
    )
    for index, peer_dn in enumerate(valid_client_peers_dn):
        peer_dict = current_requested_peers.get(peer_dn, None)
        # Remove the client pending peer
        if not accountreq.remove_pending_peers_from_client(
            configuration, request_info.client_id, [peer_dn]
        ):
            success_map[index] = False
            errors_map[index] = {
                "peer": "failed to remove the peer %s" % peer_dn
            }
            continue

        success_map[index] = True
        peers_deleted[peer_dn] = peer_dict

    if errors_map:
        return create_handler_response(
            400, success_map=success_map, errors_map=errors_map
        )

    # Notify admins about the changes
    action = "peers_requested_delete"
    client_name = extract_field(request_info.client_id, "full_name")

    notify_dict = create_peers_notify_msg(
        configuration.short_title,
        action,
        client_name,
        request_info.client_id,
        peers_deleted,
    )
    if not send_email(
        configuration,
        configuration.admin_email,
        notify_dict["header"],
        notify_dict["msg"],
    ):
        configuration.logger.error(
            "failed to send notification to admins about the client %s deleting the following requested peers succesfully %s"
            % (request_info.client_id, "\n".join(peers_deleted.keys()))
        )
        # send_email logs this error, and since the peers have been deleted, we return it as
        # an success
    return create_handler_response(200, success_map=success_map)


def convert_POST_peers_requested_accept(request_data):
    """
    Data conversion: POST /peers/requested/accept
    """
    args = request_data
    # Align with the validate_input expectations for an input_dict
    peers = args.get("peers", [])
    args["peers"] = [{"peer": peer} for peer in peers]
    return args


def handle_POST_peers_requested_accept(configuration, request_info):
    """
    Request handler: POST /peers/requested/accept
    """

    peers = request_info.arg_value("peers", list)
    validations = validate_input_peers_distinguished_names(peers)

    validation_errors, validation_accepted = [], []
    for index, validation in enumerate(validations):
        if validation["rejected"]:
            validation_errors.append(validation["rejected"])
        if validation["accepted"]:
            validation_accepted.append(validation["accepted"])

    if validation_errors:
        return create_handler_response(
            400,
            error="failed to accepted the peer(s), error: %s "
            % validation_errors,
        )

    accepted_peer_dns = [accepted["peer"] for accepted in validation_accepted]
    existing_requested_peers = accountreq.load_peers_pending(
        configuration, request_info.client_id
    )
    # 0 = peer_dn
    # 1 = peer_dict
    to_accept_peers = {
        peer_tuple[0]: peer_tuple[1]
        for peer_tuple in existing_requested_peers
        if peer_tuple[0] in accepted_peer_dns
    }

    # For now we have a special case user_settings/client_id/pending_peers
    # has its expire format set to an EPOCH value that is set to the
    # maximum when the migadmin.py approves the peer request and forwards
    # it to the users pending_peers file.
    # However the accepted_peers file user_settings/client_id/peers
    # expects it to be the date format YYYY-MN-DD, therefore
    # we have to transform the pending peer expire value when we accept it.
    # In the future when an opportune momement comes we likely want
    # to make the expire format an EPOCH value all the way through and
    # just transform it when display it to a user.

    prepared_to_accept_peers = {}
    for peer_dn, peer_dict in to_accept_peers.items():
        converted_peer_dict = {}
        for key, value in peer_dict.items():
            if key == "expire":
                expire_date = datetime.datetime.fromtimestamp(value).date()
                value = expire_date.strftime("%Y-%m-%d")
            converted_peer_dict[key] = value
        prepared_to_accept_peers[peer_dn] = converted_peer_dict

    # TODO, implement a function that handles the removal and addition
    # in one go such that the entire operation is locked
    if not accountreq.add_accepted_peers_to_client(
        configuration, request_info.client_id, prepared_to_accept_peers
    ):
        return create_handler_response(
            400,
            error="failed to accepted peers",
            errors_map=[
                {index: False} for index, peer_dn in enumerate(to_accept_peers)
            ],
        )

    # If accepted succesfully we can remove the pending peers
    if not accountreq.remove_pending_peers_from_client(
        configuration, request_info.client_id, list(to_accept_peers.keys())
    ):
        return create_handler_response(
            400,
            error="the peers were accepted but the removal of the pending ones failed",
            errors_map=[
                {index: False} for index, peer_dn in enumerate(to_accept_peers)
            ],
        )

    # We don't care about the order
    success_map = {index: True for index, peer_dn in enumerate(to_accept_peers)}

    # notify admins about the succesful additions
    action = "peers_requested_accept"
    client_name = extract_field(request_info.client_id, "full_name")
    notify_dict = create_peers_notify_msg(
        configuration.short_title,
        action,
        client_name,
        request_info.client_id,
        to_accept_peers,
    )

    if not send_email(
        configuration,
        configuration.admin_email,
        notify_dict["header"],
        notify_dict["msg"],
    ):
        configuration.logger.error(
            "failed to send notification to admins about the client %s accepting the pending peers %s"
            % (request_info.client_id, "\n".join(to_accept_peers))
        )

    return create_handler_response(200, success_map=success_map)


HANDLERS_BY_PACKAGE = {
    "peers": {
        "POST /new": handle_POST_peers_new,
        "GET /summary": handle_GET_peers_summary,
        "POST /send_invitation": handle_POST_peers_send_invitation,
        "POST /accepted/delete": handle_POST_peers_accepted_delete,
        "POST /accepted/fetch": handle_POST_peers_accepted_fetch,
        "POST /accepted/import": handle_POST_peers_accepted_import,
        "POST /accepted/update": handle_POST_peers_accepted_update,
        "POST /requested/accept": handle_POST_peers_requested_accept,
        "POST /requested/delete": handle_POST_peers_requested_delete,
    }
}

NORMALIZE_INPUTS_BY_PACKAGE = {
    "peers": {
        "POST /new": convert_POST_peers_new,
        "POST /send_invitation": convert_POST_peers_send_invitation,
        "POST /accepted/delete": convert_POST_peers_accepted_delete,
        "POST /accepted/fetch": convert_POST_peers_accepted_fetch,
        "POST /accepted/import": convert_POST_peers_accepted_import,
        "POST /accepted/update": convert_POST_peers_accepted_update,
        "POST /requested/accept": convert_POST_peers_requested_accept,
        "POST /requested/delete": convert_POST_peers_requested_delete,
    }
}


def create_api_response(
    output_objects, object_status, object_type="objects", **result
):
    """
    A helper function that creates the final
    datainterface API return structure to the output_objects.
    """
    output_objects.append(
        {
            "object_type": object_type,
            "objects": {
                **result,
                "status": object_status,
            },
        }
    )
    return (output_objects, returnvalues.OK)


def _main(
    configuration,
    logger,
    environ,
    op_name="",
    output_objects=None,
    client_id=None,
    user_arguments_dict=None,
):
    # Create new output_objects list with start entry if None was supplied
    if output_objects is None:
        output_objects = [make_start_entry()]

    # Set the response as containining JSON
    output_objects[0]["headers"].append(("Content-Type", "application/json"))

    if "wsgi.version" in environ:
        raw_data = environ["wsgi.input"].read()
    else:
        raw_data = sys.stdin.read()

    requested_content_type = environ.get("CONTENT_TYPE", "multipart/form-data")
    requested_input_format = requested_content_type.split("/")[1]
    request_data = None

    if requested_input_format == "json":
        try:
            request_data = json.loads(raw_data)
        except ValueError:
            msg = (
                "An invalid format was supplied to: '%s', requires a JSON "
                "compatible format" % op_name
            )
            logger.error(msg)
            output_objects.append(
                {"object_type": "error_text", "text": html_escape(msg)}
            )
            return (output_objects, returnvalues.CLIENT_ERROR)
    elif raw_data == b"" and user_arguments_dict:
        # The WSGI input path completely ignores delayed_input and just
        # unconditionally assumes it can process the raw data handle as
        # form data itself which it passes to us as user_arguments_dict.
        # This is likely a factor in many functionality files having
        # issues under WSGI, and means the WSGI input path cannot be made
        # to handle JSON input. But given incoming form data: detect
        # the situation and switch over to pre-parsed data.
        request_data = user_arguments_dict
    else:
        if isinstance(raw_data, str):
            raw_data = bytes(raw_data, "utf8")
        fieldstorage = cgi.FieldStorage(fp=BytesIO(raw_data), environ=environ)
        request_data = fieldstorage_to_dict(fieldstorage)

    # 1. validate data required for a basic JSON request
    errors_info, request_info = coalesce_request(
        request_data, client_id=client_id
    )
    if errors_info:
        logger.error("A validation error occurred: '%s'" % errors_info)
        msg = "Invalid input was supplied to the request API: %s" % errors_info
        # TODO, Transform error messages to something more readable
        output_objects.append(
            {"object_type": "error_text", "text": html_escape(msg)}
        )
        return (output_objects, returnvalues.CLIENT_ERROR)

    # 2. determine the specifics of the request being made
    if request_info.request_package not in HANDLERS_BY_PACKAGE:
        error = {"error": "the specified route package handler was not found"}
        return create_api_response(output_objects, 404, **error)

    # 2a. reference all routes that are implemented for the given package
    acceptable_routes = HANDLERS_BY_PACKAGE[request_info.request_package]

    if request_info.route not in acceptable_routes:
        error = {"error": "the specified handler route was not found"}
        return create_api_response(output_objects, 404, **error)
    # 2b. grab the definition for the route being requested
    request_handler = acceptable_routes[request_info.route]

    # 2.1 determine if the specified route defines a handler for normalising
    # the input request_data before it is passed to the request_handler
    # This feature is optional
    acceptable_normalizers = NORMALIZE_INPUTS_BY_PACKAGE.get(
        request_info.request_package, None
    )

    normalize_inputs_fn = None
    if acceptable_normalizers is not None:
        normalize_inputs_fn = acceptable_normalizers.get(
            request_info.route, None
        )

    if normalize_inputs_fn is not None:
        request_info.set_args(normalize_inputs_fn(request_info._request_data))

    # 3. attempt to handle the request
    handler_exit_resp = None
    try:
        handler_exit_resp, handler_data_resp = request_handler(
            configuration, request_info
        )
    except Exception as exc:
        # Currently the request_handler and the underlying validation logic
        # can throw many types of exceptions. For now we capture them all siliently
        # until we can for starters move up the input validation handling.
        logger.error(
            "An exception occured in datainterface while processing the request handler %s"
            % exc
        )

    if handler_exit_resp is None:
        return create_api_response(
            output_objects, 500, error="an unkown error occurred"
        )

    if not isinstance(handler_exit_resp, dict):
        return create_api_response(
            output_objects,
            500,
            error="the route handler returned an incorrect structure type",
        )

    if "status" not in handler_exit_resp:
        return create_api_response(
            output_objects, 500, error="the route handler returned no status"
        )

    if not isinstance(handler_exit_resp["status"], int):
        return create_api_response(
            output_objects,
            500,
            error="the route handler returned an incorrect status type",
        )

    handler_status = handler_exit_resp["status"]
    handler_message = handler_exit_resp.get("message", None)

    # TODO, properly needs to be cleaned up, with a general
    # return message, that can be an error. Should be intepreted depending on the handler_status
    # e.g.
    # result = {"data": handler_data_resp, "message": handler_message}
    # However this requires mig-ux adjustments to work

    result = {"data": handler_data_resp, "error": None}
    if handler_status != 200:
        if handler_message is not None:
            result["error"] = handler_message
        else:
            if "errors_map" not in handler_data_resp:
                result["error"] = (
                    "an error occurred in the route handler but no error message was returned"
                )

    return create_api_response(output_objects, handler_status, **result)
