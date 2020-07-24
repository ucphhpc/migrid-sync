#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cleanexe - Back end to clean one or more resource exe units
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

from shared import returnvalues
from shared.conf import get_all_exe_names
from shared.findtype import is_owner
from shared.resadm import clean_resource_exe, stop_resource_exe
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.worker import Worker, throttle_max_concurrent


def signature():
    """Signature of the main function"""

    defaults = {
        'unique_resource_name': REJECT_UNSET,
        'exe_name': [],
        'all': [''],
        'parallel': [''],
        }
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    output_objects.append({'object_type': 'text', 'text'
                          : '--------- Trying to Clean exe ----------'})
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

    unique_resource_name = accepted['unique_resource_name'][-1]
    exe_name_list = accepted['exe_name']
    all = accepted['all'][-1].lower() == 'true'
    parallel = accepted['parallel'][-1].lower() == 'true'

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Failure: You must be an owner of '
                               + unique_resource_name
                               + ' to clean the exe!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    exit_status = returnvalues.OK

    if all:
        exe_name_list = get_all_exe_names(unique_resource_name)

    # take action based on supplied list of exes

    if len(exe_name_list) == 0:
        output_objects.append({'object_type': 'text', 'text'
                              : "No exes specified and 'all' argument not set to true: Nothing to do!"
                              })

    workers = []
    task_list = []
    for exe_name in exe_name_list:
        task = Worker(target=stop_resource_exe,
                      args=(unique_resource_name, exe_name,
                      configuration.resource_home, logger))
        workers.append((exe_name, [task]))
        task_list.append(task)
        throttle_max_concurrent(task_list)
        task.start()
        if not parallel:
            task.join()

    # Complete each stop thread before launching corresponding clean threads

    for (exe_name, task_list) in workers:

        # We could optimize with non-blocking join here but keep it simple for now
        # as final result will need to wait for slowest member anyway

        task_list[0].join()
        task = Worker(target=clean_resource_exe,
                      args=(unique_resource_name, exe_name,
                      configuration.resource_home, logger))
        task_list.append(task)
        throttle_max_concurrent(task_list)
        task.start()
        if not parallel:
            task.join()

    for (exe_name, task_list) in workers:
        (status, msg) = task_list[0].finish()
        output_objects.append({'object_type': 'header', 'text'
                              : 'Clean exe output:'})
        if not status:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Problems stopping exe during clean: %s'
                                   % msg})

        (status2, msg2) = task_list[1].finish()
        if not status2:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Problems cleaning exe during clean: %s'
                                   % msg2})
            exit_status = returnvalues.SYSTEM_ERROR
        if status and status2:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'Clean exe success: Stop output: %s ; Clean output: %s'
                                   % (msg, msg2)})

    return (output_objects, exit_status)


