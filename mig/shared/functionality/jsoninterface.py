#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# workflowsjsoninterface.py - JSON interface for
# managing workflows via cgisid requests
# Copyright (C) 2019-2020  The MiG Project lead by Brian Vinter
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

"""JSON interface for handling all workflow, job and report interactions."""
from __future__ import absolute_import

import json
import sys

from mig.shared import returnvalues

from mig.shared.base import force_utf8_rec
from mig.shared.handlers import correct_handler
from mig.shared.init import initialize_main_variables
from mig.shared.job import JOB_TYPES, JOB, QUEUE, get_job_with_id
from mig.shared.safeinput import REJECT_UNSET, valid_sid, validated_input, \
    html_escape, valid_request_operation, valid_request_type, \
    valid_request_vgrid, valid_request_attributes, valid_job_id, \
    valid_workflow_pers_id, valid_workflow_name, valid_workflow_input_file, \
    valid_workflow_input_paths, valid_workflow_output, \
    valid_workflow_param_over, valid_workflow_variables, \
    valid_workflow_source, valid_workflow_recipe, valid_workflow_environments
from mig.shared.vgrid import get_vgrid_workflow_jobs, init_vgrid_script_list
from mig.shared.workflows import WORKFLOW_TYPES, PATTERN_GRAPH, WORKFLOW_ANY, \
    WORKFLOW_PATTERN, WORKFLOW_RECIPE, valid_session_id, get_workflow_with, \
    load_workflow_sessions_db, create_workflow, delete_workflow, \
    update_workflow, touch_workflow_sessions_db, search_workflow, \
    WORKFLOW_SEARCH_TYPES, WORKFLOW_REPORT, get_workflow_job_report

CREATE = 'create'
READ = 'read'
UPDATE = 'update'
DELETE = 'delete'

ALL_OPERATIONS = [
    CREATE,
    READ,
    UPDATE,
    DELETE
]

REQUEST_SIGNATURE = {
    'attributes': {},
    'type': REJECT_UNSET,
    'operation': REJECT_UNSET,
    'workflowsessionid': REJECT_UNSET,
    'vgrid': REJECT_UNSET
}

VALID_JOB_SIGNATURE = {
    'vgrid': REJECT_UNSET,
    'job_id': ''
}

VALID_QUEUE_SIGNATURE = {
    'vgrid': REJECT_UNSET
}

VALID_WORKFLOW_PATTERN_SIGNATURE = {
    'vgrid': REJECT_UNSET,
    'persistence_id': '',
    'name': '',
    'input_file': '',
    'input_paths': [],
    'output': {},
    'recipes': [],
    'variables': {},
    'parameterize_over': {}
}

VALID_WORKFLOW_RECIPE_SIGNATURE = {
    'vgrid': REJECT_UNSET,
    'persistence_id': '',
    'name': '',
    'source': '',
    'recipe': {},
    'environments': {}
}

VALID_WORKFLOW_ANY_SIGNATURE = {
    'vgrid': REJECT_UNSET,
    'persistence_id': '',
    'name': '',
    'input_file': '',
    'input_paths': [],
    'output': {},
    'recipes': [],
    'variables': {},
    'parameterize_over': {},
    'source': '',
    'recipe': {},
    'environments': {}
}

VALID_PATTERN_GRAPH_SIGNATURE = {
    'vgrid': REJECT_UNSET
}

VALID_WORKFLOW_REPORT_SIGNATURE = {
    'vgrid': REJECT_UNSET
}

VALID_REQUEST_ATTRIBUTES_SIGNATURE = {
    JOB: VALID_JOB_SIGNATURE,
    QUEUE: VALID_QUEUE_SIGNATURE,
    WORKFLOW_PATTERN: VALID_WORKFLOW_PATTERN_SIGNATURE,
    WORKFLOW_RECIPE: VALID_WORKFLOW_RECIPE_SIGNATURE,
    WORKFLOW_ANY: VALID_WORKFLOW_ANY_SIGNATURE,
    PATTERN_GRAPH: VALID_PATTERN_GRAPH_SIGNATURE,
    WORKFLOW_REPORT: VALID_WORKFLOW_REPORT_SIGNATURE
}

