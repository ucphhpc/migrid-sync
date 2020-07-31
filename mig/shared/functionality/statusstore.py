#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# statusstore - Back end to get status for one or more resource store units
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

from __future__ import absolute_import
from mig.shared import returnvalues
from mig.shared.conf import get_all_store_names
from mig.shared.findtype import is_owner
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.init import initialize_main_variables
from mig.shared.resadm import status_resource_store
from mig.shared.worker import Worker


def signature():
    """Signature of the main function"""

    defaults = {
        'unique_resource_name': REJECT_UNSET,
        'store_name': [],
        'all': [''],
        'parallel': [''],
        }
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    output_objects.append({'object_type': 'text', 'text'
                          : '--------- Trying to STATUS store ----------'
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
    unique_resource_name = accepted['unique_resource_name'][-1]
    store_name_list = accepted['store_name']
    all = accepted['all'][-1].lower() == 'true'
    parallel = accepted['parallel'][-1].lower() == 'true'

    if not is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Failure: You must be an owner of '
                               + unique_resource_name
                               + ' to get status for the store!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    exit_status = returnvalues.OK

    if all:
        store_name_list = get_all_store_names(unique_resource_name)

    # take action based on supplied list of stores

    if len(store_name_list) == 0:
        output_objects.append({'object_type': 'text', 'text'
                              : "No stores specified and 'all' argument not set to true: Nothing to do!"
                              })

    workers = []
    for store_name in store_name_list:
        task = Worker(target=status_resource_store,
                      args=(unique_resource_name, store_name,
                      configuration.resource_home, logger))
        workers.append((store_name, [task]))
        task.start()
        if not parallel:
            task.join()

    for (store_name, task_list) in workers:
        (status, msg) = task_list[0].finish()
        output_objects.append({'object_type': 'header', 'text'
                              : 'Status store'})
        if not status:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Problems getting store status: %s'
                                   % msg})
            exit_status = returnvalues.SYSTEM_ERROR
        else:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'Status command run, output: %s'
                                   % msg})
    return (output_objects, exit_status)


