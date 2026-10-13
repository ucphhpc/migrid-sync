# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# templates - template data handlers for peers
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

"""Template data handlers for peers management."""

import re
from datetime import date, datetime

from mig.lib.peers.api import create_handler_response
from mig.lib.peers.storage import list_peers_accepted, list_peers_requested
from mig.lib.reqinfo import (
    uncommaify,
    unlistify,
    unlistify_dict,
)
from mig.shared.pwcrypto import make_csrf_token
from mig.shared.safeinput import (
    valid_csrf_request_field,
    valid_peer_expire_optional,
    valid_peer_kind,
    valid_peer_query,
    valid_template_field,
    validated_input,
)


def _coerce_date(value):
    if isinstance(value, date):
        return value
    elif isinstance(value, datetime):
        return value.date()
    elif isinstance(value, str):
        return datetime.fromisoformat(value).date()
    elif isinstance(value, int):
        return datetime.fromtimestamp(value).date()
    raise ValueError("value does not look like a datetime")


def _compile_condition_value(search_value):
    """
    Compile a pattern that can be used to test for a particular search value.
    """

    if isinstance(search_value, str):
        pattern = re.compile(".*%s.*" % (re.escape(search_value),))
        return lambda value: bool(re.search(pattern, value))
    elif isinstance(search_value, date):
        return lambda value: _coerce_date(value) >= search_value
    raise NotImplementedError("cannot filter on unsupported value of type")


def _compile_condition(condition):
    """
    Returns a dictionary with the passed key identifier unchanged
    and the result of calling _compile_condition_value on the value.
    """
    return {k: _compile_condition_value(v) for k, v in condition.items()}


def _search_dicts_matching(objects, conditions):
    """
    Search dictionaries within a list for those with keys whose values
    match those supplied within a filter dictionary.

    This function operates on a first-match basis - that is, the first value
    that satisfies the condition for its corresponding key will result in the
    objects being selected.
    """

    if not conditions:
        return objects

    # compile each search term into regex once up-front to
    # allow the loop testing them to have only that concern
    search_filters = [_compile_condition(condition) for condition in conditions]

    hits = []

    # outer loop handling AND
    for obj in objects:
        match = True

        # inner loop handling OR
        for filters_to_or in search_filters:
            if not match:
                break

            if len(filters_to_or) == 1:
                # single condition fast path
                key = next(iter(filters_to_or))
                obj_value = obj.get(key, "")
                condition = filters_to_or[key]
                match = condition(obj_value)
                continue

            for key, condition in filters_to_or.items():
                obj_value = obj.get(key, "")
                match = condition(obj_value)
                if match:
                    break

        if match:
            hits.append(obj)

    return hits


def convert_csrf_tokens_request_data(request_data):
    """
    Convert MiG style wrapped request data to a standard data structure.
    """
    args = unlistify_dict(request_data)
    requests = uncommaify(unlistify(request_data.pop("requests", "")))
    args["requests"] = requests

    # We have to ensure that the expected fields are present
    # as required by the underlying csrf_tokens.html.jinja template
    # in migux is included in the request_info.args list as it is used
    # to extract the csrf tokens to render the template.
    fields = ["tokens", "method", "operation"]
    args["fields"] = fields
    return args


def convert_peers_listing_request_data(request_data):
    """
    Convert MiG style wrapped request data to a standard data structure.
    """

    args = unlistify_dict(request_data)

    query = unlistify(args.pop("query", ""))
    args["query"] = query

    expire = unlistify(args.pop("expire", ""))
    args["expire"] = expire

    kind = unlistify(args.pop("kind", ""))
    args["kind"] = kind

    fields = uncommaify(unlistify(request_data.pop("fields", "")))
    args["fields"] = fields
    return args


def validate_peers_search_inputs(search_args):
    """Validates the input of a peer search

    search_args: {"fields": [], "query": query, "kind": kind, "expire": expire}
    """

    # The query can either be a peer label or an email
    # Therefore we need to check against both kinds.
    signature = {"fields": [""], "query": [""], "kind": [""], "expire": [""]}
    accepted, rejected = validated_input(
        search_args,
        signature,
        type_override={
            "fields": valid_template_field,
            "query": valid_peer_query,
            "kind": valid_peer_kind,
            "expire": valid_peer_expire_optional,
        },
        list_wrap=True,
    )

    return unlistify_dict(accepted), unlistify_dict(rejected)


def prepare_GET_migux_apps_peers_accepted(configuration, request_info):
    """
    Data preparation function for mixux.apps.peers GET /accepted
    """
    accepted_inputs, rejected_inputs = validate_peers_search_inputs(
        request_info.args
    )
    if not accepted_inputs or rejected_inputs:
        return create_handler_response(
            400,
            message="failed to validate the input arguments when listing your accepted peers, error: %s"
            % rejected_inputs,
        )

    listing = list_peers_accepted(
        configuration, request_info.client_id
    ).values()

    return create_handler_response(
        200, data=_peers_listing_filter(listing, accepted_inputs)
    )


