#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mqueue - POSIX like message queue job inter-communication
# Copyright (C) 2003-2010  The MiG Project lead by Brian Vinter
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

"""POSIX like mqueue implementation using MiG user home for job inter-
communication.
"""

import os
import time
import fcntl

import shared.returnvalues as returnvalues
from shared.defaults import default_mqueue, mqueue_prefix, mqueue_empty
from shared.functional import validate_input, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.job import output_dir
from shared.useradm import client_id_dir
from shared.validstring import valid_user_path


valid_actions = ['create', 'remove', 'send', 'receive']
lock_name = 'mqueue.lock'

def signature():
    """Signature of the main function"""

    defaults = {'queue': [default_mqueue], 'action': REJECT_UNSET,
                'sessionid': [''], 'msg': ['']}
    return ['file_output', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    queue = accepted['queue'][-1]
    action = accepted['action'][-1]
    sessionid = accepted.get('sessionid', [''])[-1]
    msg = accepted.get('msg', [''])[-1]

    # Web format for cert access and no header for SID access

    if client_id:
        output_objects.append({'object_type': 'header', 'text'
                               : 'Message queue interaction'})
    else:
        output_objects.append({'object_type': 'start'})

    # Always return at least a basic file_output entry
    file_entry = {'object_type': 'file_output',
                  'lines': [],
                  'wrap_binary': True,
                  'wrap_targets': ['lines']}
    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid action "%s" (supported: %s)' % \
                               (action, ', '.join(valid_actions))})
        output_objects.append(file_entry)
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Find user home from session or certificate

    if sessionid:
        client_home = os.path.realpath(os.path.join(configuration.webserver_home,
                                                  sessionid))
        client_dir = os.path.basename(client_home)
    elif client_id:
        client_dir = client_id_dir(client_id)
    else:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Either certificate or session ID is required'
                               })
        output_objects.append(file_entry)
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name
        
    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    if not os.path.isdir(base_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'No matching session or user home!'})
        output_objects.append(file_entry)
        return (output_objects, returnvalues.CLIENT_ERROR)

    mqueue_base = os.path.join(base_dir, mqueue_prefix) + os.sep

    default_queue_dir = os.path.join(mqueue_base, default_mqueue)

    # Create mqueue base and default queue dir if missing

    if not os.path.exists(default_queue_dir):
        try:
            os.makedirs(default_queue_dir)
        except:
            pass

    queue_path = os.path.abspath(os.path.join(mqueue_base, queue))
    if not valid_user_path(queue_path, mqueue_base):
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid queue name: "%s"' % queue})
        output_objects.append(file_entry)
        return (output_objects, returnvalues.CLIENT_ERROR)

    lock_path = os.path.join(mqueue_base, lock_name)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    status = returnvalues.OK
    if action == 'create':
        try:
            os.mkdir(queue_path)
            output_objects.append({'object_type': 'text', 'text':
                                   'New "%s" queue created' % queue})
        except Exception, err:
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'Could not create "%s" queue: "%s"' % \
                                   (queue, err)})
            status = returnvalues.CLIENT_ERROR
    elif action == 'remove':
        try:
            for entry in os.listdir(queue_path):
                os.remove(os.path.join(queue_path, entry))
            os.rmdir(queue_path)
            output_objects.append({'object_type': 'text', 'text':
                                   'Existing "%s" queue removed' % queue})
        except Exception, err:
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'Could not remove "%s" queue: "%s"' % \
                                   (queue, err)})
            status = returnvalues.CLIENT_ERROR
    elif action == 'send':
        try:
            msg_path = os.path.join(queue_path, "%.0f" % time.time())
            msg_fd = open(msg_path, 'w')
            msg_fd.write(msg)
            msg_fd.close()
            output_objects.append({'object_type': 'text', 'text':
                                   'Message sent to "%s" queue' % queue})
        except Exception, err:
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'Could not send to "%s" queue: "%s"' % \
                                   (queue, err)})
            status = returnvalues.CLIENT_ERROR
    elif action == 'receive':
        try:
            now = int(time.time())
            msg, msg_path = [mqueue_empty], ''
            oldest_name, oldest_value = '', now
            for entry in os.listdir(queue_path):
                if not entry.isdigit():
                    continue
                entry_value = int(entry)
                if entry_value < oldest_value:
                    oldest_name, oldest_value = entry, entry_value
            if oldest_name:
                msg_path = os.path.join(queue_path, oldest_name)
                msg_fd = open(msg_path, 'r')
                msg = msg_fd.readlines()
                msg_fd.close()
                os.remove(msg_path)
                file_entry['path'] = os.path.basename(msg_path)
            # Update file_output entry for raw data with output_format=file
            file_entry['lines'] = msg
        except Exception, err:
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'Could not receive from "%s" queue: "%s"'
                                   % (queue, err)})
            status = returnvalues.CLIENT_ERROR
    else:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Unexpected mqueue action: "%s"' % action})
        status = returnvalues.SYSTEM_ERROR

    lock_handle.close()
    
    output_objects.append(file_entry)
    return (output_objects, returnvalues.OK)