VALID_JOB_TYPE = {
    'job_id': valid_job_id
}

VALID_QUEUE_TYPE = {}

VALID_WORKFLOW_PATTERN_TYPE = {
    'persistence_id': valid_workflow_pers_id,
    'name': valid_workflow_name,
    'input_file': valid_workflow_input_file,
    'input_paths': valid_workflow_input_paths,
    'output': valid_workflow_output,
    'recipes': valid_workflow_recipe,
    'variables': valid_workflow_variables,
    'parameterize_over': valid_workflow_param_over
}

VALID_WORKFLOW_RECIPE_TYPE = {
    'persistence_id': valid_workflow_pers_id,
    'name': valid_workflow_name,
    'source': valid_workflow_source,
    'recipe': valid_workflow_recipe,
    'environments': valid_workflow_environments
}

VALID_WORKFLOW_ANY_TYPE = {
    'persistence_id': valid_workflow_pers_id,
    'name': valid_workflow_name,
    'input_file': valid_workflow_input_file,
    'input_paths': valid_workflow_input_paths,
    'output': valid_workflow_output,
    'recipes': valid_workflow_recipe,
    'variables': valid_workflow_variables,
    'parameterize_over': valid_workflow_param_over,
    'source': valid_workflow_source,
    'recipe': valid_workflow_recipe,
    'environments': valid_workflow_environments
}

VALID_PATTERN_GRAPH_TYPE = {}

VALID_WORKFLOW_REPORT_TYPE = {}

VALID_REQUEST_ATTRIBUTES_TYPE = {
    JOB: VALID_JOB_TYPE,
    QUEUE: VALID_QUEUE_TYPE,
    WORKFLOW_PATTERN: VALID_WORKFLOW_PATTERN_TYPE,
    WORKFLOW_RECIPE: VALID_WORKFLOW_RECIPE_TYPE,
    WORKFLOW_ANY: VALID_WORKFLOW_ANY_TYPE,
    PATTERN_GRAPH: VALID_PATTERN_GRAPH_TYPE,
    WORKFLOW_REPORT: VALID_WORKFLOW_REPORT_TYPE
}

VALID_JOB_VALUE = {
    'job_id': ''
}

VALID_QUEUE_VALUE = {}

VALID_WORKFLOW_PATTERN_VALUE = {
    'persistence_id': '',
    'name': '',
    'input_file': '',
    'input_paths': [],
    'output': {},
    'recipes': [],
    'variables': {},
    'parameterize_over': {}
}

VALID_WORKFLOW_RECIPE_VALUE = {
    'persistence_id': '',
    'name': '',
    'source': '',
    'recipe': {}
}

VALID_WORKFLOW_ANY_VALUE = {
    'persistence_id': '',
    'name': '',
    'input_file': '',
    'input_paths': [],
    'output': {},
    'recipes': [],
    'variables': {},
    'parameterize_over': {},
    'source': '',
    'recipe': {},
}

VALID_PATTERN_GRAPH_VALUE = {}

VALID_WORKFLOW_REPORT_VALUE = {}

VALID_REQUEST_ATTRIBUTES_VALUE = {
    JOB: VALID_JOB_VALUE,
    QUEUE: VALID_QUEUE_VALUE,
    WORKFLOW_PATTERN: VALID_WORKFLOW_PATTERN_VALUE,
    WORKFLOW_RECIPE: VALID_WORKFLOW_RECIPE_VALUE,
    WORKFLOW_ANY: VALID_WORKFLOW_ANY_VALUE,
    PATTERN_GRAPH: VALID_PATTERN_GRAPH_VALUE,
    WORKFLOW_REPORT: VALID_WORKFLOW_REPORT_VALUE
}


def type_value_checker(type_value):
    """
    Validate that the provided job type is allowed. A ValueError
    Exception will be raised if type_value is invalid.
    :param type_value: The type to be checked. Valid types are 'job',
    'queue', 'workflowpattern', 'workflowrecipe' and 'workflowany'
    :return: No return
    """
    valid_types = WORKFLOW_TYPES + WORKFLOW_SEARCH_TYPES + JOB_TYPES

    if type_value not in valid_types:
        raise ValueError("Request type '%s' is not valid. "
                         % html_escape(type_value))


