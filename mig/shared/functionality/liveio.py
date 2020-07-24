#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# liveio - communication with running jobs
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Request job live input or output from resource"""

import glob
import os
import datetime
from urllib import quote

from shared import returnvalues
from shared.base import client_id_dir
from shared.conf import get_resource_exe
from shared.defaults import all_jobs, job_output_dir, csrf_field
from shared.fileio import unpickle, pickle
from shared.functional import validate_input_and_cert
from shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from shared.init import initialize_main_variables, find_entry
from shared.ssh import copy_file_to_resource
from shared.validstring import valid_user_path


interactive_actions = ['interactive', '']
get_actions = interactive_actions
post_actions = ['put', 'send', 'output', 'get', 'receive', 'input']
valid_actions = get_actions + post_actions


def signature():
    """Signature of the main function"""

    defaults = {'job_id': [], 'action': ['interactive'], 'src': [],
                'dst': ['']}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    status = returnvalues.OK
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

    job_ids = accepted['job_id']
    action = accepted['action'][-1]
    src = accepted['src']
    dst = accepted['dst'][-1]

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s live I/O' % configuration.short_title
    add_import, add_init, add_ready = '', '', ''
    add_init += '''
    var fields = 1;
    var max_fields = 20;
    var src_input = "<input class='fillwidth' type=text name=src value='' /><br />";
    function addSource() {
        if (fields < max_fields) {
            $("#srcfields").append(src_input);
            fields += 1;
        } else {
            alert("Maximum " + max_fields + " source fields allowed!");
        }
    }
    '''
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append(
        {'object_type': 'header', 'text': 'Request live communication with jobs'})

    if not configuration.site_enable_jobs:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Job execution is not enabled on this system'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid action "%s" (supported: %s)' %
                               (action, ', '.join(valid_actions))})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action in post_actions:
        if not safe_handler(configuration, 'post', op_name, client_id,
                            get_csrf_limit(configuration), accepted):
            output_objects.append(
                {'object_type': 'error_text', 'text': '''Only accepting
                CSRF-filtered POST requests to prevent unintended updates'''
                 })
            return (output_objects, returnvalues.CLIENT_ERROR)

    if not job_ids or action in interactive_actions:
        job_id = ''
        if job_ids:
            job_id = job_ids[-1]
        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        fill_helpers = {'job_id': job_id,
                        'form_method': form_method,
                        'csrf_field': csrf_field,
                        'csrf_limit': csrf_limit}
        target_op = 'liveio'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

        output_objects.append({'object_type': 'text', 'text': '''
Fill in the live I/O details below to request communication with a running
job.
Job ID can be a full ID or a wild card pattern using "*" and "?" to match one
or more of your job IDs.
Use send output without source and destination paths to request upload of the
default stdio files from the job on the resource to the associated job_output
directory in your MiG home.
Destination is a always handled as a directory path to put source files into.
Source and destination paths are always taken relative to the job execution
directory on the resource and your MiG home respectively.
'''})
        html = '''
<table class="liveio">
<tr>
<td>
<form method="%(form_method)s" action="%(target_op)s.py">
<table class="liveio">
<tr><td class=centertext>
</td></tr>
<tr><td>
Action:<br />
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type=radio name=action checked value="send" />send output
<input type=radio name=action value="get" />get input
</td></tr>
<tr><td>
Job ID:<br />
<input class="fillwidth" type=text name=job_id value="%(job_id)s" />
</td></tr>
<tr><td>
Source path(s):<br />
<div id="srcfields">
<input class="fillwidth" type=text name=src value="" /><br />
</div>
<input id="addsrcbutton" type="button" onclick="addSource(); return false;"
    value="Add another source field" />
</td></tr>
<tr><td>
Destination path:<br />
<input class="fillwidth" type=text name=dst value="" />
</td></tr>
<tr><td>
<input type="submit" value="Send request" />
</td></tr>
</table>
</form>
</td>
</tr>
</table>
''' % fill_helpers
        output_objects.append({'object_type': 'html_form', 'text': html})
        output_objects.append({'object_type': 'text', 'text': '''
Further live job control is avalable through your personal message queues.
They provide a basic interface for centrally storing messages under your grid
account and can be used to pass messages between jobs or for orchestrating
jobs before and during execution.
'''
                               })
        output_objects.append({'object_type': 'link', 'destination':
                               'mqueue.py',
                               'text': 'Message queue interface'})
        return (output_objects, returnvalues.OK)
    elif action in ['get', 'receive', 'input']:
        action = 'get'
        action_desc = 'will be downloaded to the job on the resource'
    elif action in ['put', 'send', 'output']:
        action = 'send'
        action_desc = 'will be uploaded from the job on the resource'
    else:
        output_objects.append(
            {'object_type': 'error_text', 'text': 'Invalid live io action: %s' % action})
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'text', 'text': 'Requesting live I/O for %s'
                           % ', '.join(job_ids)})

    if action == 'get' and (not src or not dst):
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'src and dst parameters required for live input'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Automatic fall back to stdio files if output with no path provided

    if src:
        src_text = 'The files ' + ' '.join(src)
    else:
        src_text = 'The job stdio files'

    if dst:
        dst_text = 'the ' + dst + ' directory'
    else:
        dst_text = 'the corresponding job_output directory'

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = \
        os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                                     client_dir)) + os.sep

    filelist = []
    for job_id in job_ids:
        job_id = job_id.strip()

        # is job currently being executed?

        # Backward compatibility - all_jobs keyword should match all jobs

        if job_id == all_jobs:
            job_id = '*'

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        unfiltered_match = glob.glob(base_dir + job_id + '.mRSL')
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.warning("%s tried to %s restricted path %s ! (%s)" %
                               (client_id, op_name, abs_path, job_id))

                continue

            # Insert valid job files in filelist for later treatment

            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match....

        if not match:
            output_objects.append(
                {'object_type': 'error_text', 'text': '%s: You do not have any matching job IDs!' % job_id})
        else:
            filelist += match

    for filepath in filelist:

        # Extract job_id from filepath (replace doesn't modify filepath)

        mrsl_file = filepath.replace(base_dir, '')
        job_id = mrsl_file.replace('.mRSL', '')
        job_dict = unpickle(filepath, logger)
        if not job_dict:
            status = returnvalues.CLIENT_ERROR
            output_objects.append(
                {'object_type': 'error_text', 'text': ('You can only list status of your own jobs. '
                                                       'Please verify that you submitted the mRSL file '
                                                       'with job id "%s" (Could not unpickle mRSL file %s)'
                                                       ) % (job_id, filepath)})
            continue

        if job_dict['STATUS'] != 'EXECUTING':
            output_objects.append(
                {'object_type': 'text', 'text': 'Job %s is not currently being executed! Job status: %s'
                 % (job_id, job_dict['STATUS'])})
            continue

        if job_dict['UNIQUE_RESOURCE_NAME'] == 'ARC':
            output_objects.append(
                {'object_type': 'text', 'text': 'Job %s is submitted to ARC, details are not available!'
                 % job_id})
            continue

        last_live_update_dict = {}
        last_live_update_file = configuration.mig_system_files + os.sep\
            + job_id + '.last_live_update'
        if os.path.isfile(last_live_update_file):
            last_live_update_dict_unpickled = \
                unpickle(last_live_update_file, logger)
            if not last_live_update_dict_unpickled:
                output_objects.append({'object_type': 'error_text',
                                       'text': 'Could not unpickle %s - skipping request!'
                                       % last_live_update_file})
                continue

            if not last_live_update_dict_unpickled.has_key(
                    'LAST_LIVE_UPDATE_REQUEST_TIMESTAMP'):
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': 'Could not find needed key in %s.'
                     % last_live_update_file})
                continue

            last_live_update_request = \
                last_live_update_dict_unpickled['LAST_LIVE_UPDATE_REQUEST_TIMESTAMP'
                                                ]

            difference = datetime.datetime.now() - last_live_update_request
            try:
                min_delay = \
                    int(configuration.min_seconds_between_live_update_requests)
            except:
                min_delay = 30

            if difference.seconds < min_delay:
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': ('Request not allowed, you must wait at least '
                              '%s seconds between live update requests!'
                              ) % min_delay})
                continue

        # save this request to file to avoid DoS from a client request loop.

        last_live_update_dict['LAST_LIVE_UPDATE_REQUEST_TIMESTAMP'] = \
            datetime.datetime.now()
        pickle_ret = pickle(last_live_update_dict,
                            last_live_update_file, logger)
        if not pickle_ret:
            output_objects.append(
                {'object_type': 'error_text', 'text': 'Error saving live io request timestamp to last_live_update '
                 'file, request not sent!'})
            continue

        # #
        # ## job is being executed right now, send live io request to frontend
        # #

        # get resource_config, needed by scp_file_to_resource
        # (res_status, resource_config) = get_resource_configuration(
        #    resource_home, unique_resource_name, logger)

        resource_config = job_dict['RESOURCE_CONFIG']
        (res_status, exe) = get_resource_exe(resource_config, job_dict['EXE'],
                                             logger)
        if not res_status:
            output_objects.append(
                {'object_type': 'error_text', 'text': 'Could not get exe configuration for job %s' % job_id})
            continue

        local_file = '%s.%supdate' % (job_dict['LOCALJOBNAME'], action)
        if not os.path.exists(local_file):

            # create

            try:
                filehandle = open(local_file, 'w')
                filehandle.write('job_id '
                                 + job_dict['JOB_ID'] + '\n')
                filehandle.write('localjobname '
                                 + job_dict['LOCALJOBNAME'] + '\n')
                filehandle.write('execution_user '
                                 + exe['execution_user'] + '\n')
                filehandle.write('execution_node '
                                 + exe['execution_node'] + '\n')
                filehandle.write('execution_dir ' + exe['execution_dir']
                                 + '\n')
                filehandle.write('target liveio\n')

                # Leave defaults src and dst to FE script if not provided

                if src:
                    filehandle.write('source ' + ' '.join(src) + '\n')
                if dst:
                    filehandle.write('destination ' + dst + '\n')

                # Backward compatible test for shared_fs - fall back to scp

                if exe.has_key('shared_fs') and exe['shared_fs']:
                    filehandle.write('copy_command cp\n')
                    filehandle.write('copy_frontend_prefix \n')
                    filehandle.write('copy_execution_prefix \n')
                else:
                    filehandle.write('copy_command scp -B\n')
                    filehandle.write('copy_frontend_prefix ${frontend_user}@${frontend_node}:\n'
                                     )
                    filehandle.write('copy_execution_prefix ${execution_user}@${execution_node}:\n'
                                     )

                filehandle.write('### END OF SCRIPT ###\n')
                filehandle.close()
            except Exception, exc:
                pass

        if not os.path.exists(local_file):
            output_objects.append(
                {'object_type': 'error_text', 'text': '.%supdate file not available on %s server' %
                 (action, configuration.short_title)})
            continue

        scp_status = copy_file_to_resource(local_file, '%s.%supdate'
                                           % (job_dict['LOCALJOBNAME'], action), resource_config, logger)
        if not scp_status:
            output_objects.append(
                {'object_type': 'error_text', 'text': 'Error sending request for live io to resource!'})
            continue
        else:
            output_objects.append(
                {'object_type': 'text', 'text': 'Request for live io was successfully sent to the resource!'
                 })
            output_objects.append(
                {'object_type': 'text', 'text': '%s %s and should become available in %s in a minute.' %
                 (src_text, action_desc, dst_text)
                 })
            if action == 'send':
                if not dst:
                    target_path = '%s/%s/*' % (job_output_dir, job_id)
                else:
                    target_path = dst
                enc_url = 'ls.py?path=%s' % quote(target_path)
                output_objects.append({'object_type': 'link', 'destination':
                                       enc_url, 'text': 'View uploaded files'})
            else:
                enc_url = 'ls.py?path='
                enc_url += ';path='.join([quote(i) for i in src])
                output_objects.append({'object_type': 'link', 'destination':
                                       enc_url, 'text':
                                       'View files for download'})

        try:
            os.remove(local_file)
        except Exception, exc:
            pass

    return (output_objects, returnvalues.OK)
