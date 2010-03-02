#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobschedule - Request schedule for a job
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Forward valid schedule requests to grid_script for consistent job schedule data"""

import os
import glob

import shared.returnvalues as returnvalues
from shared.defaults import all_jobs
from shared.fileio import unpickle, send_message_to_grid_script
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.useradm import client_id_dir
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'job_id': REJECT_UNSET}
    return ['saveschedulejobs', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()
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

        # Check directory traversal attempts before actual handling to
        # avoid leaking information about file system layout while
        # allowing consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern + '.mRSL')
        match = []
        for server_path in unfiltered_match:
            real_path = os.path.abspath(server_path)
            if not valid_user_path(real_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.error('%s tried to use %s %s outside own home! (pattern %s)'
                              % (client_id, op_name, real_path,
                             pattern))
                continue

            # Insert valid job files in filelist for later treatment

            match.append(real_path)

        # Now actually treat list of allowed matchings and notify if
        # no (allowed) match^I

        if not match:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '%s: You do not have any matching job IDs!'
                                   % pattern})
            status = returnvalues.CLIENT_ERROR
        else:
            filelist += match

    # job schedule is hard on the server, limit

    if len(filelist) > 100:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Too many matching jobs (%s)!'
                               % len(filelist)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    saveschedulejobs = []

    for filepath in filelist:

        # Extract job_id from filepath (replace doesn't modify filepath)

        mrsl_file = filepath.replace(base_dir, '')
        job_id = mrsl_file.replace('.mRSL', '')

        saveschedulejob = {'object_type': 'saveschedulejob',
                           'job_id': job_id}

        dict = unpickle(filepath, logger)
        if not dict:
            saveschedulejob['message'] = \
                'The file containing the information for job id %s could not be opened! You can only read schedule for your own jobs!'\
                 % job_id
            saveschedulejobs.append(saveschedulejob)
            status = returnvalues.CLIENT_ERROR
            continue

        # Check that file belongs to the user requesting the job schedule

        if client_id != dict['USER_CERT']:
            saveschedulejob['message'] = \
                '%s the job you are trying to modify does not belong to you!'\
                 % client_id
            status = returnvalues.CLIENT_ERROR
            saveschedulejobs.append(saveschedulejob)
            continue

        saveschedulejob['oldstatus'] = dict['STATUS']

        # Is the job status QUEUED or RETRY?

        possible_schedule_states = ['QUEUED', 'RETRY']
        if not dict['STATUS'] in possible_schedule_states:
            saveschedulejob['message'] = \
                'You can only read schedule for jobs with status: %s.'\
                 % ' or '.join(possible_schedule_states)
            saveschedulejobs.append(saveschedulejob)
            continue

        # notify queue

        if not send_message_to_grid_script('JOBSCHEDULE ' + job_id
                 + '\n', logger, configuration):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Error sending message to grid_script, job may not be updated.'
                                  })
            status = returnvalues.SYSTEM_ERROR
            continue

        saveschedulejobs.append(saveschedulejob)

    output_objects.append({'object_type': 'saveschedulejobs',
                          'saveschedulejobs': saveschedulejobs})
    return (output_objects, status)