def operation_value_checker(operation_value):
    """
    Validate that the provided job operation is allowed. A ValueError
    Exception will be raised if operation_value is invalid.
    :param operation_value: The operation to be checked. Valid operations are:
    'create', 'read', 'update' and 'delete'.
    :return: No return.
    """
    if operation_value not in ALL_OPERATIONS:
        raise ValueError("Workflow operation '%s' is not valid. "
                         % html_escape(operation_value))


REQUEST_TYPE_MAP = {
    'type': valid_request_type,
    'operation': valid_request_operation,
    'vgrid': valid_request_vgrid,
    'attributes': valid_request_attributes,
    'workflowsessionid': valid_sid
}

REQUEST_VALUE_MAP = {
    'type': type_value_checker,
    'operation': operation_value_checker,
}


def job_read(configuration, user_id, attributes):
    status, response = get_job_with_id(
        configuration, attributes['job_id'], attributes['vgrid'], user_id,
        only_user_jobs=False
    )
    if status:
        return (False, {'object_type': 'error_text', 'text': response})
    return (True, {'object_type': 'job_dict', 'jobs': response})


def queue_read(configuration, user_id, attributes):
    job_list = get_vgrid_workflow_jobs(
        configuration, attributes['vgrid'], json_serializable=True
    )

    job_dict = {}
    for job in job_list:
        job_dict[job['JOB_ID']] = job

    return (True, {'object_type': 'job_dict', 'jobs': job_dict})


def pattern_create(configuration, user_id, attributes):
    status, response = create_workflow(
        configuration, user_id, workflow_type=WORKFLOW_PATTERN, **attributes)
    if not status:
        return (False, {'object_type': 'error_text', 'text': response})
    return (True, {'object_type': 'workflows', 'text': response})


def pattern_read(configuration, user_id, attributes):
    workflows = get_workflow_with(
        configuration, user_id, user_query=True,
        workflow_type=WORKFLOW_PATTERN, **attributes)
    return (True, {'object_type': 'workflows', 'workflows': workflows})


def pattern_update(configuration, user_id, attributes):
    status, response = update_workflow(
        configuration, user_id, workflow_type=WORKFLOW_PATTERN, **attributes)
    if not status:
        return (False, {'object_type': 'error_text', 'text': response})
    return (True, {'object_type': 'workflows', 'text': response})


def pattern_delete(configuration, user_id, attributes):
    status, response = delete_workflow(
        configuration, user_id, workflow_type=WORKFLOW_PATTERN, **attributes)
    if not status:
        return (False, {'object_type': 'error_text', 'text': response})
    return (True, {'object_type': 'workflows', 'text': response})


def recipe_create(configuration, user_id, attributes):
    status, response = create_workflow(
        configuration, user_id, workflow_type=WORKFLOW_RECIPE, **attributes)
    if not status:
        return (False, {'object_type': 'error_text', 'text': response})
    return (True, {'object_type': 'workflows', 'text': response})


def recipe_read(configuration, user_id, attributes):
    workflows = get_workflow_with(
        configuration, user_id, user_query=True,
        workflow_type=WORKFLOW_RECIPE, **attributes)
    return (True, {'object_type': 'workflows', 'workflows': workflows})


def recipe_update(configuration, user_id, attributes):
    status, response = update_workflow(
        configuration, user_id, workflow_type=WORKFLOW_RECIPE, **attributes)
    if not status:
        return (False, {'object_type': 'error_text', 'text': response})
    return (True, {'object_type': 'workflows', 'text': response})


def recipe_delete(configuration, user_id, attributes):
    status, response = delete_workflow(
        configuration, user_id, workflow_type=WORKFLOW_RECIPE, **attributes)
    if not status:
        return (False, {'object_type': 'error_text', 'text': response})
    return (True, {'object_type': 'workflows', 'text': response})


def any_read(configuration, user_id, attributes):
    workflows = get_workflow_with(
        configuration, user_id, user_query=True, workflow_type=WORKFLOW_ANY,
        **attributes)
    return (True, {'object_type': 'workflows', 'workflows': workflows})


