#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# liveoutput - [insert a few words of module description on this line]
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

"""Request job live output from resource"""

import glob
import os
import datetime

from shared.validstring import valid_user_path
from shared.fileio import unpickle, pickle
from shared.ssh import copy_file_to_resource
from shared.conf import get_resource_exe
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues
from shared.useradm import client_id_dir


def signature():
    """Signature of the main function"""

    defaults = {'job_id': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_title=False, op_header=False)
    client_dir = client_id_dir(client_id)
    output_objects.append({
        'object_type': 'title',
        'text': 'MiG live output',
        'javascript': '',
        'bodyfunctions': '',
        })
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
    job_ids = accepted['job_id']

    output_objects.append({'object_type': 'header', 'text'
                          : 'Requesting live output for %s'
                           % ', '.join(job_ids)})

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                                            client_dir)) + os.sep

    if not os.path.isdir(base_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'You have not been created as a user on the MiG server!'
                               + ' Please contact the MiG team.'})
        return (output_objects, returnvalues.USER_NOT_CREATED)

    filelist = []
    for job_id in job_ids:
        job_id = job_id.strip()

        # is job currently being executed?

        # Backward compatibility - keyword ALL should match all jobs

        if job_id == 'ALL':
            job_id = '*'

        # Check directory traversal attempts before actual handling to
        # avoid leaking information about file system layout while
        # allowing consistent error messages

        unfiltered_match = glob.glob(base_dir + job_id + '.mRSL')
        match = []
        for server_path in unfiltered_match:
            real_path = os.path.abspath(server_path)
            if not valid_user_path(real_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                # logger.warning("%s tried to %s %s outside own home! (pattern %s)" % \
                # (client_id, op_name, real_path,pattern))

                continue

            # Insert valid job files in filelist for later treatment

            match.append(real_path)

        # Now actually treat list of allowed matchings and notify if
        # no (allowed) match....

        if not match:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '%s: You do not have any matching job IDs!'
                                   % job_id})
        else:
            filelist += match

    for filepath in filelist:

        # Extract jo_id from filepath (replace doesn't modify filepath)

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

        if job_dict['STATUS'] != 'EXECUTING':
            output_objects.append({'object_type': 'text', 'text'
                                  : 'Job %s is not currently being executed! Job status: %s'
                                   % (job_id, job_dict['STATUS'])})
            continue

        last_live_update_dict = {}
        last_live_update_file = configuration.mig_system_files + os.sep\
             + job_id + '.last_live_update'
        if os.path.isfile(last_live_update_file):
            last_live_update_dict_unpickled = \
                unpickle(last_live_update_file, logger)
            if not last_live_update_dict_unpickled:
                output_objects.append({'object_type': 'error_text',
                        'text'
                        : 'Could not unpickle %s - skipping request!'
                         % last_live_update_file})
                continue

            if not last_live_update_dict_unpickled.has_key('LAST_LIVE_UPDATE_REQUEST_TIMESTAMP'
                    ):
                output_objects.append({'object_type': 'error_text',
                        'text': 'Could not find needed key in %s.'
                         % last_live_update_file})
                continue

            last_live_update_request = \
                last_live_update_dict_unpickled['LAST_LIVE_UPDATE_REQUEST_TIMESTAMP'
                    ]

            difference = datetime.datetime.now()\
                 - last_live_update_request
            try:
                min_delay = \
                    int(configuration.min_seconds_between_live_update_requests)
            except:
                min_delay = 30

            if difference.seconds < min_delay:
                output_objects.append({'object_type': 'error_text',
                        'text': 'Request not allowed, you must '
                         + 'wait at least %s seconds between live update requests!'
                         % min_delay})
                continue

        # save this request to file to avoid DoS from a client request loop.

        last_live_update_dict['LAST_LIVE_UPDATE_REQUEST_TIMESTAMP'] = \
            datetime.datetime.now()
        pickle_ret = pickle(last_live_update_dict,
                            last_live_update_file, logger)
        if not pickle_ret:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Error saving live output request timestamp to last_live_update file, request not send!'
                                  })
            continue

        # #
        # ## job is being executed right now, send live output request to frontend
        # #

        # get resource_config, needed by scp_file_to_resource
        # (status, resource_config) = get_resource_configuration(resource_home, unique_resource_name, logger)

        resource_config = job_dict['RESOURCE_CONFIG']
        (status, exe) = get_resource_exe(resource_config, job_dict['EXE'
                ], logger)
        if not status:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Could not get exe configuration for job %s'
                                   % job_id})
            continue

        local_file = '%s.update' % job_dict['LOCALJOBNAME']
        if not os.path.exists(local_file):

            # create

            try:
                filehandle = open(local_file, 'w')
                filehandle.write('content of .update file\n')
                filehandle.write('localjobname '
                                  + job_dict['LOCALJOBNAME'] + '\n')
                filehandle.write('execution_user '
                                  + exe['execution_user'] + '\n')
                filehandle.write('execution_node '
                                  + exe['execution_node'] + '\n')
                filehandle.write('execution_dir ' + exe['execution_dir']
                                  + '\n')

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
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '.update file not available on MiG server'
                                  })
            continue

        scpstatus = copy_file_to_resource(local_file, '%s.update'
                 % job_dict['LOCALJOBNAME'], resource_config, logger)
        if not scpstatus:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Error sending request for live output to ressource!'
                                  })
            continue
        else:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'Request for live output was successfully sent to the ressource!'
                                  })
            output_objects.append({'object_type': 'text', 'text'
                                  : 'The stdout and stderr files for the job will be uploaded from the executing resource and should become available in a minute using the link below.'
                                  })
            output_objects.append({'object_type': 'link', 'destination'
                                  : '/cgi-bin/ls.py?path=job_output/%s/*'
                                   % job_id, 'text': 'View status files'
                                  })

        try:
            os.remove(local_file)
        except Exception, exc:
            pass

    return (output_objects, returnvalues.OK)