def prepare_GET_migux_apps_peers_requested(configuration, request_info):
    """
    Data preparation function for mixux.apps.peers GET /requested
    """

    accepted_inputs, rejected_inputs = validate_peers_search_inputs(
        request_info.args
    )
    if not accepted_inputs or rejected_inputs:
        return create_handler_response(
            400,
            error="failed to validate the input arguments when listing your requsted peers, error: %s"
            % rejected_inputs,
        )

    listing = list_peers_requested(configuration, request_info.client_id)

    # When a peer request is accepted and forwarded from migadmin.py
    # it is inserted into the user's user_settings/client_id/pending_peers file.
    # Here the expire value is set to the maximum time a peer can be valid as an EPOCH timestamp.
    # Therefore we need to transform this into the YYYY-MM-DD format to make it understandable for the user
    # who is going to accept the request.

    transformed_requested_peers = []
    for requested_peer_dict in listing:
        converted_peer_dict = {}
        for key, value in requested_peer_dict.items():
            if key == "expire":
                expire_date = datetime.fromtimestamp(value).date()
                value = expire_date.strftime("%Y-%m-%d")
            converted_peer_dict[key] = value
        transformed_requested_peers.append(converted_peer_dict)

    return create_handler_response(
        200,
        data=_peers_listing_filter(
            transformed_requested_peers, accepted_inputs
        ),
    )


def _peers_listing_filter(objects, request_args):
    """
    Generate filters dictionary for a peers listing request.
    """
    conditions = []

    query = request_args["query"]
    if not (query == "*" or query == ""):
        conditions.append(
            {
                "label": query,
                "email": query,
            }
        )

    expire = request_args["expire"]
    if expire != "":
        conditions.append(
            {
                "expire": datetime.fromisoformat(expire).date(),
            }
        )

    kind = request_args["kind"]
    if kind != "":
        conditions.append(
            {
                "kind": kind,
            }
        )

    return _search_dicts_matching(objects, conditions)


def validate_csrf_requests_input(csrf_args):
    """Validates the input of a peer search

    csrf_args: {"requests": [], "fields": []}
    """

    # The query can either be a peer label or an email
    # Therefore we need to check against both kinds.
    signature = {"requests": [""], "fields": [""]}
    accepted, rejected = validated_input(
        csrf_args,
        signature,
        type_override={
            "requests": valid_csrf_request_field,
            "fields": valid_template_field,
        },
        list_wrap=True,
    )
    # We skip unlisting fields since this is expected to be a list
    return accepted, unlistify_dict(rejected)


def prepare_GET_migux_apps_peers_csrf_tokens(configuration, request_info):
    """
    Data preparation function for mixux.apps.peers GET /csrf_tokens.

    This function is responsible for generating csrf tokens for the specific requests.
    The requests are expected to be a list of strings, that each contains the particular method
    and operation for which a csrf token should be generated.

    An example of the requests parameter could be:
    {
        "requests": ["method=POST&operation=/peers/peer_accept", "method=POST&operation=/peers/peer_reject"]
    }
    """
    # Validate the requests parameter
    accepted, rejected = validate_csrf_requests_input(request_info.args)
    if not accepted or rejected:
        return create_handler_response(
            400,
            error="failed to validate the request for csrf tokens for the specific arguments, error: %s"
            % rejected,
        )

    accepted_requests = accepted["requests"]
    token_errors, tokens = {}, []
    for request_object in accepted_requests:
        if "&" not in request_object:
            token_errors[request_object] = "missing & in csrf token request"
            continue
        request_object_split = request_object.split("&")
        if len(request_object_split) != 2:
            token_errors[request_object] = (
                "in a csrf request, only a single & is valid to deliminate the method and operation"
            )
            continue

        method_obj, operation_obj = (
            request_object_split[0],
            request_object_split[1],
        )

        method_split = method_obj.split("=")
        if len(method_split) != 2:
            token_errors[request_object] = (
                "in a csrf request, only a single method assignment via = is allowed"
            )
            continue
        method = method_split[1]

        operation_split = operation_obj.split("=")
        if len(operation_split) != 2:
            token_errors[request_object] = (
                "in a csrf request, only a single operation assignment via = is allowed"
            )
            continue
        operation = operation_split[1]

        token = make_csrf_token(
            configuration, method, operation, request_info.client_id
        )
        tokens.append(
            {"token": token, "method": method, "operation": operation}
        )

    if token_errors:
        return create_handler_response(
            400,
            error="failed to generate csrf tokens for the following requests: %s"
            % token_errors,
        )

    return create_handler_response(200, data=tokens)


TMPL_DATA_HANDLERS = {
    "migux.apps.peers": {
        "GET /accepted": prepare_GET_migux_apps_peers_accepted,
        "GET /requested": prepare_GET_migux_apps_peers_requested,
        "GET /csrf_tokens": prepare_GET_migux_apps_peers_csrf_tokens,
    }
}


NORMALIZE_INPUTS_BY_PACKAGE = {
    "migux.apps.peers": {
        "GET /accepted": convert_peers_listing_request_data,
        "GET /requested": convert_peers_listing_request_data,
        "GET /csrf_tokens": convert_csrf_tokens_request_data,
    }
}
