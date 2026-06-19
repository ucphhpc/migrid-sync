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

# This is intended as a more generic interface than workflowsjsoninterface.py
# and jobsjsoninterface.py, especially as we're now adding a third
# reportjsoninterface.py. It may need to be overhauled or expanded to be a
# truly generic json interface and is currently only suitable for the various
# workflow interactions

"""
datainterface is a functionality module intended to expose routes consuming
and returning data structures within constraints of the usually page-centric
MiGrid request/response model.

Dynamic web applications are usually structured such that they inidividual
requests to a series of routes to request data or operations. This module
carefully provides a bridge allowing a series of routes to be exposed by MiG.

The primary constraints are an inability to make direct use of URL paths and
the only usable submission medium for structured data being a POST. We define
a json payload which encodes the route information. This is decoded upon an
incomng request and the corresponding route handler triggered. In this way
the result resembles express in the node world or flask in the Pythoen world.

Note that the above design does take some cues have been takn from the
jsoninterface module but unlike it, which is very specfied to workflows and
was not desgined to be extensible, the ability to easily extend the available
series of routes is a key feature here.
"""

from __future__ import absolute_import

import cgi
import importlib
from io import BytesIO
import json
import os
import re
import sys

from mig.shared import returnvalues

from mig.lib.reqinfo import coalesce_request, booleanify, \
    unconcatify, unlistify_dict
import mig.shared.accountreq as accountreq
from mig.shared.base import distinguished_name_to_user
import mig.shared.fileio as fileio
from mig.shared.init import initialize_main_variables, make_start_entry, \
    find_entry
from mig.shared.functionality.peersaction import process_peer_action
import mig.shared.returnvalues as returnvalues
from mig.shared.safeinput import REJECT_UNSET, html_escape, \
    valid_request_operation, valid_request_type
from mig.shared.scriptinput import fieldstorage_to_dict


_STATUS_UNSET = object()


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
    user_arguments_dict['output_format'] = ['json']
    user_arguments_dict.pop('__DELAYED_INPUT__', None)
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id,
                                  configuration=configuration,
                                  op_title=False,
                                  op_header=False,
                                  op_menu=False)

    # Now ensure output format above is applied by the WSGI wrappers
    start_entry = find_entry(output_objects, 'start')
    start_entry['override_format'] = True

    return _main(configuration, logger, environ, op_name=op_name,
                 output_objects=output_objects, client_id=client_id,
                 user_arguments_dict=user_arguments_dict)


def handle_GET_peers_summary(configuration, request_info):
    """
    Request handler: GET /peers/summary
    """

    accepted_peers = accountreq.list_peers_accepted(configuration, request_info.client_id)
    requested_peers = accountreq.list_peers_requested(configuration, request_info.client_id)

    return 200, {
        'accepted_count': len(accepted_peers),
        'requested_count': len(requested_peers),
    }


def convert_POST_peers_new(request_data):
    """
    Data conversion: POST /peers/new
    """
    args = unlistify_dict(request_data)
    args['invite_on_email'] = booleanify(args.get('invite_on_email', 'false'))
    return args


def handle_POST_peers_new(configuration, request_info):
    """
    Request handler: POST /peers/new
    """

    fields_dict = request_info.args
    invite_on_email = fields_dict.pop('invite_on_email')

    success_map = {}
    errors_map = {}
    for index, peer_fields_dict in enumerate([fields_dict]):
        peer_dict, errors = accountreq.peer_dict_from_fields(peer_fields_dict)
        if errors:
            success_map[index] = False
            errors_map[index] = errors
            continue

        # comment field must contain the requesting peer
        peer_dict["comment"] = request_info.client_email

        success, temp_user_file_abs = accountreq.save_account_request(configuration, peer_dict)
        if not success:
            success_map[index] = False
            continue

        req_id = os.path.basename(temp_user_file_abs)
        success, _ = accountreq.peer_account_req(req_id, configuration, request_info.client_id,
                                                    admin_copy=False,
                                                    include_auto_email=False)
        if not success:
            success_map[index] = False
            continue

        success_map[index] = True

    if errors_map:
        status = 400
    else:
        status = 200
    return status, {
        'success_map': success_map,
        'errors_map': errors_map,
    }


def handle_DELETE_peers_accepted(configuration, request_info):
    """
    Request handler: DELETE /peers/accepted
    """

    peers = request_info.arg_value('peers', list)

    success_map = {}

    for index, peer_dn in enumerate(peers):
        peer_user = distinguished_name_to_user(peer_dn)

        name_to_user_failure = len(peer_user) == 1 and 'distinguished_name' in peer_user

        success_map[index] = not name_to_user_failure

    if any((not success for success in success_map.values())):
        status = 400
    else:
        status = 200
        process_peer_action(
            configuration, [], request_info.client_id, peers, 'remove', 'userid',
            updates={})

    return 200, { 'success_map': success_map }


def convert_POST_peers_accepted_import(request_data):
    """
    Data conversion: POST /peers/accepted/import
    """
    args = unlistify_dict(request_data)
    args['csvlines'] = unconcatify(args.pop('csvtext', ''), '\n')
    return args


def handle_POST_peers_accepted_import(configuration, request_info):
    """
    Request handler: DELETE /peers/accepted/import
    """

    args = request_info.args
    updates = {
        'kind': args.get('kind', ''),
        'label': args.get('label', ''),
        'raw_expire': args.get('expire', ''),
    }
    _, returnvalue = process_peer_action(configuration, [], request_info.client_id, args['csvlines'], 'import', 'csvform', updates, do_invite=True)

    if returnvalue == returnvalues.OK:
        status = 200
    else:
        status = 400
    return status, {}


