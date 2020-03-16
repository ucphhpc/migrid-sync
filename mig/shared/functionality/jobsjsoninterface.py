#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobsjsoninterface.py - JSON interface for
# managing jobs via cgisid requests
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
#

"""JSON interface for job related requests"""

import json
import os
import sys
import tempfile

import shared.returnvalues as returnvalues

from shared.base import force_utf8_rec, client_id_dir
from shared.fileio import unpickle, unpickle_and_change_status, \
    send_message_to_grid_script
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.job import new_job
from shared.mrslkeywords import get_keywords_dict
from shared.safeinput import REJECT_UNSET, valid_sid, validated_input, \
    html_escape, valid_job_id, valid_job_vgrid, valid_job_attributes, \
    valid_job_type, valid_job_operation
from shared.job import JOB_TYPES, JOB, QUEUE, get_job_with_id, fields_to_mrsl
from shared.workflows import valid_session_id, load_workflow_sessions_db, \
    touch_workflow_sessions_db
from shared.vgrid import get_vgrid_workflow_jobs, init_vgrid_script_list

JOB_API_CREATE = 'create'
JOB_API_READ = 'read'
JOB_API_UPDATE = 'update'

PATTERN_LIST = 'pattern_list'
RECIPE_LIST = 'recipe_list'

VALID_OPERATIONS = [
    JOB_API_CREATE, JOB_API_READ, JOB_API_UPDATE
]

JOB_SIGNATURE = {
    'attributes': {},
    'type': REJECT_UNSET,
    'operation': REJECT_UNSET,
    'workflowsessionid': REJECT_UNSET,
    'job_id': '',
    'vgrid': ''
}


def type_value_checker(type_value):
    """
    Validate that the provided job type is allowed. A ValueError
    Exception will be raised if type_value is invalid.
    :param type_value: The type to be checked. Valid types are 'job',
    and 'queue'
    :return: No return
    """
    valid_types = JOB_TYPES

    if type_value not in valid_types:
        raise ValueError("Workflow type '%s' is not valid. "
                         % html_escape(type_value))


def operation_value_checker(operation_value):
    """
    Validate that the provided job operation is allowed. A ValueError
    Exception will be raised if operation_value is invalid.
    :param operation_value: The operation to be checked. Valid operations are:
    'create', 'read', 'update' and 'delete'.
    :return: No return.
    """
    if operation_value not in VALID_OPERATIONS:
        raise ValueError("Workflow operation '%s' is not valid. "
                         % html_escape(operation_value))


JOB_ATTRIBUTES_TYPE_MAP = {
    'job_id': valid_job_id,
    'vgrid': valid_job_vgrid
}


JOB_INPUT_TYPE_MAP = {
    'attributes': valid_job_attributes,
    'type': valid_job_type,
    'operation': valid_job_operation,
    'workflowsessionid': valid_sid
}

JOB_TYPE_MAP = dict(JOB_ATTRIBUTES_TYPE_MAP, **JOB_INPUT_TYPE_MAP)

JOB_VALUE_MAP = {
    'type': type_value_checker,
    'operation': operation_value_checker,
}


# Job API functions
def job_api_create(configuration, workflow_session, job_type=JOB,
                   **job_attributes):
    """
    Handler for 'create' calls to job API.
    :param configuration: The MiG configuration object.
    :param workflow_session: The MiG job session. This must contain the
    key 'owner'
    :param job_type: [optional] A MiG job type. Default is 'job'.
    :param job_attributes: dictionary of arguments used to create the job
    :return: Tuple (boolean, string)
    If a job can be created then a tuple is returned of first value True, and
    the created job's id in the second value. If it cannot be created then a
    tuple is returned with a first value of False, and an explanatory error
    message as the second value.
    """
    _logger = configuration.logger

    client_id = workflow_session['owner']
    external_dict = get_keywords_dict(configuration)

    if 'vgrid' not in job_attributes:
        msg = "Cannot create new job without specifying a VGrid for it to be " \
              "attached to. "
        return (False, msg)
    vgrid = job_attributes['vgrid']

    # User is vgrid owner or member
    success, msg, _ = init_vgrid_script_list(vgrid, client_id, configuration)
    if not success:
        return (False, msg)

    job_attributes.pop('vgrid')

    mrsl = fields_to_mrsl(configuration, job_attributes, external_dict)

    tmpfile = None

    # save to temporary file
    try:
        (filehandle, real_path) = tempfile.mkstemp(text=True)
        os.write(filehandle, mrsl)
        os.close(filehandle)
    except Exception, err:
        msg = 'Failed to write temporary mRSL file: %s' % err
        _logger.error(msg)
        return (False, msg)

    # submit it
    try:
        (job_status, newmsg, job_id) = \
            new_job(real_path, client_id, configuration, False, True)
    except Exception, exc:
        msg = "Failed to submit new job. Possible invalid mRSL?"
        _logger.error(msg)
        return (False, msg)

    if not job_status:
        _logger.error(newmsg)
        return (False, newmsg)

    return (True, job_id)


