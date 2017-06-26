#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobaction - Request status change (freeze, cancel, ...) for one or more jobs
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Forward valid job state requests to grid_script for consistent job status
changes.
"""

import os
import glob

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import all_jobs
from shared.fileio import unpickle, unpickle_and_change_status, \
    send_message_to_grid_script
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables
from shared.validstring import valid_user_path


# Valid actions and the corresponding new job state

valid_actions = {'cancel': 'CANCELED', 'freeze': 'FROZEN', 'thaw': 'QUEUED'}

def signature():
    """Signature of the main function"""

    defaults = {'job_id': REJECT_UNSET, 'action': REJECT_UNSET}
    return ['changedstatusjobs', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    patterns = accepted['job_id']
    action = accepted['action'][-1]

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not action in valid_actions.keys():
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid job action "%s" (only %s supported)'
                               % (action, ', '.join(valid_actions.keys()))})
        return (output_objects, returnvalues.CLIENT_ERROR)

    new_state = valid_actions[action]

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = \
        os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                        client_dir)) + os.sep

    status = returnvalues.OK
    filelist = []
    for pattern in patterns:
        pattern = pattern.strip()

        # Backward compatibility - all_jobs keyword should match all jobs

        if pattern == all_jobs:
            pattern = '*'

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern + '.mRSL')
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.error(
                    '%s tried to use %s %s outside own home! (pattern %s)'
                    % (client_id, op_name, abs_path, pattern))
                continue

            # Insert valid job files in filelist for later treatment

            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '%s: You do not have any matching job IDs!'
                                   % pattern})
            status = returnvalues.CLIENT_ERROR
        else:
            filelist += match

    # job state change is hard on the server, limit

    if len(filelist) > 500:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Too many matching jobs (%s)!'
                               % len(filelist)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    changedstatusjobs = []

    for filepath in filelist:

        # Extract job_id from filepath (replace doesn't modify filepath)

        mrsl_file = filepath.replace(base_dir, '')
        job_id = mrsl_file.replace('.mRSL', '')

        changedstatusjob = {'object_type': 'changedstatusjob',
                            'job_id': job_id}

        job_dict = unpickle(filepath, logger)
        if not job_dict:
            changedstatusjob['message'] = '''The file containing the
information for job id %s could not be opened! You can only %s your own
jobs!''' % (job_id, action)
            changedstatusjobs.append(changedstatusjob)
            status = returnvalues.CLIENT_ERROR
            continue

        changedstatusjob['oldstatus'] = job_dict['STATUS']

        # Is the job status compatible with action?

        possible_cancel_states = ['PARSE', 'QUEUED', 'RETRY', 'EXECUTING',
                                  'FROZEN']
        if action == 'cancel' and \
               not job_dict['STATUS'] in possible_cancel_states:
            changedstatusjob['message'] = \
                'You can only cancel jobs with status: %s.'\
                 % ' or '.join(possible_cancel_states)
            status = returnvalues.CLIENT_ERROR
            changedstatusjobs.append(changedstatusjob)
            continue
        possible_freeze_states = ['QUEUED', 'RETRY']
        if action == 'freeze' and \
               not job_dict['STATUS'] in possible_freeze_states:
            changedstatusjob['message'] = \
                'You can only freeze jobs with status: %s.'\
                 % ' or '.join(possible_freeze_states)
            status = returnvalues.CLIENT_ERROR
            changedstatusjobs.append(changedstatusjob)
            continue
        possible_thaw_states = ['FROZEN']
        if action == 'thaw' and \
               not job_dict['STATUS'] in possible_thaw_states:
            changedstatusjob['message'] = \
                'You can only thaw jobs with status: %s.'\
                 % ' or '.join(possible_thaw_states)
            status = returnvalues.CLIENT_ERROR
            changedstatusjobs.append(changedstatusjob)
            continue

        # job action is handled by changing the STATUS field, notifying the
        # job queue and making sure the server never submits jobs with status
        # FROZEN or CANCELED.

        # file is repickled to ensure newest information is used, job_dict
        # might be old if another script has modified the file.

        if not unpickle_and_change_status(filepath, new_state, logger):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Job status could not be changed to %s!'
                                   % new_state})
            status = returnvalues.SYSTEM_ERROR

        # Avoid key error and make sure grid_script gets expected number of
        # arguments

        if not job_dict.has_key('UNIQUE_RESOURCE_NAME'):
            job_dict['UNIQUE_RESOURCE_NAME'] = \
                'UNIQUE_RESOURCE_NAME_NOT_FOUND'
        if not job_dict.has_key('EXE'):
            job_dict['EXE'] = 'EXE_NAME_NOT_FOUND'

        # notify queue

        if not send_message_to_grid_script('JOBACTION ' + job_id + ' '
                                           + job_dict['STATUS'] + ' '
                                           + new_state + ' '
                                           + job_dict['UNIQUE_RESOURCE_NAME']
                                           + ' ' + job_dict['EXE'] + '\n',
                                           logger, configuration):
            output_objects.append({'object_type': 'error_text', 'text'
                                   : '''Error sending message to grid_script,
job may still be in the job queue.'''})
            status = returnvalues.SYSTEM_ERROR
            continue

        changedstatusjob['newstatus'] = new_state
        changedstatusjobs.append(changedstatusjob)

    output_objects.append({'object_type': 'changedstatusjobs',
                          'changedstatusjobs': changedstatusjobs})
    return (output_objects, status)
