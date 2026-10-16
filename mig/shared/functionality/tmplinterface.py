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
incoming request and the corresponding route handler triggered. The handler
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

from mig.lib.peers import templates as peers_templates
from mig.lib.reqinfo import (
    coalesce_request,
    uncommaify,
    unlistify,
    unlistify_dict,
)
from mig.shared import accountreq, returnvalues
from mig.shared.functionality.datainterface import create_handler_response
from mig.shared.init import initialize_main_variables, make_start_entry
from mig.shared.pwcrypto import make_csrf_token
from mig.shared.safeinput import (
    html_escape,
    valid_csrf_request_field,
    valid_peer_expire_optional,
    valid_peer_kind,
    valid_peer_query,
    valid_template_field,
    validated_input,
)
from mig.shared.scriptinput import fieldstorage_to_dict


def create_text_response(
    output_objects,
    output_text,
    object_type="objects",
    output_return_code=returnvalues.OK,
):
    """
    A helper function for creating output_object responses.
    """
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


TMPL_DATA_HANDLERS = {**peers_templates.TMPL_DATA_HANDLERS}


NORMALIZE_INPUTS_BY_PACKAGE = {**peers_templates.NORMALIZE_INPUTS_BY_PACKAGE}


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

    # Set the response as containing HTML
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
        logger.error(
            "A validation error occurred on the general structure of the template API request: '%s'"
            % errors_info
        )
        msg = (
            "The general request structure supplied to the request API was invalid or had illegal inputs, failed with the error: %s"
            % errors_info
        )
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

    # Validate that the specified package is supported
    if request_info.request_package not in TMPL_DATA_HANDLERS:
        return create_text_response(
            output_objects,
            "the specified route package handler was not found",
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
        # can throw many types of exceptions. For now we capture them all silently
        # until we can for starters move up the input validation handling.
        logger.error(
            "An exception occured in tmplinterface while processing the template data handler %s"
            % exc
        )

    if template_data_exit_resp is None:
        return create_text_response(
            output_objects,
            "an unknown error occurred during data preparation for the template handler",
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
        if template_handler_message is None:
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
