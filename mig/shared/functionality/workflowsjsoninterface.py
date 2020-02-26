#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# workflowsjsoninterface.py - JSON interface for
# managing workflows via cgisid requests
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""JSON interface for workflows related requests"""

import sys
import json
import shared.returnvalues as returnvalues

from shared.base import force_utf8_rec
from shared.init import initialize_main_variables
from shared.safeinput import REJECT_UNSET, valid_workflow_pers_id, \
    valid_workflow_vgrid, valid_workflow_name, valid_workflow_input_file, \
    valid_workflow_input_paths, valid_workflow_output, valid_workflow_recipes,\
    valid_workflow_variables, valid_workflow_attributes, valid_workflow_type, \
    valid_workflow_operation, valid_sid, validated_input, html_escape
from shared.workflows import WORKFLOW_TYPES, WORKFLOW_CONSTRUCT_TYPES, \
    WORKFLOW_PATTERN, valid_session_id, get_workflow_with,\
    load_workflow_sessions_db, create_workflow, delete_workflow,\
    update_workflow, touch_workflow_sessions_db, search_workflow, \
    WORKFLOW_ACTION_TYPES, WORKFLOW_SEARCH_TYPES

WORKFLOW_API_CREATE = 'create'
WORKFLOW_API_READ = 'read'
WORKFLOW_API_UPDATE = 'update'
WORKFLOW_API_DELETE = 'delete'

PATTERN_LIST = 'pattern_list'
RECIPE_LIST = 'recipe_list'

VALID_OPERATIONS = [WORKFLOW_API_CREATE, WORKFLOW_API_READ,
                    WORKFLOW_API_UPDATE, WORKFLOW_API_DELETE]

WORKFLOW_SIGNATURE = {
    'attributes': {},
    'type': REJECT_UNSET,
    'operation': REJECT_UNSET,
    'workflowsessionid': REJECT_UNSET,
    'persistence_id': '',
    'vgrid': '',
    'name': '',
    'input_file': '',
    'input_paths': [],
    'output': {},
    'recipes': [],
    'variables': {},
    'parameterize_over': {}
}


def type_value_checker(type_value):
    """
    Validate that the provided workflow type is allowed. A ValueError
    Exception will be raised if type_value is invalid.
    :param type_value: The type to be checked. Valid types are
    'workflowpattern', 'workflowrecipe', 'any', and 'manual_trigger'.
    :return: No return
    """
    valid_types = WORKFLOW_TYPES + WORKFLOW_ACTION_TYPES +\
                  WORKFLOW_SEARCH_TYPES

    if type_value not in valid_types:
        raise ValueError("Workflow type '%s' is not valid"
                         % html_escape(valid_types))


def operation_value_checker(operation_value):
    """
    Validate that the provided workflow operation is allowed. A ValueError
    Exception will be raised if operation_value is invalid.
    :param operation_value: The operation to be checked. Valid operations are:
    'create', 'read', 'update' and 'delete'.
    :return: No return.
    """
    if operation_value not in VALID_OPERATIONS:
        raise ValueError("Workflow operation '%s' is not valid"
                         % html_escape(operation_value))


WORKFLOW_ATTRIBUTES_TYPE_MAP = {
    'persistence_id': valid_workflow_pers_id,
    'vgrid': valid_workflow_vgrid,
    'name': valid_workflow_name,
    'input_file': valid_workflow_input_file,
    'input_paths': valid_workflow_input_paths,
    'output': valid_workflow_output,
    'recipes': valid_workflow_recipes,
    'variables': valid_workflow_variables,
    'parameterize_over': valid_workflow_variables
}


WORKFLOWS_INPUT_TYPE_MAP = {
    'attributes': valid_workflow_attributes,
    'type': valid_workflow_type,
    'operation': valid_workflow_operation,
    'workflowsessionid': valid_sid
}

WORKFLOWS_TYPE_MAP = dict(WORKFLOW_ATTRIBUTES_TYPE_MAP,
                          **WORKFLOWS_INPUT_TYPE_MAP)

WORKFLOW_VALUE_MAP = {
    'type': type_value_checker,
    'operation': operation_value_checker,
}


# Workflow API functions
def workflow_api_create(configuration, workflow_session,
                        workflow_type=WORKFLOW_PATTERN, **workflow_attributes):
    """
    Handler for 'create' calls to workflow API.
    :param configuration: The MiG configuration object.
    :param workflow_session: The MiG workflow session. This must contain the
    key 'owner'
    :param workflow_type: [optional] A MiG workflow construct type. This should
    be one of 'workflowpattern' or 'workflowrecipe'. Default is
    'workflowpattern'.
    :param workflow_attributes: dictionary of arguments used to create the
    specified workflow object
    :return: (Tuple (boolean, string) or function call to 'create_workflow')
    if workflow_type is valid the function 'create_workflow' is called. Else,
    a tuple is returned with a first value of False, and an explanatory error
    message as the second value.
    """
    _logger = configuration.logger
    _logger.debug("W_API: create: (%s, %s, %s)" % (workflow_session,
                                                   workflow_type,
                                                   workflow_attributes))

    if workflow_type in WORKFLOW_CONSTRUCT_TYPES:
        return create_workflow(configuration,
                               workflow_session['owner'],
                               workflow_type=workflow_type,
                               **workflow_attributes)
    return (False, "Invalid workflow create api type: '%s', valid are: '%s'" %
            (workflow_type,
             ', '.join(WORKFLOW_CONSTRUCT_TYPES)))


def workflow_api_read(configuration, workflow_session,
                      workflow_type=WORKFLOW_PATTERN, **workflow_attributes):
    """
    Handler for 'read' calls to workflow API.
    :param configuration: The MiG configuration object.
    :param workflow_session: The MiG workflow session. This must contain the
    key 'owner'
    :param workflow_type: [optional] A MiG workflow read type. This should
    be one of 'job', 'queue', 'workflowpattern', 'workflowrecipe', 'any' or
    'pattern_graph'. Default is 'workflowpattern'.
    :param workflow_attributes: dictionary of arguments used to select the
    workflow object to read.
    :return: (Tuple (boolean, string) or function call to 'get_jobs_with',
    'get_workflow_with' or 'search_workflow') If the given workflow_type is
    either 'job' or 'queue' the function 'get_jobs_with' will be called. If
    the given workflow type is either 'workflowpattern', 'workflowrecipe', or
    'any' the function 'get_workflow_with' is called. If the given
    workflow_type is 'pattern_graph' the function 'search_workflow' is called.
    If the given workflow_type is none of the above a tuple is returned with a
    first value of False, and an explanatory error message as the second value.
    """
    _logger = configuration.logger
    _logger.debug("W_API: search: (%s, %s, %s)" % (workflow_session,
                                                   workflow_type,
                                                   workflow_attributes))

    if workflow_type in WORKFLOW_TYPES:
        workflows = get_workflow_with(configuration,
                                      workflow_session['owner'],
                                      user_query=True,
                                      workflow_type=workflow_type,
                                      **workflow_attributes)
        if not workflows:
            return (False, 'Failed to find a workflow you own with '
                           'attributes: %s' % workflow_attributes)
        return (workflows, '')
    elif workflow_type in WORKFLOW_SEARCH_TYPES:
        return search_workflow(configuration,
                               workflow_session['owner'],
                               workflow_type=workflow_type,
                               **workflow_attributes)
    return (False, "Invalid workflow read api type: '%s', valid are: '%s'" %
            (workflow_type, ', '.join(WORKFLOW_TYPES)))


def workflow_api_update(configuration, workflow_session,
                        workflow_type=WORKFLOW_PATTERN, **workflow_attributes):
    """
    Handler for 'update' calls to workflow API.
    :param configuration: The MiG configuration object.
    :param workflow_session: The MiG workflow session. This must contain the
    key 'owner'
    :param workflow_type: [optional] A MiG workflow construct type. This should
    be one of 'workflowpattern' or 'workflowrecipe'. Default is
    'workflowpattern'.
    :param workflow_attributes: dictionary of arguments used to update the
    specified workflow object. Must contain key 'vgrid'.
    :return: (Tuple (boolean, string) or function call to 'update_workflow')
    If the given workflow_type is valid the function 'update_workflow' will be
    called. Else, a tuple is returned with a first value of False, and an
    explanatory error message as the second value.
    """
    _logger = configuration.logger
    _logger.debug("W_API: update: (%s, %s, %s)" % (workflow_session,
                                                   workflow_type,
                                                   workflow_attributes))

    if 'vgrid' not in workflow_attributes:
        return (False, "Can't create workflow %s without 'vgrid' attribute"
                % workflow_type)

    if workflow_type in WORKFLOW_CONSTRUCT_TYPES:
        return update_workflow(configuration, workflow_session['owner'],
                               workflow_type, **workflow_attributes)

    return (False, "Invalid workflow update api type: '%s', valid are: '%s'" %
            (workflow_type, ', '.join(WORKFLOW_CONSTRUCT_TYPES)))


def workflow_api_delete(configuration, workflow_session,
                        workflow_type=WORKFLOW_PATTERN, **workflow_attributes):
    """
    Handler for 'delete' calls to workflow API.
    :param configuration: The MiG configuration object.
    :param workflow_session: The MiG workflow session. This must contain the
    key 'owner'
    :param workflow_type: [optional] A MiG workflow construct type. This should
    be one of 'workflowpattern' or 'workflowrecipe'. Default is
    'workflowpattern'.
    :param workflow_attributes: dictionary of arguments used to update the
    specified workflow object. Must contain key 'persistence_id'.
    :return: (Tuple (boolean, string) or function call to 'delete_workflow')
    If the given workflow_type is valid the function 'delete_workflow' will be
    called. Else, a tuple is returned with a first value of False, and an
    explanatory error message as the second value.
    """
    _logger = configuration.logger
    _logger.debug("W_API: delete: (%s, %s, %s)" % (workflow_session,
                                                   workflow_type,
                                                   workflow_attributes))

    if 'persistence_id' not in workflow_attributes:
        return (False, "Can't delete workflow without 'persistence_id' "
                       "attribute"
                % workflow_attributes)

    if workflow_type in WORKFLOW_CONSTRUCT_TYPES:
        return delete_workflow(configuration, workflow_session['owner'],
                               workflow_type, **workflow_attributes)

    return (False, "Invalid workflow update api type: '%s', valid are: '%s'" %
            (workflow_type, ', '.join(WORKFLOW_CONSTRUCT_TYPES)))


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
                               'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # IMPORTANT!! Do not access the json_data input before it has been
    # validated by validated_input.
    accepted, rejected = validated_input(
        json_data, WORKFLOW_SIGNATURE,
        type_override=WORKFLOWS_TYPE_MAP,
        value_override=WORKFLOW_VALUE_MAP,
        list_wrap=True)

    if not accepted or rejected:
        logger.error("A validation error occurred: '%s'" % rejected)
        msg = "Invalid input was supplied to the workflow API: %s" % rejected
        # TODO, Transform error messages to something more readable
        output_objects.append({'object_type': 'error_text', 'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    workflow_attributes = json_data.get('attributes', None)
    workflow_type = json_data.get('type', None)
    operation = json_data.get('operation', None)
    workflow_session_id = json_data.get('workflowsessionid', None)

    if not valid_session_id(configuration, workflow_session_id):
        output_objects.append({'object_type': 'error_text',
                               'text': 'Invalid workflowsessionid'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # workflow_session_id symlink points to the vGrid it gives access to
    workflow_sessions_db = []
    try:
        workflow_sessions_db = load_workflow_sessions_db(configuration)
    except IOError:
        logger.debug("Workflow sessions db didn't load, creating new db")
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
        # TODO, Log this in the auth logger,
        # Also track multiple attempts from the same IP
        output_objects.append({'object_type': 'error_text',
                               'text': 'Invalid workflowsessionid'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    workflow_session = workflow_sessions_db.get(workflow_session_id)
    logger.info('workflowjsoninterface found %s' % workflow_session)
    # Create
    if operation == WORKFLOW_API_CREATE:
        created, msg = workflow_api_create(configuration,
                                           workflow_session,
                                           workflow_type,
                                           **workflow_attributes)
        if not created:
            output_objects.append({'object_type': 'error_text',
                                   'text': msg})
            logger.error("Returning error msg '%s'" % msg)
            return (output_objects, returnvalues.CLIENT_ERROR)
        output_objects.append({'object_type': 'workflows',
                               'text': msg})
        return (output_objects, returnvalues.OK)
    # Read
    if operation == WORKFLOW_API_READ:
        workflows, msg = workflow_api_read(configuration, workflow_session,
                                           workflow_type,
                                           **workflow_attributes)
        if not workflows:
            output_objects.append(
                {'object_type': 'error_text',
                 'text': msg})
            return (output_objects, returnvalues.OK)

        output_objects.append({'object_type': 'workflows',
                               'workflows': workflows})
        return (output_objects, returnvalues.OK)

    # Update
    if operation == WORKFLOW_API_UPDATE:
        updated, msg = workflow_api_update(configuration, workflow_session,
                                           workflow_type,
                                           **workflow_attributes)
        if not updated:
            output_objects.append({'object_type': 'error_text',
                                   'text': msg})
            return (output_objects, returnvalues.OK)
        output_objects.append({'object_type': 'workflows',
                               'text': msg})
        return (output_objects, returnvalues.OK)

    # Delete
    if operation == WORKFLOW_API_DELETE:
        deleted, msg = workflow_api_delete(configuration, workflow_session,
                                           workflow_type,
                                           **workflow_attributes)
        if not deleted:
            output_objects.append({'object_type': 'error_text',
                                   'text': msg})
            return (output_objects, returnvalues.OK)
        output_objects.append({'object_type': 'workflows', 'text': msg})
        return (output_objects, returnvalues.OK)

    output_objects.append({'object_type': 'error_text',
                           'text': 'You are out of bounds here'})
    return (output_objects, returnvalues.CLIENT_ERROR)