def graph_read(configuration, user_id, attributes):
    status, response = search_workflow(
        configuration, user_id, workflow_type=PATTERN_GRAPH, **attributes)
    if not status:
        return (False, {'object_type': 'error_text', 'text': response})
    return (True, {'object_type': 'workflows', 'workflows': response})


def report_read(configuration, user_id, attributes):
    status, response = get_workflow_job_report(
        configuration, attributes['vgrid'])
    if not status:
        return (False, {'object_type': 'error_text', 'text': response})
    return (True, {'object_type': 'workflow_report', 'report': response})


VALID_REQUEST_OPERATIONS = {
    JOB: {
        READ: job_read},
    QUEUE: {
        READ: queue_read},
    WORKFLOW_PATTERN: {
        CREATE: pattern_create,
        READ: pattern_read,
        UPDATE: pattern_update,
        DELETE: pattern_delete},
    WORKFLOW_RECIPE: {
        CREATE: recipe_create,
        READ: recipe_read,
        UPDATE: recipe_update,
        DELETE: recipe_delete},
    WORKFLOW_ANY: {
        READ: any_read},
    PATTERN_GRAPH: {
        READ: graph_read},
    WORKFLOW_REPORT: {
        READ: report_read}
}


def valid_operation_for_type(configuration, operation, request_type):
    if request_type not in VALID_REQUEST_OPERATIONS:
        msg = 'Request type %s has no supported operations.' % request_type
        configuration.logger.warning(msg)
        return (False, msg)

    valid_operations = VALID_REQUEST_OPERATIONS[request_type]
    if operation not in valid_operations:
        msg = 'Operation %s not supported for request type %s. Valid are %s' \
              % (operation, request_type, valid_operations)
        configuration.logger.warning(msg)
        return (False, msg)
    return (True, '')


def valid_attributes_for_type(configuration, attributes, request_type):
    if request_type not in VALID_REQUEST_ATTRIBUTES_SIGNATURE:
        msg = 'Request type %s has no supported attributes.' % request_type
        configuration.logger.warning(msg)
        return (False, msg)

    if request_type not in VALID_REQUEST_ATTRIBUTES_TYPE:
        msg = 'Request type %s has no supported attributes.' % request_type
        configuration.logger.warning(msg)
        return (False, msg)

    signature = VALID_REQUEST_ATTRIBUTES_SIGNATURE[request_type]
    type_map = VALID_REQUEST_ATTRIBUTES_TYPE[request_type]
    accepted, rejected = validated_input(
        attributes, signature, type_override=type_map, list_wrap=True)

    if not accepted or rejected:
        msg = "Invalid input was supplied to the requests API: %s" % rejected
        return (False, msg)

    return (True, '')


