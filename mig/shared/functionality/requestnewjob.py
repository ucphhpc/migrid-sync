#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# requestnewjob - Request a new job to execute on resource
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

"""Handle request for a job from a resource"""

import os
import sys
import fcntl
import time

import shared.returnvalues as returnvalues
from shared.cgishared import init_cgiscript_possibly_with_cert
from shared.conf import get_resource_configuration
from shared.fileio import send_message_to_grid_script
from shared.findtype import is_resource
from shared.functional import validate_input, REJECT_UNSET
from shared.httpsclient import check_source_ip
from shared.init import initialize_main_variables
from shared.validstring import valid_dir_input


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET,
                'exe': REJECT_UNSET, 'cputime': ['10000'],
                'nodecount': ['1'], 'localjobname': REJECT_UNSET, 'sandboxkey': [''],
                'execution_delay': ['0'], 'exe_pgid': ['0']}
    return ['text', defaults]

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_title=False,
                                  op_menu=client_id)

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    remote_ip = str(os.getenv('REMOTE_ADDR'))

    unique_resource_name = accepted['unique_resource_name'][-1]
    exe = accepted['exe'][-1]
    cputime = int(accepted['cputime'][-1])
    nodecount = int(accepted['nodecount'][-1])
    localjobname = accepted['localjobname'][-1]
    sandboxkey = accepted['sandboxkey'][-1]
    execution_delay = int(accepted['execution_delay'][-1])
    exe_pgid = int(accepted['exe_pgid'][-1])

    status = returnvalues.OK


    # No header and footer here
    output_objects.append({'object_type': 'start'})
    output_objects.append({'object_type': 'script_status', 'text': ''})
        
    # Please note that base_dir must end in slash to avoid access to other
    # resource dirs when own name is a prefix of another resource name
    
    base_dir = os.path.abspath(os.path.join(configuration.resource_home,
                                            unique_resource_name)) + os.sep

    if not is_resource(unique_resource_name, configuration.resource_home):
        output_objects.append(
            {'object_type': 'error_text', 'text': 
             "Failure: You must be an owner of '%s' to get the PGID!" % \
             unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # is_resource incorporates unique_resource_name verification - no need to
    # specifically check for illegal directory traversal on that variable.

    (load_status, resource_conf) = \
                  get_resource_configuration(configuration.resource_home,
                                             unique_resource_name, logger)
    if not load_status:
        logger.error("Invalid requestnewjob - no resouce_conf for: %s : %s" % \
                     (unique_resource_name, resource_conf))
        output_objects.append({'object_type': 'error_text', 'text':
                               'invalid request: no such resource!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Check that resource address matches request source to make DoS harder
    proxy_fqdn = resource_conf.get('FRONTENDPROXY', None)
    try:
        check_source_ip(remote_ip, unique_resource_name, proxy_fqdn)
    except ValueError, vae:
        logger.error("Invalid requestnewjob: %s (%s)" % (vae, accepted))
        output_objects.append({'object_type': 'error_text', 'text':
                               'invalid request: %s' % vae})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if resource_conf.get('SANDBOX', False):
        if sandboxkey == '':
            logger.error("Missing sandboxkey for sandbox resource: %s" % \
                         unique_resource_name)
            output_objects.append({'object_type': 'error_text', 'text':
                               'sandbox must set sandboxkey in job requests!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        # resource is a sandbox and a sandboxkey was received
        if resource_conf['SANDBOXKEY'] != sandboxkey:
            logger.error("Incorrect sandboxkey for sandbox resource: %s : %s" \
                         % (unique_resource_name, sandboxkey))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'sandbox provided an invalid sandboxkey!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # TODO: add full session ID check here

    # If the server is under heavy usage, requestjobs might come too fast and
    # thereby make the usage even heavier. The resource request a new job again
    # because the requestjob process is finished, resulting in more load. A
    # resource should not be able to have more than one job request at a time.
    # A "jobrequest_pending" file in the resource's home directory means that
    # a requestnewjob is processed. The file is also deleted when a resource
    # is started. This locking by file is not good if the MiG server runs on a
    # NFS file system. The lock file contains a timestamp used to autoexpire
    # old locks if a job wasn't handed out within the requested cputime.

    lock_file = os.path.abspath(os.path.join(base_dir, 'jobrequest_pending.%s' % exe))
    filehandle = None
    now = time.time()
    try:
        lock_until = now + min(300.0, float(cputime))
    except Exception:
        logger.error('invalid cputime in requestnewjob: %s' % cputime)
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'invalid cputime: %s - must be a number!' % cputime})
        return (output_objects, returnvalues.CLIENT_ERROR)

    try:
        filehandle = open(lock_file, 'r+')
    except IOError, ioe:
        output_objects.append(
            {'object_type': 'text', 'text':
             'No jobrequest_pending.%s lock found - creating one' % exe})

    if filehandle:
        try:
            fcntl.flock(filehandle.fileno(), fcntl.LOCK_EX)
            filehandle.seek(0, 0)

            lock_content = filehandle.read()
            if lock_content:
                try:
                    expire_time = float(lock_content)
                except Exception:

                    # Old expire file - force lock to expire

                    expire_time = 0.0

                if now < expire_time:
                    logger.error('invalid cputime in requestnewjob: %s' % cputime)
                    output_objects.append(
                        {'object_type': 'error_text', 'text':
                         'requestnewjob is locked until last requestnewjob for'
                         'this exe (%s) has returned.' % exe})
                    return (output_objects, returnvalues.CLIENT_ERROR)
                else:
                    logger.info('requestnewjob found expired lock '
                                '(%.2f < %.2f) - allowing new request.' % \
                                (now, expire_time))
            filehandle.seek(0, 0)
            filehandle.write('%.2f' % lock_until)
            filehandle.close()
        except IOError, ioe:
            logger.error('Could not get exclusive lock in requestnewjob')
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '''Could not get exclusive lock. Your last job request for %s
has been received on the %s server. The job should be available shortly. If you
receive this message often, please increase the timeout for job requests.''' \
                 % (exe, configuration.short_title)})
            return (output_objects, returnvalues.CLIENT_ERROR)
    else:

        # create file

        try:
            filehandle = open(lock_file, 'w')
            fcntl.flock(filehandle.fileno(), fcntl.LOCK_EX)
            filehandle.seek(0, 0)
            filehandle.write('%.2f' % lock_until)
            filehandle.close()
        except IOError, ioe:
            logger.error('Failed to create jobrequest_pending lock: %s' % ioe)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Failed to create jobrequest_pending lock!'})
            return (output_objects, returnvalues.ERROR)

    # Tell "grid_script" that the resource requests a job

    message = 'RESOURCEREQUEST %s %s %s %s %s %s %s\n' % (
        exe,
        unique_resource_name,
        cputime,
        nodecount,
        localjobname,
        execution_delay,
        exe_pgid,
        )
    if not send_message_to_grid_script(message, logger, configuration):
        logger.error('could not send resource request for %s to grid_script!'
                     % unique_resource_name)
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Fatal error: could not handle resource job request'})
        return (output_objects, returnvalues.ERROR)

    output_objects.append(
            {'object_type': 'text', 'text': 'REQUESTNEWJOB OK. The job will '
             'be sent to the resource: %s.%s %s %s (sandboxkey: %s)'
             % (unique_resource_name, exe, str(exe_pgid),
                os.getenv('REMOTE_ADDR'), sandboxkey)})
    return (output_objects, status)