def job_api_read(configuration, workflow_session, job_type=JOB,
                 **job_attributes):
    """
    Handler for 'read' calls to job API.
    :param configuration: The MiG configuration object.
    :param workflow_session: The MiG workflow session. This must contain the
    key 'owner'
    :param job_type: [optional] A MiG job read type. This should
    be one of 'job', or 'queue'. Default is 'job'.
    :param job_attributes: dictionary of arguments used to select the
    job to read.
    :return: (Tuple (boolean, string) or function call to 'get_job_with_id')
    If the given job_type is 'job', the function 'get_job_with_id' will be
    called. If the given job_type is 'queue' then a tuple is returned with the
    first value being True and a dictionary of jobs being the second value,
    with the job ids being the keys. If a problem is encountered a tuple is
    returned with the first value being False and an explanatory error message
    for a second value.
    """
    _logger = configuration.logger

    if 'vgrid' not in job_attributes:
        return (False, "Can't read jobs without 'vgrid' attribute")
    vgrid = job_attributes['vgrid']

    # User is vgrid owner or member
    client_id = workflow_session['owner']
    success, msg, _ = init_vgrid_script_list(vgrid, client_id,
                                             configuration)
    if not success:
        return (False, msg)

    if job_type == QUEUE:
        job_list = get_vgrid_workflow_jobs(
            configuration, vgrid, json_serializable=True
        )

        _logger.info("Found %d jobs" % len(job_list))

        job_dict = {}
        for job in job_list:
            job_dict[job['JOB_ID']] = job

        return (True, job_dict)
    else:
        if 'job_id' not in job_attributes:
            return (False, "Can't read single job without 'job_id' attribute")

        return get_job_with_id(
            configuration,
            job_attributes['job_id'],
            vgrid,
            workflow_session['owner'],
            only_user_jobs=False
        )