def main(client_id, user_arguments_dict):
    """
    Main function used by front end.
    :param client_id: A MiG user.
    :param user_arguments_dict: A JSON message sent to the MiG. This will be
    parsed and if valid, the relevant API handler functions are called to
    generate meaningful output.
    :return: (Tuple (list, Tuple(integer,string))) Returns a tuple with the
    first value being a list of output objects generated by the call. The
    second value is also a tuple used for error code reporting, with the first
    value being an error code and the second being a brief explanation.
    """
    # Ensure that the output format is in JSON
    user_arguments_dict['output_format'] = ['json']
    user_arguments_dict.pop('__DELAYED_INPUT__', None)
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_title=False, op_header=False,
                                  op_menu=False)

    # Add allow Access-Control-Allow-Origin to headers
    # Required to allow Jupyter Widget from localhost to request against the
    # API
    # TODO, possibly restrict allowed origins
    output_objects[0]['headers'].append(('Access-Control-Allow-Origin', '*'))
    output_objects[0]['headers'].append(('Access-Control-Allow-Headers',
                                         'Content-Type'))
    output_objects[0]['headers'].append(('Access-Control-Max-Age', 600))
    output_objects[0]['headers'].append(('Access-Control-Allow-Methods',
                                         'POST, OPTIONS'))
    output_objects[0]['headers'].append(('Content-Type', 'application/json'))

    if not correct_handler('POST'):
        msg = "Interaction from %s not POST request" % client_id
        logger.error(msg)
        output_objects.append({
            'object_type': 'error_text',
            'text': html_escape(msg)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not configuration.site_enable_workflows:
        output_objects.append({
            'object_type': 'error_text',
            'text': 'Workflows are not enabled on this system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Input data
    data = sys.stdin.read()
    try:
        json_data = json.loads(data, object_hook=force_utf8_rec)
    except ValueError:
        msg = "An invalid format was supplied to: '%s', requires a JSON " \
              "compatible format" % op_name
        logger.error(msg)
        output_objects.append({'object_type': 'error_text',
                               'text': html_escape(msg)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # IMPORTANT!! Do not access the json_data input before it has been
    # validated by validated_input. Note attributes entry has not yet been
    # validated, this is done once the type and operation is determined
    accepted, rejected = validated_input(
        json_data, REQUEST_SIGNATURE,
        type_override=REQUEST_TYPE_MAP,
        value_override=REQUEST_VALUE_MAP,
        list_wrap=True)

    if not accepted or rejected:
        logger.error("A validation error occurred: '%s'" % rejected)
        msg = "Invalid input was supplied to the request API: %s" % rejected
        # TODO, Transform error messages to something more readable
        output_objects.append({'object_type': 'error_text',
                               'text': html_escape(msg)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    request_type = accepted.pop('type', [None])[0]
    operation = accepted.pop('operation', None)[0]
    workflow_session_id = accepted.pop('workflowsessionid', None)[0]
    vgrid = accepted.pop('vgrid', None)
    # Note these have not been sufficiently checked, and should not be accessed
    # until the valid_attributes_for_type function has been called on them.
    # This is done later once we have checked the operation and request_type.
    attributes = {}
    for key, value in accepted.items():
        if key in json_data['attributes']:
            attributes[key] = value
    attributes['vgrid'] = vgrid

    if not valid_session_id(configuration, workflow_session_id):
        output_objects.append({'object_type': 'error_text',
                               'text': 'Invalid workflowsessionid'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # workflow_session_id symlink points to the vGrid it gives access to
    workflow_sessions_db = []
    try:
        workflow_sessions_db = load_workflow_sessions_db(configuration)
    except IOError:
        logger.info("Workflow sessions db didn't load, creating new db")
        if not touch_workflow_sessions_db(configuration, force=True):
            output_objects.append(
                {'object_type': 'error_text',
                 'text': "Internal sessions db failure, please contact "
                         "an admin at '%s' to resolve this issue." %
                         configuration.admin_email})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        else:
            # Try reload
            workflow_sessions_db = load_workflow_sessions_db(configuration)

    if workflow_session_id not in workflow_sessions_db:
        logger.error("Workflow session '%s' from user '%s' not found in "
                     "database" % (workflow_session_id, client_id))
        configuration.auth_logger.error(
            "Workflow session '%s' provided by user '%s' but not present in "
            "database" % (workflow_session_id, client_id))
        # TODO Also track multiple attempts from the same IP
        output_objects.append({'object_type': 'error_text',
                               'text': 'Invalid workflowsessionid'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    workflow_session = workflow_sessions_db.get(workflow_session_id)
    logger.info('jsoninterface found %s' % workflow_session)
    owner = workflow_session['owner']

    # User is vgrid owner or member
    success, msg, _ = init_vgrid_script_list(vgrid, owner, configuration)
    if not success:
        logger.error("Illegal access attempt by user '%s' to vgrid '%s'. %s"
                     % (owner, vgrid, msg))
        output_objects.append({'object_type': 'error_text',
                               'text': html_escape(msg)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    status, msg = valid_attributes_for_type(
        configuration, attributes, request_type)
    if not status:
        output_objects.append(
            {'object_type': 'error_text',
             'text': html_escape(msg)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    status, msg = valid_operation_for_type(
        configuration, operation, request_type)
    if not status:
        output_objects.append(
            {'object_type': 'error_text',
             'text': html_escape(msg)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    request_func = VALID_REQUEST_OPERATIONS[request_type][operation]
    status, response = request_func(configuration, owner, attributes)

    output_objects.append(response)
    if not status:
        return (output_objects, returnvalues.SYSTEM_ERROR)

    return (output_objects, returnvalues.OK)
