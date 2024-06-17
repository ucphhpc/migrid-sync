#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobstatus - Display status of jobs
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

"""Job status back end functionality"""

from __future__ import absolute_import

import glob
import os
import time

from mig.shared import returnvalues
from mig.shared.base import client_id_dir, hexlify
from mig.shared.defaults import all_jobs, job_output_dir, csrf_field
from mig.shared.fileio import unpickle
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.htmlgen import html_post_helper
from mig.shared.init import initialize_main_variables
from mig.shared.job import get_job_ids_with_specified_project_name
from mig.shared.mrslparser import expand_variables
from mig.shared.parseflags import verbose, sorted, interactive
from mig.shared.resource import anon_resource_id
from mig.shared.validstring import valid_user_path

try:
    from mig.shared import arcwrapper
except Exception as exc:
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
    # NOTE: switched to use key instead of cmp to support both python 2 and 3
    # https://portingguide.readthedocs.io/en/latest/comparisons.html#the-cmp-argument
    paths.sort(key=lambda i: mtime(i))
    if new_first:
        paths = paths[::-1]
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
        logger.error("jobstatus input validation failed: %s" % accepted)
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

    if not configuration.site_enable_jobs:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Job execution is not enabled on this system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = \
        os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                                     client_dir)) + os.sep

    output_objects.append({'object_type': 'header', 'text': '%s %s job status' %
                           (configuration.short_title, order)})

    if not patterns:
        output_objects.append(
            {'object_type': 'error_text', 'text': 'No job_id specified!'})
        return (output_objects, returnvalues.NO_SUCH_JOB_ID)

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text': '%s using flag: %s' % (op_name,
                                                                                         flag)})

    if not os.path.isdir(base_dir):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''You have not been created as a user on the %s server! Please
