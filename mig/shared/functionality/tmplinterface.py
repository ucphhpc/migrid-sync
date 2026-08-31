#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# tmplinterface.py - template rendering endpoint
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
tmplinterface is a functionality module intended to expose routes which
return HTML fragments generated via the rendering of templates.

This module exists to support dynamic web applications that seek to load data
in a piecemeal fashion as successive portions of the interface are used. Each
route corresponds to some portion of data needed for a particular interaction,
and thus the need for a custom functionality file arises to support defining a
series of routes that can specify which template they must respond with.

The primary constraints are an inability to make direct use of URL paths and
the only usable submission medium for structured data being a POST. We define
a json payload which encodes the route information. This is decoded upon an
incomng request and the corresponding route handler triggered. The handler
must respond with HTML fragments as opposed to a complete page.
"""

from __future__ import absolute_import

import cgi
import importlib
import json
import os
import re
import sys
from datetime import date, datetime
from io import BytesIO

from mig.lib.reqinfo import (
    coalesce_request,
    uncommaify,
    unlistify,
    unlistify_dict,
)
from mig.shared import accountreq, returnvalues
from mig.shared.functionality.datainterface import create_handler_response
from mig.shared.init import initialize_main_variables, make_start_entry
from mig.shared.safeinput import (
    html_escape,
    valid_peer_expire_optional,
    valid_peer_kind,
    valid_peer_query,
    valid_template_field,
    validated_input,
)
from mig.shared.scriptinput import fieldstorage_to_dict

# supporting logic


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
        pattern = re.compile(".*%s.*" % (search_value,))
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


def create_text_response(
    output_objects,
    output_text,
    object_type="objects",
    output_return_code=returnvalues.OK,
):
    output_objects.append({"object_type": object_type, "text": output_text})
    return (output_objects, output_return_code)


# main logic


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
    user_arguments_dict["output_format"] = ["html"]
    user_arguments_dict.pop("__DELAYED_INPUT__", None)
    configuration, logger, output_objects, op_name = initialize_main_variables(
        client_id,
        op_title=False,
        op_header=False,
        op_menu=False,
        configuration=configuration,
    )

    return _main(
        configuration,
        logger,
        environ,
        op_name=op_name,
        output_objects=output_objects,
        client_id=client_id,
        user_arguments_dict=user_arguments_dict,
    )


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

    listing = accountreq.list_peers_accepted(
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

    listing = accountreq.list_peers_requested(
        configuration, request_info.client_id
    )

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


def create_tmpl_response(
    output_objects,
    template_group,
    template_name,
    template_args,
    object_type="template",
):
    """
    A helper function that creates the final
    tmplinterface return structure to the output_objects.
    """
    output_objects.append(
        {
            "object_type": object_type,
            "template_group": template_group,
            "template_name": template_name,
            "template_args": template_args,
        }
    )
    return (output_objects, returnvalues.OK)


TMPL_DATA_HANDLERS = {
    "migux.apps.peers": {
        "GET /accepted": prepare_GET_migux_apps_peers_accepted,
        "GET /requested": prepare_GET_migux_apps_peers_requested,
    }
}


NORMALIZE_INPUTS_BY_PACKAGE = {
    "migux.apps.peers": {
        "GET /accepted": convert_peers_listing_request_data,
        "GET /requested": convert_peers_listing_request_data,
    }
}


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

    # Set the response as containining HTML
    output_objects[0]["headers"].append(("Content-Type", "text/html"))

    if "wsgi.version" in environ:
        raw_data = environ["wsgi.input"].read()
    else:
        raw_data = sys.stdin.read()

    # Input data
    request_content_type = environ.get("CONTENT_TYPE", "multipart/form-data")
    request_input_format = request_content_type.split("/")[1]
    request_data = None

    if request_input_format == "json":
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

    # Validate that the specified package is enabled
    enabled_templates = configuration.division("TEMPLATES")
    enabled_template_packages = enabled_templates.base_packages

    # Extract the toplevel requested package name which is specified as an enabled
    # [TEMPLATES]["base_packages"]
    # TODO, validate per full module import
    parent_requested_package = request_info.request_package.split(".")[0]
    if parent_requested_package not in enabled_template_packages:
        return create_text_response(
            output_objects,
            "the specified template is not supported or enabled.",
            object_type="error_text",
            output_return_code=returnvalues.CLIENT_ERROR,
        )
    try:
        package_module = importlib.import_module(request_info.request_package)
    except (ImportError, ModuleNotFoundError) as exc:
        logger.error(
            "failed to import the client specified tmplinterface request_package %s "
            % exc
        )
        return create_text_response(
            output_objects,
            "the specified template package could not be imported",
            object_type="error_text",
            output_return_code=returnvalues.CLIENT_ERROR,
        )

    if not hasattr(package_module, "TEMPLATE_ROUTES"):
        return create_text_response(
            output_objects,
            "the specified template package does not declare the expected TEMPLATE_ROUTES",
            object_type="error_text",
            output_return_code=returnvalues.CLIENT_ERROR,
        )

    if request_info.route not in package_module.TEMPLATE_ROUTES:
        return create_text_response(
            output_objects,
            "the specified template route is not supported by the selected template package",
            object_type="error_text",
            output_return_code=returnvalues.CLIENT_ERROR,
        )

    responder = package_module.TEMPLATE_ROUTES[request_info.route]
    if "generate_args" not in responder:
        return create_text_response(
            output_objects,
            "the required 'generate_args' key was not found in the template package routes",
            object_type="error_text",
            output_return_code=returnvalues.CLIENT_ERROR,
        )

    # 2a. reference all routes that are implemented for the given package
    if request_info.request_package not in TMPL_DATA_HANDLERS:
        return create_text_response(
            output_objects,
            "the specified route package handler was not found",
            object_type="error_text",
            output_return_code=returnvalues.CLIENT_ERROR,
        )

    # 2a. reference all routes that are implemented for the given package
    acceptable_routes = TMPL_DATA_HANDLERS[request_info.request_package]
    if request_info.route not in acceptable_routes:
        return create_text_response(
            output_objects,
            "the specified template data handling route was not found",
            object_type="error_text",
            output_return_code=returnvalues.CLIENT_ERROR,
        )

    template_data_handler = acceptable_routes[request_info.route]

    # 2.1 determine if the specified route defines a handler for normalising
    # the input request_data before it is passed to the template_data_handler
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
    template_data_exit_resp = None
    try:
        template_data_exit_resp, template_data_resp = template_data_handler(
            configuration, request_info
        )
    except Exception as exc:
        # Currently the template_data_handler and the underlying validation logic
        # can throw many types of exceptions. For now we capture them all siliently
        # until we can for starters move up the input validation handling.
        logger.error(
            "An exception occured in tmplinterface while processing the template data handler %s"
            % exc
        )

    if template_data_exit_resp is None:
        return create_text_response(
            output_objects,
            "an unknown error occurred during data preparation",
            object_type="error_text",
            output_return_code=returnvalues.SYSTEM_ERROR,
        )

    if not isinstance(template_data_exit_resp, dict):
        return create_text_response(
            output_objects,
            "the route template handler returned an incorrect structure type",
            object_type="error_text",
            output_return_code=returnvalues.ERROR,
        )

    if "status" not in template_data_exit_resp:
        return create_text_response(
            output_objects,
            "the route template handler returned no status",
            object_type="error_text",
            output_return_code=returnvalues.ERROR,
        )

    if not isinstance(template_data_exit_resp["status"], int):
        return create_text_response(
            output_objects,
            "the route template handler returned an incorrect status type",
            object_type="error_text",
            output_return_code=returnvalues.ERROR,
        )

    template_handler_status = template_data_exit_resp["status"]
    template_handler_message = template_data_exit_resp.get("message", None)

    if template_handler_status != 200:
        if template_handler_message is not None:
            template_handler_message = (
                "an unknown error occurred from the template handler"
            )
        return create_text_response(
            output_objects,
            template_handler_message,
            object_type="error_text",
            output_return_code=returnvalues.ERROR,
        )

    if "data" not in template_data_resp:
        return create_text_response(
            output_objects,
            "failed to find the required 'data' key in the template data response",
            object_type="error_text",
            output_return_code=returnvalues.ERROR,
        )

    template_data = template_data_resp["data"]
    # We pass the template_data_resp to the client ux library here, which
    # is responsible for accepting and rendering it to the client
    # so the request itself does not return the content.
    # The template_data is required to be iterable and support being called
    # with iter(template_data)
    try:
        iter(template_data)
    except TypeError:
        return create_text_response(
            output_objects,
            "the template handler returned a datastructure that cannot be iterated",
            object_type="error_text",
            output_return_code=returnvalues.ERROR,
        )

    render_info = responder["generate_args"](request_info, template_data)
    return create_tmpl_response(
        output_objects,
        request_info.request_package,
        render_info["template_name"],
        render_info["template_args"],
    )