def job_api_update(configuration, workflow_session, job_type=JOB,
                   **job_attributes):
    """
    Handler for 'update' calls to job API.
    :param configuration: The MiG configuration object.
    :param workflow_session: The MiG workflow session. This must contain the
    key 'owner'
    :param job_type: [optional] A MiG job type. Default is 'job'.
    :param job_attributes: dictionary of arguments used to update the
    specified workflow object. Currently can only be a job id to cancel.
    :return: Tuple (boolean, string)
    If the given job_type is valid a tuple is returned with True in the
    first value and a feedback message in the second. Else, a tuple is
    returned with a first value of False, and an explanatory error message as
    the second value.
    """
    _logger = configuration.logger

    client_id = workflow_session['owner']

    job_id = job_attributes.get('JOB_ID', None)
    if not job_id:
        msg = "No job id provided in update"
        _logger.error(msg)
        return (False, msg)

    if 'vgrid' not in job_attributes:
        return (False, "Can't update job without 'vgrid' attribute")
    vgrid = job_attributes['vgrid']

    # User is vgrid owner or member
    client_id = workflow_session['owner']
    success, msg, _ = init_vgrid_script_list(vgrid, client_id,
                                             configuration)
    if not success:
        return (False, msg)

    status, job = get_job_with_id(
        configuration,
        job_id,
        vgrid,
        client_id,
        only_user_jobs=False
    )

    if not status:
        msg = "Could not open job file for job '%s'" % job_id
        _logger.error(msg)
        return (False, msg)

    if 'STATUS' in job_attributes:
        new_state = 'CANCELED'
        if job_attributes['STATUS'] == new_state:
            possible_cancel_states = [
                'PARSE', 'QUEUED', 'RETRY', 'EXECUTING', 'FROZEN'
            ]

            if not job['STATUS'] in possible_cancel_states:
                msg = 'Could not cancel job with status ' + job['STATUS']
                _logger.error(msg)
                return (False, msg)

            job_user_dir = client_id_dir(job['USER_CERT'])
            file_path = os.path.join(
                configuration.mrsl_files_dir, job_user_dir, job_id + '.mRSL')
            if not unpickle_and_change_status(file_path, new_state, _logger):
                _logger.error('%s could not cancel job: %s'
                              % (client_id, job_id))
                msg = 'Could not change status of job ' + job_id
                _logger.error(msg)
                return (False, msg)

            if not job.has_key('UNIQUE_RESOURCE_NAME'):
                job['UNIQUE_RESOURCE_NAME'] = 'UNIQUE_RESOURCE_NAME_NOT_FOUND'
            if not job.has_key('EXE'):
                job['EXE'] = 'EXE_NAME_NOT_FOUND'

            message = 'JOBACTION ' + job_id + ' ' \
                      + job['STATUS'] + ' ' + new_state + ' ' \
                      + job['UNIQUE_RESOURCE_NAME'] + ' ' \
                      + job['EXE'] + '\n'
            if not send_message_to_grid_script(message, _logger, configuration):
                msg = '%s failed to send message to grid script: %s' \
                      % (client_id, message)
                _logger.error(msg)
                return (False, msg)
            return (True, 'Job %s has been succesfully canceled' % job_id)

    return (False, "No updated applied from attributes '%s'" % job_attributes)


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

    if not correct_handler('POST'):
        msg = "Interaction from %s not POST request" % client_id
        logger.error(msg)
        output_objects.append({
            'object_type': 'error_text',
            'text': msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not configuration.site_enable_workflows:
        output_objects.append({
            'object_type': 'error_text',
            'text': 'Workflows are not enabled on this system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

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

    # TODO: consider additional CSRF protection here?
    # attacker needs to intercept jupyter session_id from running session
    # and work around security restrictions in Jupyter API to abuse anything
    # https://github.com/jupyter/jupyter/wiki/Jupyter-Notebook-Server-API

    # IMPORTANT!! Do not access the json_data input before it has been
    # validated by validated_input.
    accepted, rejected = validated_input(
        json_data, JOB_SIGNATURE,
        type_override=JOB_TYPE_MAP,
        value_override=JOB_VALUE_MAP,
        list_wrap=True)

    if not accepted or rejected:
        logger.error("A validation error occurred: '%s'" % rejected)
        msg = "Invalid input was supplied to the job API: %s" % rejected
        # TODO, Transform error messages to something more readable
        output_objects.append({'object_type': 'error_text', 'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    job_type = accepted.pop('type', [None])[0]
    operation = accepted.pop('operation', None)
    workflow_session_id = accepted.pop('workflowsessionid', None)
    job_attributes = {}
    for key, value in accepted.items():
        if key in json_data['attributes']:
            job_attributes[key] = value

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

    if 'vgrid' not in job_attributes:
        logger.info("Invalid json job interaction. user '%s' does not specify "
                    "a vgrid in '%s'" % (client_id, job_attributes.keys()))
        msg = "Cannot create new job without specifying a VGrid for it to be " \
              "attached to. "
        output_objects.append({'object_type': 'error_text',
                               'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)
    vgrid = job_attributes['vgrid']

    # User is vgrid owner or member
    success, msg, _ = init_vgrid_script_list(vgrid, client_id,
                                             configuration)
    if not success:
        logger.error("Illegal access attempt by user '%s' to vgrid '%s'. %s"
                     % (client_id, vgrid, msg))
        output_objects.append({'object_type': 'error_text',
                               'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Create
    if operation == JOB_API_CREATE:
        created, msg = job_api_create(configuration, workflow_session,
                                      job_type, **job_attributes)
        if not created:
            output_objects.append({'object_type': 'error_text',
                                   'text': msg})
            logger.error("Returning error msg '%s'" % msg)
            return (output_objects, returnvalues.CLIENT_ERROR)
        output_objects.append({'object_type': 'text', 'text': msg})
        return (output_objects, returnvalues.OK)
    # Read
    if operation == JOB_API_READ:
        status, jobs = job_api_read(configuration, workflow_session,
                                 job_type, **job_attributes)
        if not status:
            output_objects.append(
                {'object_type': 'error_text',
                 'text': jobs})
            return (output_objects, returnvalues.OK)

        output_objects.append({'object_type': 'job_dict', 'jobs': jobs})
        return (output_objects, returnvalues.OK)

    # Update
    if operation == JOB_API_UPDATE:
        updated, msg = job_api_update(configuration, workflow_session,
                                      job_type, **job_attributes)
        if not updated:
            output_objects.append({'object_type': 'error_text',
                                   'text': msg})
            return (output_objects, returnvalues.OK)
        output_objects.append({'object_type': 'text', 'text': msg})
        return (output_objects, returnvalues.OK)

    # Delete has not been implemented, and probably shouldn't be. Jobs may be
    # canceled remotely but not entirely deleted.

    output_objects.append({'object_type': 'error_text',
                           'text': 'You are out of bounds here'})
    return (output_objects, returnvalues.CLIENT_ERROR)
