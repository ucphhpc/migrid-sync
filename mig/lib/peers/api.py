# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# api - API route handlers for peers management
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
#

"""API route handlers for peers management."""

import datetime

from mig.lib.peers.legacy import parse_peers
from mig.lib.peers.notifications import (
    create_peer_invitation_msg,
    create_peers_notify_msg,
)
from mig.lib.peers.parsing import peer_dict_from_fields
from mig.lib.peers.permissions import peers_permit_allowed
from mig.lib.peers.storage import (
    add_accepted_peers_to_client,
    list_peers_accepted,
    list_peers_requested,
    load_peers_pending,
    peer_already_exists,
    remove_accepted_peers_from_client,
    remove_pending_peers_from_client,
    update_peers_accepted,
)
from mig.lib.peers.validation import (
    check_peers_permit,
    validate_input_peer_distinguished_name,
    validate_input_peers_distinguished_names,
    validate_peer_expire_value,
    validate_peer_invite_on_email,
    validate_peers_csvlines,
    validate_peers_import_fields,
    validate_peers_update_fields,
)
from mig.lib.reqinfo import (
    booleanify,
    unconcatify,
    unlistify,
    unlistify_dict,
)
from mig.shared.base import extract_field, fill_user
from mig.shared.notification import send_email


def create_handler_response(
    status, message=None, error=None, **ui_response_kwargs
):
    """
    A helper function to create route handler responses.
    """
    response = {"status": status, "message": message, "error": error}, {
        **ui_response_kwargs
    }
    return response


