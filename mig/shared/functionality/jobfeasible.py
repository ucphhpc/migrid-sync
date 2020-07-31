#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobfeasible - Request job feasibility status for a waiting job
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Run feasibility check for waiting job"""
from __future__ import absolute_import

import os
import glob

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import all_jobs
from mig.shared.fileio import unpickle
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables
from mig.shared.jobfeasibility import job_feasibility
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'job_id': REJECT_UNSET}
    return ['checkcondjobs', defaults]


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
            '''Job execution is not enabled on this system'''})
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

        # Check directory traversal attempts before actual handling to
        # avoid leaking information about file system layout while
        # allowing consistent error messages

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
        # (allowed) match^I

        if not match:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '%s: You do not have any matching job IDs!'
                                   % pattern})
            status = returnvalues.CLIENT_ERROR
        else:
            filelist += match

    # job feasibility is hard on the server, limit

    if len(filelist) > 100:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Too many matching jobs (%s)!'
                               % len(filelist)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    checkcondjobs = []

    for filepath in filelist:

        # Extract job_id from filepath (replace doesn't modify filepath)

        mrsl_file = filepath.replace(base_dir, '')
        job_id = mrsl_file.replace('.mRSL', '')

        checkcondjob = {'object_type': 'checkcondjob',
                           'job_id': job_id}

        dict = unpickle(filepath, logger)
        if not dict:
            checkcondjob['message'] = \
                                    ('The file containing the information ' \
                                     'for job id %s could not be opened! ' \
                                     'You can only check feasibility of ' \
                                     'your own jobs!'
                                     ) % job_id
            checkcondjobs.append(checkcondjob)
            status = returnvalues.CLIENT_ERROR
            continue

        # Is the job status pending?

        possible_check_states = ['QUEUED', 'RETRY', 'FROZEN']
        if not dict['STATUS'] in possible_check_states:
            checkcondjob['message'] = \
                'You can only check feasibility of jobs with status: %s.'\
                 % ' or '.join(possible_check_states)
            checkcondjobs.append(checkcondjob)
            continue

        # Actually check feasibility
        feasible_res = job_feasibility(configuration, dict)
        checkcondjob.update(feasible_res)
        checkcondjobs.append(checkcondjob)

    output_objects.append({'object_type': 'checkcondjobs',
                          'checkcondjobs': checkcondjobs})
    return (output_objects, status)
