#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobschedule - Request schedule for a job
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Forward valid schedule requests to grid_script for consistent job
scheduling data"""

from __future__ import absolute_import

import os
import glob

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import all_jobs
from mig.shared.fileio import unpickle, send_message_to_grid_script
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'job_id': REJECT_UNSET}
    return ['saveschedulejobs', defaults]


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

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not configuration.site_enable_jobs:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Job execution is not enabled on this system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

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

                logger.warning('%s tried to %s restricted path %s ! (%s)'
                               % (client_id, op_name, abs_path, pattern))
                continue

            # Insert valid job files in filelist for later treatment

            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '%s: You do not have any matching job IDs!' % pattern})
            status = returnvalues.CLIENT_ERROR
        else:
            filelist += match

    # job schedule is hard on the server, limit

    if len(filelist) > 100:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Too many matching jobs (%d)!'
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
            saveschedulejob['message'] = '''The file containing the information
for job id %s could not be opened! You can only read schedule for your own
jobs!''' % job_id
            saveschedulejobs.append(saveschedulejob)
            status = returnvalues.CLIENT_ERROR
            continue

        saveschedulejob['oldstatus'] = dict['STATUS']

        # Is the job status pending?

        possible_schedule_states = ['QUEUED', 'RETRY', 'FROZEN']
        if not dict['STATUS'] in possible_schedule_states:
            saveschedulejob['message'] = \
                'You can only read schedule for jobs with status: %s.'\
                % ' or '.join(possible_schedule_states)
            saveschedulejobs.append(saveschedulejob)
            continue

        # notify queue

        if not send_message_to_grid_script('JOBSCHEDULE ' + job_id
                                           + '\n', logger, configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Error sending message to grid_script, update may fail.'})
            status = returnvalues.SYSTEM_ERROR
            continue

        saveschedulejobs.append(saveschedulejob)

    savescheduleinfo = """Please find any available job schedule status in
verbose job status output."""
    output_objects.append({'object_type': 'saveschedulejobs',
                           'saveschedulejobs': saveschedulejobs,
                           'savescheduleinfo': savescheduleinfo})
    return (output_objects, status)