def handle_GET_peers_summary(configuration, request_info):
    """
    Request handler: GET /peers/summary
    """
    # Check if user is permitted to manage peers
    if not check_peers_permit(configuration, request_info.client_id):
        return create_handler_response(
            403, error="you are not permitted to manage peers"
        )

    accepted_peers = list_peers_accepted(configuration, request_info.client_id)
    requested_peers = list_peers_requested(
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
    # Check if user is permitted to manage peers
    if not check_peers_permit(configuration, request_info.client_id):
        return create_handler_response(
            403, error="you are not permitted to manage peers"
        )

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
    accepted_peers = list_peers_accepted(configuration, request_info.client_id)
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
            error="you tried to send invitations to peers that you don' t have, namely: %s"
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
    # Check if user is permitted to manage peers
    if not check_peers_permit(configuration, request_info.client_id):
        return create_handler_response(
            403, error="you are not permitted to manage peers"
        )

    fields_dict = request_info.args
    input_invite_on_email = fields_dict.pop("invite_on_email")
    accepted_invite, rejected_invite = validate_peer_invite_on_email(
        input_invite_on_email
    )
    if not accepted_invite or rejected_invite:
        return create_handler_response(
            400,
            error="failed to add a new peer, the received invite on email argument was rejected %s"
            % rejected_invite,
        )
    invite_on_email = accepted_invite.get("invite_on_email", False)

    success_map = {}
    errors_map = {}
    created_peers = {}
    for index, peer_fields_dict in enumerate([fields_dict]):
        # input validation
        peer_dict, errors = peer_dict_from_fields(
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

        already_exists, exists_msg = peer_already_exists(
            configuration, request_info.client_id, peer_dict["email"]
        )
        if already_exists:
            success_map[index] = False
            errors_map[index] = {"email": exists_msg}
            continue

        peer_dn = peer_dict["distinguished_name"]
        peer_dict = fill_user(peer_dict)
        pending_peer_entry = {peer_dn: peer_dict}
        saved = add_accepted_peers_to_client(
            configuration, request_info.client_id, pending_peer_entry
        )
        if not saved:
            # Atm, we are only creating one peer here,
            # so we can return early
            return create_handler_response(
                500,
                error="failed to save the submitted peer, please contact support for help with this.",
            )
        created_peers[peer_dn] = peer_dict
        success_map[index] = True

    if errors_map:
        return create_handler_response(400, errors_map=errors_map)

    if not created_peers:
        return create_handler_response(
            500,
            error="no errors were discovered, but the peer was not created, please contact support about this",
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

    # notify admins about the successful additions
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
    # Check if user is permitted to manage peers
    if not check_peers_permit(configuration, request_info.client_id):
        return create_handler_response(
            403, error="you are not permitted to manage peers"
        )

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
    accepted_peers = list_peers_accepted(configuration, request_info.client_id)
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
            error="invalid peers that you don't have were found in your delete request, namely: %s"
            % invalid_client_peers_dn,
        )

    success_map, errors_map = {}, {}
    peers_deleted = {}
    for index, peer_dn in enumerate(valid_client_peers_dn):
        peer_dict = accepted_by_dn[peer_dn]
        if not remove_accepted_peers_from_client(
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
            "failed to send notification to admins about the client %s deleting the following accepted peers successfully %s"
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
    # Check if user is permitted to manage peers
    if not check_peers_permit(configuration, request_info.client_id):
        return create_handler_response(
            403, error="you are not permitted to manage peers"
        )

    peer = request_info.args["peer"]
    accepted, rejected = validate_input_peer_distinguished_name(peer)

    if not accepted or rejected:
        return create_handler_response(
            400,
            error="failed to fetch the accepted with, received an incorrect peer argument %s"
            % rejected,
        )
    peer_dn = accepted["peer"]

    accepted_peers = list_peers_accepted(configuration, request_info.client_id)
    accepted_by_dn = {
        peer["distinguished_name"]: peer for peer in accepted_peers.values()
    }

    if peer_dn not in accepted_by_dn:
        return create_handler_response(404, error="peer not found")
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
    # Check if user is permitted to manage peers
    if not check_peers_permit(configuration, request_info.client_id):
        return create_handler_response(
            403, error="you are not permitted to manage peers"
        )

    args = request_info.args
    # Validate invite on email
    input_invite_on_email = args.pop("invite_on_email")
    accepted_invite, rejected_invite = validate_peer_invite_on_email(
        input_invite_on_email
    )
    if not accepted_invite or rejected_invite:
        return create_handler_response(
            400,
            error="failed to import peer(s), the received invite on email argument was rejected %s"
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
            error="failed to import peer(s), the received import argument(s) was rejected %s"
            % rejected_common,
        )

    # Validate the peers import field
    csvlines = {"csvlines": args.pop("csvlines", [])}
    accepted_csvlines, rejected_csvlines = validate_peers_csvlines(csvlines)
    if not accepted_csvlines or rejected_csvlines:
        return create_handler_response(
            400,
            error="failed to import peer(s), the received peers csvlines argument(s) was rejected %s"
            % rejected_csvlines,
        )

    peers = accepted_csvlines.get("csvlines", [])
    parsed_peers, parse_err = parse_peers(configuration, peers, "csvform")
    if parse_err:
        return create_handler_response(
            400,
            error="failed to import the submitted peers, err %s" % parse_err,
        )

    if not parsed_peers:
        return create_handler_response(
            400,
            error="failed to find any peers in the submitted peers csvlines",
        )

    success_map, errors_map = {}, {}
    created_peers = {}
    for index, peer_fields_dict in enumerate(parsed_peers):
        # Assign global key-value args
        peer_fields_dict["label"] = accepted_common["label"]
        peer_fields_dict["kind"] = accepted_common["kind"]
        peer_fields_dict["expire"] = accepted_common["expire"]

        # input validation
        peer_dict, errors = peer_dict_from_fields(
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

        already_exists, exists_msg = peer_already_exists(
            configuration, request_info.client_id, peer_dict["email"]
        )
        if already_exists:
            success_map[index] = False
            errors_map[index] = {"email": exists_msg}
            continue

        peer_dn = peer_dict["distinguished_name"]
        peer_dict = fill_user(peer_dict)
        pending_peer_entry = {peer_dn: peer_dict}
        saved = add_accepted_peers_to_client(
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
            error="no errors were discovered, but the peer was not created, please contact support about this",
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

    # notify admins about the successful import
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

    expire = unlistify(args.pop("expire", None))
    args["expire"] = {"expire": expire}

    label = unlistify(args.pop("label", None))
    args["label"] = {"label": label}

    kind = unlistify(args.pop("kind", None))
    args["kind"] = {"kind": kind}
    return args


def handle_POST_peers_accepted_update(configuration, request_info):
    """
    Request Handler: POST /peers/accepted/update
    """
    # Check if user is permitted to manage peers
    if not check_peers_permit(configuration, request_info.client_id):
        return create_handler_response(
            403, error="you are not permitted to manage peers"
        )

    args = request_info.args

    input_peer = args["peer"]
    accepted, rejected = validate_input_peer_distinguished_name(input_peer)
    if rejected:
        return create_handler_response(
            400,
            error="failed to update the peer, received an incorrect peer argument %s"
            % rejected,
        )
    peer_dn = accepted["peer"]

    # Validate the global peers args
    common_update_args = {}
    for input_arg in ["label", "kind", "expire"]:
        value = args.get(input_arg, None)
        if value is not None:
            common_update_args[input_arg] = value

    accepted_common, rejected_common = validate_peers_update_fields(
        common_update_args
    )
    if not accepted_common or rejected_common:
        return create_handler_response(
            400,
            error="failed to update peer, the received update argument(s) was rejected %s"
            % rejected_common,
        )

    label = accepted_common["label"]
    kind = accepted_common["kind"]
    expire = accepted_common["expire"]

    if expire is not None:
        # validate expire range (min/max days)
        valid_expire, expire_message = validate_peer_expire_value(expire)
        if not valid_expire:
            return create_handler_response(
                400,
                error="an incorrect End Date value was received.",
                errors_map={"0": {"expire": expire_message}},
            )

    accepted_peers = list_peers_accepted(configuration, request_info.client_id)
    accepted_by_dn = {
        peer["distinguished_name"]: peer for peer in accepted_peers.values()
    }
    if peer_dn not in accepted_by_dn:
        return create_handler_response(
            404, error="you don't have an accepted peer with those details"
        )

    # Update the underlying peer
    update_peer_dict = {peer_dn: {}}
    if label is not None:
        update_peer_dict[peer_dn]["label"] = label
    if kind is not None:
        update_peer_dict[peer_dn]["kind"] = kind
    if expire is not None:
        update_peer_dict[peer_dn]["expire"] = expire

    if not update_peers_accepted(
        configuration, request_info.client_id, update_peer_dict
    ):
        return create_handler_response(
            400, error="failed to update the accepted peer %s" % peer_dn
        )

    updated_peers = list_peers_accepted(configuration, request_info.client_id)

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
            "failed to send notification to admins about the client %s updating the following accepted peers successfully %s"
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
    # Check if user is permitted to manage peers
    if not check_peers_permit(configuration, request_info.client_id):
        return create_handler_response(
            403, error="you are not permitted to manage peers"
        )

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
    requested_peers = list_peers_requested(
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
            error="invalid peers that you don't have were found in your delete request, namely: %s"
            % invalid_client_peers_dn,
        )

    success_map, errors_map = {}, {}
    peers_deleted = {}

    # Client current pending peers
    current_requested_peers = dict(
        load_peers_pending(configuration, request_info.client_id)
    )
    for index, peer_dn in enumerate(valid_client_peers_dn):
        peer_dict = current_requested_peers.get(peer_dn, None)
        # Remove the client pending peer
        if not remove_pending_peers_from_client(
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
            "failed to send notification to admins about the client %s deleting the following requested peers successfully %s"
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
    # Check if user is permitted to manage peers
    if not check_peers_permit(configuration, request_info.client_id):
        return create_handler_response(
            403, error="you are not permitted to manage peers"
        )

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
    existing_requested_peers = load_peers_pending(
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
    # In the future when an opportune moment comes we likely want
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
    if not add_accepted_peers_to_client(
        configuration, request_info.client_id, prepared_to_accept_peers
    ):
        return create_handler_response(
            400,
            error="failed to accepted peers",
            errors_map=[
                {index: False} for index, peer_dn in enumerate(to_accept_peers)
            ],
        )

    # If accepted successfully we can remove the pending peers
    if not remove_pending_peers_from_client(
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

    # notify admins about the successful additions
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
