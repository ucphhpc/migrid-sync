#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mqueue - POSIX like message queue job inter-communication
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

"""POSIX like mqueue implementation using MiG user home for job inter-
communication.
"""

from __future__ import absolute_import

import os
import time
import fcntl

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import default_mqueue, mqueue_prefix, mqueue_empty, \
    csrf_field
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.validstring import valid_user_path

get_actions = ['interactive', 'listqueues', 'listmessages', 'show']
post_actions = ['create', 'remove', 'send', 'receive']
valid_actions = get_actions + post_actions
lock_name = 'mqueue.lock'


def signature():
    """Signature of the main function"""

    defaults = {'queue': [default_mqueue], 'action': ['interactive'],
                'iosessionid': [''], 'msg': [''], 'msg_id': ['']}
    return ['file_output', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    queue = accepted['queue'][-1]
    action = accepted['action'][-1]
    iosessionid = accepted['iosessionid'][-1]
    msg = accepted['msg'][-1]
    msg_id = accepted['msg_id'][-1]

    # Web format for cert access and no header for SID access

    if client_id:
        output_objects.append(
            {'object_type': 'header', 'text': 'Message queue %s' % action})
    else:
        output_objects.append({'object_type': 'start'})

    # Always return at least a basic file_output entry

    file_entry = {'object_type': 'file_output',
                  'lines': [],
                  'wrap_binary': True,
                  'wrap_targets': ['lines']}

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid action %r (supported: %s)' %
                               (action, ', '.join(valid_actions))})
        output_objects.append(file_entry)
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action in post_actions:
        if not safe_handler(configuration, 'post', op_name, client_id,
                            get_csrf_limit(configuration), accepted):
            output_objects.append(
                {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Find user home from session or certificate

    if iosessionid:
        client_home = os.path.realpath(os.path.join(configuration.webserver_home,
                                                    iosessionid))
        client_dir = os.path.basename(client_home)
    elif client_id:
        client_dir = client_id_dir(client_id)
    else:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Either certificate or session ID is required'})
        output_objects.append(file_entry)
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    if not os.path.isdir(base_dir):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'No matching session or user home!'})
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

    # IMPORTANT: path must be expanded to abs for proper chrooting
    queue_path = os.path.abspath(os.path.join(mqueue_base, queue))
    if not valid_user_path(configuration, queue_path, mqueue_base):
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid queue name: %r' % queue})
        output_objects.append(file_entry)
        return (output_objects, returnvalues.CLIENT_ERROR)

    lock_path = os.path.join(mqueue_base, lock_name)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    status = returnvalues.OK
    if action == "interactive":
        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        fill_helpers = {'queue': queue,
                        'msg': msg,
                        'form_method': form_method,
                        'csrf_field': csrf_field,
                        'csrf_limit': csrf_limit, }
        target_op = 'mqueue'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

        output_objects.append({'object_type': 'text', 'text': '''
Fill in the fields below to control and access your personal message queues.
Jobs can receive from and send to the message queues during execution, and use
them as a means of job inter-communication. Expect message queue operations to
take several seconds on the resources, however. That is, use it for tasks like
orchestrating long running jobs, and not for low latency communication.
'''})
        html = '''
<form name="mqueueform" method="%(form_method)s" action="%(target_op)s.py">
<table class="mqueue">
<tr><td class=centertext>
</td></tr>
<tr><td>
Action:<br />
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type=radio name=action value="create" onclick="javascript: document.mqueueform.queue.disabled=false; document.mqueueform.msg.disabled=true;" />create queue
<input type=radio name=action checked value="send" onclick="javascript: document.mqueueform.queue.disabled=false; document.mqueueform.msg.disabled=false;" />send message to queue
<input type=radio name=action value="receive" onclick="javascript: document.mqueueform.queue.disabled=false; document.mqueueform.msg.disabled=true;" />receive message from queue
<input type=radio name=action value="remove" onclick="javascript: document.mqueueform.queue.disabled=false; document.mqueueform.msg.disabled=true;" />remove queue
<input type=radio name=action value="listqueues" onclick="javascript: document.mqueueform.queue.disabled=true; document.mqueueform.msg.disabled=true;" />list queues
<input type=radio name=action value="listmessages" onclick="javascript: document.mqueueform.queue.disabled=false; document.mqueueform.msg.disabled=true;" />list messages
<input type=radio name=action value="show" onclick="javascript: document.mqueueform.queue.disabled=false; document.mqueueform.msg.disabled=true;" />show message
</td></tr>
<tr><td>
Queue:<br />
<input class="fillwidth" type=text name=queue value="%(queue)s" />
</td></tr>
<tr><td>
<div id="msgfieldf">
<input class="fillwidth" type=text name=msg value="%(msg)s" /><br />
</div>
</td></tr>
<tr><td>
<input type="submit" value="Apply" />
</td></tr>
</table>
</form>
''' % fill_helpers
        output_objects.append({'object_type': 'html_form', 'text': html})
        output_objects.append({'object_type': 'text', 'text': '''
Further live job control is avalable through the live I/O interface.
They provide a basic interface for centrally managing input and output files
for active jobs.
'''
                               })
        output_objects.append({'object_type': 'link', 'destination':
                               'liveio.py',
                               'text': 'Live I/O interface'})
        return (output_objects, returnvalues.OK)
    elif action == 'create':
        try:
            os.mkdir(queue_path)
            output_objects.append({'object_type': 'text', 'text':
                                   'New %r queue created' % queue})
        except Exception as err:
            logger.error("create mqueue %s failed: %s" % (queue_path, err))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create %r queue' % queue})
            status = returnvalues.CLIENT_ERROR
    elif action == 'remove':
        try:
            for entry in os.listdir(queue_path):
                os.remove(os.path.join(queue_path, entry))
            os.rmdir(queue_path)
            output_objects.append({'object_type': 'text', 'text':
                                   'Existing %r queue removed' % queue})
        except Exception as err:
            logger.error("remove mqueue %s failed: %s" % (queue_path, err))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not remove %r queue' % queue})
            status = returnvalues.CLIENT_ERROR
    elif action == 'send':
        try:
            if not msg_id:
                msg_id = "%.0f" % time.time()
            msg_path = os.path.join(queue_path, msg_id)
            # TODO: port to write_file
            msg_fd = open(msg_path, 'w')
            msg_fd.write(msg)
            msg_fd.close()
            output_objects.append({'object_type': 'text', 'text':
                                   'Message sent to %r queue' % queue})
        except Exception as err:
            logger.error("write to mqueue %s failed: %s" % (queue_path, err))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not send to %r queue' % queue})
            status = returnvalues.CLIENT_ERROR
    elif action == 'receive':
        try:
            if not msg_id:
                messages = os.listdir(queue_path)
                messages.sort()
                if messages:
                    msg_id = messages[0]
            if msg_id:
                msg_path = os.path.join(queue_path, msg_id)
                # TODO: port to read_file_lines
                msg_fd = open(msg_path, 'r')
                message = msg_fd.readlines()
                msg_fd.close()
                os.remove(msg_path)
                file_entry['path'] = os.path.basename(msg_path)
            else:
                message = [mqueue_empty]
            # Update file_output entry for raw data with output_format=file
            file_entry['lines'] = message
        except Exception as err:
            logger.error("read from mqueue %s failed: %s" % (queue_path, err))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not receive from %r queue' % queue})
            status = returnvalues.CLIENT_ERROR
    elif action == 'show':
        try:
            if not msg_id:
                messages = os.listdir(queue_path)
                messages.sort()
                if messages:
                    msg_id = messages[0]
            if msg_id:
                msg_path = os.path.join(queue_path, msg_id)
                msg_fd = open(msg_path, 'r')
                message = msg_fd.readlines()
                msg_fd.close()
                file_entry['path'] = os.path.basename(msg_path)
            else:
                message = [mqueue_empty]
            # Update file_output entry for raw data with output_format=file
            file_entry['lines'] = message
        except Exception as err:
            logger.error("show %s from mqueue %s failed: %s" % (msg_id,
                                                                queue_path,
                                                                err))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not show %s from %r queue' %
                                   (msg_id, queue)})
            status = returnvalues.CLIENT_ERROR
    elif action == 'listmessages':
        try:
            messages = os.listdir(queue_path)
            messages.sort()
            output_objects.append({'object_type': 'list', 'list': messages})
        except Exception as err:
            logger.error("list on mqueue %s failed: %s" % (queue_path, err))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not list %r queue messages' % queue})
            status = returnvalues.CLIENT_ERROR
    elif action == 'listqueues':
        try:
            queues = [i for i in os.listdir(mqueue_base) if
                      os.path.isdir(os.path.join(mqueue_base, i))]
            queues.sort()
            output_objects.append({'object_type': 'list', 'list': queues})
        except Exception as err:
            logger.error("list mqueues failed: %s" % err)
            output_objects.append(
                {'object_type': 'error_text', 'text': 'Could not list queues'})
            status = returnvalues.CLIENT_ERROR
    else:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Unexpected mqueue action: %r' % action})
        status = returnvalues.SYSTEM_ERROR

    lock_handle.close()

    output_objects.append(file_entry)
    output_objects.append({'object_type': 'link',
                           'destination': 'mqueue.py?queue=%s&msg=%s' %
                           (queue, msg),
                           'text': 'Back to message queue interaction'})
    return (output_objects, returnvalues.OK)
