#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobstatus - Display status of jobs
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

"""Job status back end functionality"""

import glob
import os
import time

import shared.returnvalues as returnvalues
from shared.defaults import all_jobs
from shared.fileio import unpickle
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables
from shared.job import output_dir, get_job_ids_with_specified_project_name
from shared.parseflags import verbose, sorted
from shared.useradm import client_id_dir
from shared.validstring import valid_user_path

try:
    import shared.arcwrapper as arc
except Exception, exc:
    # Ignore errors and let it crash if ARC is enabled without the lib
    pass

def signature():
    """Signature of the main function"""

    defaults = {
        'job_id': ['*'],
        'max_jobs': ['1000000'],
        'flags': [''],
        'project_name': [],
        }
    return ['jobs', defaults]


def sort(paths, new_first=True):
    """Sort list of paths after modification time. The new_first
    argument specifies if the newest ones should be at the front
    of the resulting list.
    """

    mtime = os.path.getmtime
    if new_first:
        paths.sort(lambda i, j: cmp(mtime(j), mtime(i)))
    else:
        paths.sort(lambda i, j: cmp(mtime(i), mtime(j)))
    return paths


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
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

    flags = ''.join(accepted['flags'])
    max_jobs = int(accepted['max_jobs'][-1])
    order = 'unsorted '
    if sorted(flags):
        order = 'sorted '
    patterns = accepted['job_id']
    project_names = accepted['project_name']

    if len(project_names) > 0:
        for project_name in project_names:
            project_name_job_ids = \
                get_job_ids_with_specified_project_name(client_id,
                    project_name, configuration.mrsl_files_dir, logger)
            patterns.extend(project_name_job_ids)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = \
        os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                        client_dir)) + os.sep

    output_objects.append({'object_type': 'header', 'text'
                          : '%s %s job status' % \
                            (configuration.short_title, order)})

    if not patterns:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'No job_id specified!'})
        return (output_objects, returnvalues.NO_SUCH_JOB_ID)

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

    if not os.path.isdir(base_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'You have not been created'
                               + ' as a user on the %s server!' % \
                                 configuration.short_title
                               + ' Please contact the %s team.' % \
                                 configuration.short_title })
        return (output_objects, returnvalues.CLIENT_ERROR)

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
        # no (allowed) match....

        if not match:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '%s: You do not have any matching job IDs!'
                                   % pattern})
            status = returnvalues.CLIENT_ERROR
        else:
            filelist += match

    if sorted(flags):
        sort(filelist)

    if max_jobs < len(filelist):
        output_objects.append({'object_type': 'text', 'text'
                              : 'Only showing first %d of the %d matching jobs as requested'
                               % (max_jobs, len(filelist))})
        filelist = filelist[:max_jobs]

    # Iterate through jobs and print details for each

    job_list = {'object_type': 'job_list', 'jobs': []}

    for filepath in filelist:

        # Extract job_id from filepath (replace doesn't modify filepath)

        mrsl_file = filepath.replace(base_dir, '')
        job_id = mrsl_file.replace('.mRSL', '')
        job_dict = unpickle(filepath, logger)
        if not job_dict:
            status = returnvalues.CLIENT_ERROR

            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'You can only list status of your own jobs.'

                                   + ' Please verify that you submitted the mRSL file '

                                   + "with job id '%s' (Could not unpickle mRSL file %s)"
                                   % (job_id, filepath)})
            continue

        # Check that file belongs to the user requesting the status

        if client_id != job_dict['USER_CERT']:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'The job you are trying to get status for does not belong to you!'
                                  })
            status = returnvalues.CLIENT_ERROR
            continue

        job_obj = {'object_type': 'job', 'job_id': job_id}
        job_obj['status'] = job_dict['STATUS']

        time_fields = [
            'VERIFIED',
            'VERIFIED_TIMESTAMP',
            'RECEIVED_TIMESTAMP',
            'QUEUED_TIMESTAMP',
            'SCHEDULE_TIMESTAMP',
            'EXECUTING_TIMESTAMP',
            'FINISHED_TIMESTAMP',
            'FAILED_TIMESTAMP',
            'CANCELED_TIMESTAMP',
            ]
        for name in time_fields:
            if job_dict.has_key(name):

                # time objects cannot be marshalled, asctime if timestamp

                try:
                    job_obj[name.lower()] = time.asctime(job_dict[name])
                except Exception, exc:

                    # not a time object, just add

                    job_obj[name.lower()] = job_dict[name]

        ###########################################
        # ARC job status retrieval on demand:
        # But we should _not_ update the status in the mRSL files, since 
        # other MiG code might rely on finding only valid "MiG" states.
        
        if configuration.arc_clusters and \
               job_dict.get('UNIQUE_RESOURCE_NAME', 'unset') == 'ARC' \
               and job_dict['STATUS'] == 'EXECUTING':
            try:
                home = os.path.join(configuration.user_home, client_dir)
                arcsession = arc.Ui(home)
                arcstatus = arcsession.jobStatus(job_dict['EXE'])
                job_obj['status'] = arcstatus['status']
            except arc.ARCWrapperError, err:
                logger.error('Error retrieving ARC job status: %s' % err.what())
                job_obj['status'] += '(Error: ' + err.what() + ')' 
            except arc.NoProxyError, err:
                logger.error('While retrieving ARC job status: %s' % err.what())
                job_obj['status'] += '(Error: ' + err.what() + ')' 
            except Exception, err:
                logger.error('Error retrieving ARC job status: %s' % err)
                job_obj['status'] += '(Error during retrieval)' 

        execution_histories = []
        if verbose(flags):
            if job_dict.has_key('EXECUTE'):
                command_line = '; '.join(job_dict['EXECUTE'])
                if len(command_line) > 256:
                    job_obj['execute'] = '%s ...' % command_line[:252]
                else:
                    job_obj['execute'] = command_line
            if job_dict.has_key('PUBLICNAME'):
                if job_dict['PUBLICNAME']:
                    job_obj['resource'] = job_dict['PUBLICNAME']
                else:
                    job_obj['resource'] = 'HIDDEN'
            if job_dict.has_key('RESOURCE_VGRID'):
                job_obj['vgrid'] = job_dict['RESOURCE_VGRID']

            if job_dict.has_key('EXECUTION_HISTORY'):
                counter = 0
                for history_dict in job_dict['EXECUTION_HISTORY']:
                    execution_history = \
                        {'object_type': 'execution_history'}

                    if history_dict.has_key('QUEUED_TIMESTAMP'):
                        execution_history['queued'] = \
                            time.asctime(history_dict['QUEUED_TIMESTAMP'
                                ])
                    if history_dict.has_key('EXECUTING_TIMESTAMP'):
                        execution_history['executing'] = \
                            time.asctime(history_dict['EXECUTING_TIMESTAMP'
                                ])
                    if history_dict.has_key('PUBLICNAME'):
                        if history_dict['PUBLICNAME']:
                            execution_history['resource'] = history_dict['PUBLICNAME']
                        else:
                            execution_history['resource'] = 'HIDDEN'
                    if history_dict.has_key('RESOURCE_VGRID'):
                        execution_history['vgrid'] = \
                            history_dict['RESOURCE_VGRID']
                    if history_dict.has_key('FAILED_TIMESTAMP'):
                        execution_history['failed'] = \
                            time.asctime(history_dict['FAILED_TIMESTAMP'
                                ])
                    if history_dict.has_key('FAILED_MESSAGE'):
                        execution_history['failed_message'] = \
                            history_dict['FAILED_MESSAGE']
                    execution_histories.append({'execution_history'
                            : execution_history, 'count': counter})
                    counter += 1
        if job_dict.has_key('SCHEDULE_HINT'):
            job_obj['schedule_hint'] = job_dict['SCHEDULE_HINT']

        job_obj['execution_histories'] = execution_histories

        job_obj['statuslink'] = {'object_type': 'link',
                                 'destination': 'ls.py?path=%s/%s/*'\
                                  % (output_dir, job_id), 'text': 'View status files'}
        job_obj['mrsllink'] = {'object_type': 'link',
                               'destination': 'mrslview.py?job_id=%s'\
                                % job_id,
                               'text': 'View parsed mRSL contents'}

        if job_dict.has_key('OUTPUTFILES') and job_dict['OUTPUTFILES']:

            # Create a single ls link with all supplied outputfiles

            path_string = ''
            for path in job_dict['OUTPUTFILES']:

                # OUTPUTFILES is either just combo path or src dst paths

                parts = path.split()

                # Always take last part as destination

                path_string += 'path=%s;' % parts[-1]

            job_obj['outputfileslink'] = {'object_type': 'link',
                    'destination': 'ls.py?%s' % path_string,
                    'text': 'View output files'}
        job_obj['resubmitlink'] = {'object_type': 'link',
                                   'destination': 'resubmit.py?job_id=%s'\
                                    % job_id, 'text': 'Resubmit job'}

        job_obj['cancellink'] = {'object_type': 'link',
                                 'destination': 'canceljob.py?job_id=%s'\
                                  % job_id, 'text': 'Cancel job'}
        job_obj['jobschedulelink'] = {'object_type': 'link',
                'destination': 'jobschedule.py?job_id=%s' % job_id,
                'text': 'Request schedule information'}
        job_obj['liveoutputlink'] = {'object_type': 'link',
                'destination': 'liveoutput.py?job_id=%s' % job_id,
                'text': 'Request live update'}
        job_list['jobs'].append(job_obj)
    output_objects.append(job_list)

    return (output_objects, status)


