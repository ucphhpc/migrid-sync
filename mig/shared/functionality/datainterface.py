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

Dynamic web applications are usually structured around making individual
requests to a series of routes to request data or operations. This module
carefully provides a bridge allowing a series of routes to be exposed by MiG.

The primary constraints are an inability to make direct use of URL paths and
the only usable submission medium for structured data being a POST. We define
a json payload which encodes the route information. This is normalized upon an
incoming request and the corresponding route handler triggered with a simple
dictionary of args. This resembles flask or FastAPI in the Python world.

Note the above design takes some cues from the jsoninterface module but unlike
it, which is very specific to workflows and was not designed for extensibility,
the ability to easily extend the routes made available is a key feature here.
"""

from __future__ import absolute_import

import cgi
import datetime
import json
import os
import sys
from io import BytesIO

from mig.lib.peers import api as peers_api
from mig.lib.reqinfo import (
    booleanify,
    coalesce_request,
    unconcatify,
    unlistify,
    unlistify_dict,
)
from mig.shared import accountreq, returnvalues
from mig.shared.base import (
    distinguished_name_to_user,
    extract_field,
    fill_user,
    string_snippet,
)
from mig.shared.defaults import (
    CSRF_WARN,
    keyword_auto,
    peers_expire_max_days,
    peers_expire_min_days,
    peers_fields,
)
from mig.shared.handlers import check_enable_csrf, get_csrf_limit
from mig.shared.init import (
    find_entry,
    initialize_main_variables,
    make_start_entry,
)
from mig.shared.notification import send_email
from mig.shared.pwcrypto import make_csrf_token
from mig.shared.safeinput import (
    REJECT_UNSET,
    html_escape,
    valid_boolean,
    valid_date,
    valid_distinguished_name,
    valid_peer_expire_optional,
    valid_peer_kind,
    valid_peer_label,
    valid_peers_csvlines,
    validated_input,
)
from mig.shared.scriptinput import fieldstorage_to_dict
from mig.shared.url import urlencode


def _validate_csrf_token(configuration, request_info, environ):
    """
    Validates that the csrf token in the request matches the expected token.
    """
    _logger = configuration.logger

    if not check_enable_csrf(
        configuration, request_info.request_data, environ=environ
    ):
        return True

    # Extract token from request data or header
    if request_info.csrf_token is None:
        _logger.warning(
            "No CSRF token provided for request route: %s by: %s"
            % (request_info.full_route, request_info.client_email)
        )
        return False

    # Generate expected token
    limit = get_csrf_limit(configuration, environ=environ)
    expected_token = make_csrf_token(
        configuration,
        request_info.method,
        request_info.full_route,
        request_info.client_id,
        limit=limit,
    )

    # Compare tokens (use string_snippet for logging to avoid exposing full tokens)
    if request_info.csrf_token != expected_token:
        msg = "CSRF check failed in datainterface: %s vs %s" % (
            string_snippet(request_info.csrf_token),
            string_snippet(expected_token),
        )
        if configuration.site_csrf_protection != CSRF_WARN:
            _logger.error(msg)
            return False
        else:
            _logger.warning(msg)
            return True
    return True


def _state_change_request(environ, request_method):
    """Returns True if the request is a state change request, False otherwise"""
    state_change_requests = ["POST", "PUT", "PATCH", "DELETE"]
    if (
        environ["REQUEST_METHOD"].upper() in state_change_requests
        and request_method.upper() in state_change_requests
    ):
        return True
    return False


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


HANDLERS_BY_PACKAGE = {}
HANDLERS_BY_PACKAGE.update(peers_api.HANDLERS_BY_PACKAGE)

NORMALIZE_INPUTS_BY_PACKAGE = {}
NORMALIZE_INPUTS_BY_PACKAGE.update(peers_api.NORMALIZE_INPUTS_BY_PACKAGE)


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

    # Set the response as containing JSON
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
        logger.error(
            "A validation error occurred on the general structure of the datainterface API request: '%s'"
            % errors_info
        )
        msg = (
            "The general request structure supplied to the data API was invalid or had illegal inputs, failed with the error: %s"
            % errors_info
        )
        output_objects.append(
            {"object_type": "error_text", "text": html_escape(msg)}
        )
        return (output_objects, returnvalues.CLIENT_ERROR)

    # 1a. validate the CSRF token if it is present for state change requests
    if _state_change_request(environ, request_info.method):
        if not _validate_csrf_token(configuration, request_info, environ):
            error = {"error": "the supplied CSRF token was invalid"}
            return create_api_response(output_objects, 403, **error)

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
        # can throw many types of exceptions. For now we capture them all silently
        # until we can for starters move up the input validation handling.
        logger.error(
            "An exception occured in datainterface while processing the request handler %s"
            % exc
        )

    if handler_exit_resp is None:
        return create_api_response(
            output_objects, 500, error="an unknown error occurred"
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
    handler_error_msg = handler_exit_resp.get("error", None)

    # TODO, properly needs to be cleaned up, with a general
    # return message, that can be an error. Should be interpreted depending on the handler_status
    # e.g.
    # handler_message = handler_exit_resp.get("message", None)
    # result = {"data": handler_data_resp, "message": handler_message}
    # However this requires mig-ux adjustments to work

    result = {"data": handler_data_resp, "error": None}
    if handler_status != 200:
        if handler_error_msg is not None:
            result["error"] = handler_error_msg
        else:
            if "errors_map" not in handler_data_resp:
                result["error"] = (
                    "an error occurred in the route handler but no error message was returned"
                )

    return create_api_response(output_objects, handler_status, **result)