contact the site admins.''' % configuration.short_title})
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
        # (allowed) match....

        if not match:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '%s: You do not have any matching job IDs!' % pattern})
            status = returnvalues.CLIENT_ERROR
        else:
            filelist += match

    if sorted(flags):
        sort(filelist)

    if max_jobs > 0 and max_jobs < len(filelist):
        output_objects.append(
            {'object_type': 'text', 'text':
             'Only showing first %d of the %d matching jobs as requested'
             % (max_jobs, len(filelist))})
        filelist = filelist[:max_jobs]

    # Iterate through jobs and list details for each

    job_list = {'object_type': 'job_list', 'jobs': []}

    for filepath in filelist:

        # Extract job_id from filepath (replace doesn't modify filepath)

        mrsl_file = filepath.replace(base_dir, '')
        job_id = mrsl_file.replace('.mRSL', '')
        job_dict = unpickle(filepath, logger)
        if not job_dict:
            status = returnvalues.CLIENT_ERROR

            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'No such job: %s (could not load mRSL file %s)' %
                 (job_id, mrsl_file)})
            continue

        # Expand any job variables before use
        job_dict = expand_variables(job_dict)

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
            if name in job_dict:

                # time objects cannot be marshalled, asctime if timestamp

                try:
                    job_obj[name.lower()] = time.asctime(job_dict[name])
                except Exception as exc:

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
                arcsession = arcwrapper.Ui(home)
                arcstatus = arcsession.jobStatus(job_dict['EXE'])
                job_obj['status'] = arcstatus['status']
            except arcwrapper.ARCWrapperError as err:
                logger.error('Error retrieving ARC job status: %s' %
                             err.what())
                job_obj['status'] += '(Error: ' + err.what() + ')'
            except arcwrapper.NoProxyError as err:
                logger.error('While retrieving ARC job status: %s' %
                             err.what())
                job_obj['status'] += '(Error: ' + err.what() + ')'
            except Exception as err:
                logger.error('Error retrieving ARC job status: %s' % err)
                job_obj['status'] += '(Error during retrieval)'

        exec_histories = []
        if verbose(flags):
            if 'EXECUTE' in job_dict:
                command_line = '; '.join(job_dict['EXECUTE'])
                if len(command_line) > 256:
                    job_obj['execute'] = '%s ...' % command_line[:252]
                else:
                    job_obj['execute'] = command_line
            res_conf = job_dict.get('RESOURCE_CONFIG', {})
            if 'RESOURCE_ID' in res_conf:
                public_id = res_conf['RESOURCE_ID']
                if res_conf.get('ANONYMOUS', True):
                    public_id = anon_resource_id(public_id)
                job_obj['resource'] = public_id
            if job_dict.get('PUBLICNAME', False):
                job_obj['resource'] += ' (alias %(PUBLICNAME)s)' % job_dict
            if 'RESOURCE_VGRID' in job_dict:
                job_obj['vgrid'] = job_dict['RESOURCE_VGRID']

            if 'EXECUTION_HISTORY' in job_dict:
                counter = 0
                for history_dict in job_dict['EXECUTION_HISTORY']:
                    exec_history = \
                        {'object_type': 'execution_history'}

                    if 'QUEUED_TIMESTAMP' in history_dict:
                        exec_history['queued'] = \
                            time.asctime(history_dict['QUEUED_TIMESTAMP'
                                                      ])
                    if 'EXECUTING_TIMESTAMP' in history_dict:
                        exec_history['executing'] = \
                            time.asctime(history_dict['EXECUTING_TIMESTAMP'
                                                      ])
                    if 'PUBLICNAME' in history_dict:
                        if history_dict['PUBLICNAME']:
                            exec_history['resource'] = \
                                history_dict['PUBLICNAME']
                        else:
                            exec_history['resource'] = 'HIDDEN'
                    if 'RESOURCE_VGRID' in history_dict:
                        exec_history['vgrid'] = \
                            history_dict['RESOURCE_VGRID']
                    if 'FAILED_TIMESTAMP' in history_dict:
                        exec_history['failed'] = \
                            time.asctime(history_dict['FAILED_TIMESTAMP'
                                                      ])
                    if 'FAILED_MESSAGE' in history_dict:
                        exec_history['failed_message'] = \
                            history_dict['FAILED_MESSAGE']
                    exec_histories.append(
                        {'execution_history': exec_history, 'count': counter})
                    counter += 1
        if 'SCHEDULE_HINT' in job_dict:
            job_obj['schedule_hint'] = job_dict['SCHEDULE_HINT']
        # We should not show raw schedule_targets due to lack of anonymization
        if 'SCHEDULE_TARGETS' in job_dict:
            job_obj['schedule_hits'] = len(job_dict['SCHEDULE_TARGETS'])
        if 'EXPECTED_DELAY' in job_dict:
            # Catch None value
            if not job_dict['EXPECTED_DELAY']:
                job_obj['expected_delay'] = 0
            else:
                job_obj['expected_delay'] = int(job_dict['EXPECTED_DELAY'])

        job_obj['execution_histories'] = exec_histories

        if interactive(flags):
            job_obj['statuslink'] = {'object_type': 'link',
                                     'destination': 'fileman.py?path=%s/%s/'
                                     % (job_output_dir, job_id), 'text':
                                     'View status files'}
            job_obj['mrsllink'] = {'object_type': 'link',
                                   'destination': 'mrslview.py?job_id=%s'
                                   % job_id,
                                   'text': 'View parsed mRSL contents'}

            if 'OUTPUTFILES' in job_dict and job_dict['OUTPUTFILES']:

                # Create a single ls link with all supplied outputfiles

                path_string = ''
                for path in job_dict['OUTPUTFILES']:

                    # OUTPUTFILES is either just combo path or src dst paths

                    parts = path.split()

                    # Always take last part as destination

                    path_string += 'path=%s;' % parts[-1]

                job_obj['outputfileslink'] = {'object_type': 'link',
                                              'destination': 'ls.py?%s' %
                                              path_string,
                                              'text': 'View output files'}

            form_method = 'post'
            csrf_limit = get_csrf_limit(configuration)
            target_op = 'resubmit'
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            js_name = 'resubmit%s' % hexlify(job_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'job_id': job_id,
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            job_obj['resubmitlink'] = {'object_type': 'link',
                                       'destination':
                                       "javascript: %s();" % js_name,
                                       'text': 'Resubmit job'}

            target_op = 'jobaction'
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            js_name = 'freeze%s' % hexlify(job_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'action': 'freeze', 'job_id': job_id,
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            job_obj['freezelink'] = {'object_type': 'link',
                                     'destination':
                                     "javascript: %s();" % js_name,
                                     'text': 'Freeze job in queue'}
            js_name = 'thaw%s' % hexlify(job_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'action': 'thaw', 'job_id': job_id,
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            job_obj['thawlink'] = {'object_type': 'link',
                                   'destination':
                                   "javascript: %s();" % js_name,
                                   'text': 'Thaw job in queue'}
            js_name = 'cancel%s' % hexlify(job_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'action': 'cancel', 'job_id': job_id,
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            job_obj['cancellink'] = {'object_type': 'link',
                                     'destination':
                                     "javascript: %s();" % js_name,
                                     'text': 'Cancel job'}
            target_op = 'jobschedule'
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            js_name = 'jobschedule%s' % hexlify(job_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'job_id': job_id,
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            job_obj['jobschedulelink'] = {'object_type': 'link',
                                          'destination':
                                          "javascript: %s();" % js_name,
                                          'text':
                                          'Request schedule information'}
            target_op = 'jobfeasible'
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            js_name = 'jobfeasible%s' % hexlify(job_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'job_id': job_id,
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            job_obj['jobfeasiblelink'] = {'object_type': 'link',
                                          'destination':
                                          "javascript: %s();" % js_name,
                                          'text': 'Check job feasibility'}
            job_obj['liveiolink'] = {'object_type': 'link',
                                     'destination': 'liveio.py?job_id=%s' %
                                     job_id, 'text': 'Request live I/O'}
        job_list['jobs'].append(job_obj)
    output_objects.append(job_list)

    return (output_objects, status)
