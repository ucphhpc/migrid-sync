#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# statusexe - Back end to get status for one or more resource exe units
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

import cgi
import os
import sys

from shared.conf import get_all_exe_names
from shared.findtype import is_owner
from shared.resadm import status_resource_exe
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues
from shared.worker import Worker


def signature():
    """Signature of the main function"""
    defaults = {
        'unique_resource_name': REJECT_UNSET,
        'exe_name': [],
        'all': [''],
        'parallel': [''],
        }
    return ['text', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()
    output_objects.append({'object_type': 'text', 'text'
                          : '--------- Trying to STATUS exe ----------'
                          })

    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        cert_name_no_spaces,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    unique_resource_name = accepted['unique_resource_name'][-1]
    exe_name_list = accepted['exe_name']
    all = (accepted['all'][-1].lower() == 'true')
    parallel = (accepted['parallel'][-1].lower() == 'true')

    if not is_owner(cert_name_no_spaces, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Failure: You must be an owner of '
                               + unique_resource_name
                               + ' to get status for the exe!'})
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
    for exe_name in exe_name_list:
        task = Worker(target=status_resource_exe, args=(unique_resource_name,
                                                        exe_name,
                                                        configuration.resource_home,
                                                        logger))
        workers.append((exe_name, [task]))
        task.start()
        if not parallel:
            task.join()
        
    for (exe_name, task_list) in workers:
        (status, msg) = task_list[0].finish()
        output_objects.append({'object_type': 'header', 'text'
                              : 'Status exe'})
        if not status:
            output_objects.append({'object_type': 'error_text', 'text'
                    : 'Problems getting exe status: %s' % msg})
            exit_status = returnvalues.SYSTEM_ERROR
        else:
            output_objects.append({'object_type': 'text', 'text'
                    : 'Status command run, output: %s' % msg})
    return (output_objects, exit_status)