def handle_DELETE_peers_requested(configuration, request_info):
    """
    Request handler: DELETE /peers/requested
    """

    peers = request_info.arg_value('peers', list)
    user_pending_reqid_by_dn = dict(accountreq.list_account_reqs_pairs(configuration))

    success_map = {}

    for index, peer_dn in enumerate(peers):
        try:
            peer_reqid = user_pending_reqid_by_dn[peer_dn]
        except KeyError:
            success_map[index] = False
            continue

        _, returnvalue = process_peer_action(configuration, [], request_info.client_id, [peer_dn], 'reject', 'userid', {})
        success = returnvalue == returnvalues.OK
        success_map[index] = success

        if not success:
            continue

        # peersaction "reject" does not the pending user file, do so
        pending_user_file_path = os.path.join(configuration.user_pending, peer_reqid)
        fileio.delete_file(pending_user_file_path, configuration.logger)

    return 200, { 'success_map': success_map }


def handle_POST_peers_requested_accept(configuration, request_info):
    """
    Request handler: POST /peers/requested/accept
    """

    peers = request_info.arg_value('peers', list)
    user_pending_reqid_by_dn = dict(accountreq.list_account_reqs_pairs(configuration))

    success_map = {}

    for index, peer_dn in enumerate(peers):
        try:
            peer_reqid = user_pending_reqid_by_dn[peer_dn]
        except KeyError:
            success_map[index] = False
            continue

        _, returnvalue = process_peer_action(configuration, [], request_info.client_id, [peer_dn], 'accept', 'userid', {}, auto_expire=True)
        success = returnvalue == returnvalues.OK

        if not success:
            # the peer was not recorded
            success_map[index] = False
            continue

        # peersaction "accept" does not create the user, do so
        # note that this does implicitly remove the pending user file
        success, _ = accountreq.accept_account_req(peer_reqid, configuration, request_info.client_id, admin_copy=False, user_copy=True)

        success_map[index] = success

    return 200, { 'success_map': success_map }


HANDLERS_BY_PACKAGE = {
    "migux.apps.peers": {
        "POST /new": handle_POST_peers_new,
        "GET /summary": handle_GET_peers_summary,
        "POST /accepted/delete": handle_DELETE_peers_accepted,
        "POST /accepted/import": handle_POST_peers_accepted_import,
        "POST /requested/accept": handle_POST_peers_requested_accept,
        "POST /requested/delete": handle_DELETE_peers_requested,
    }
}

NORMALIZE_INPUTS_BY_PACKAGE = {
    "migux.apps.peers": {
        "POST /new": convert_POST_peers_new,
        "POST /accepted/import": convert_POST_peers_accepted_import,
    }
}


def _main(configuration, logger, environ, op_name='', output_objects=None, client_id=None,
          user_arguments_dict=None):

    # Create new output_objects list with start entry if None was supplied
    if output_objects is None:
        output_objects = [make_start_entry()]

    # Set the response as containining JSON
    output_objects[0]['headers'].append(('Content-Type', 'application/json'))

    if 'wsgi.version' in environ:
        raw_data = environ['wsgi.input'].read()
    else:
        raw_data = sys.stdin.read()

    requested_content_type = environ.get('CONTENT_TYPE', 'multipart/form-data')
    requested_input_format = requested_content_type.split('/')[1]
    request_data = None

    if requested_input_format == 'json':
        try:
            request_data = json.loads(raw_data)
        except ValueError:
            msg = "An invalid format was supplied to: '%s', requires a JSON " \
                "compatible format" % op_name
            logger.error(msg)
            output_objects.append({'object_type': 'error_text',
                                'text': html_escape(msg)})
            return (output_objects, returnvalues.CLIENT_ERROR)
    elif raw_data == b'' and user_arguments_dict:
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
            raw_data = bytes(raw_data, 'utf8')
        fieldstorage = cgi.FieldStorage(fp=BytesIO(raw_data),
                                         environ=environ)
        request_data = fieldstorage_to_dict(fieldstorage)

    # 1. validate data required for a basic JSON request

    errors_info, request_info = coalesce_request(request_data, client_id=client_id)
    if errors_info:
        logger.error("A validation error occurred: '%s'" % errors_info)
        msg = "Invalid input was supplied to the request API: %s" % errors_info
        # TODO, Transform error messages to something more readable
        output_objects.append({'object_type': 'error_text',
                               'text': html_escape(msg)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # 2. determine the specifics of the request being made

    status = _STATUS_UNSET
    result = None

    try:
        # 2a. reference all routes that are implemented for the given package
        acceptable_routes = HANDLERS_BY_PACKAGE[request_info.request_package]
        # 2b. grab the definition for the route being requested
        request_handler = acceptable_routes[request_info.route]
    except KeyError:
        status = 404
        result = {
            'error': 'no such route',
        }

    try:
        acceptable_normalizers = NORMALIZE_INPUTS_BY_PACKAGE[request_info.request_package]
        normalize_inputs_fn = acceptable_normalizers[request_info.route]
        request_info.set_args(normalize_inputs_fn(request_info._request_data))
    except KeyError:
        pass

    # 3. attempt to handle the request

    if status is _STATUS_UNSET:
        try:
            status, data = request_handler(configuration, request_info)

            result = {
                'data': data,
                'error': None
            }
        except Exception as any_exc:
            pass

    if status is _STATUS_UNSET:
        status = 500
    if not result:
        result = {
            'error': 'an unknown error occurred'
        }

    output_objects.append({
        'object_type': 'objects',
        'objects': {
            **result,
            'status': status,
        }
    })

    return (output_objects, returnvalues.OK)
