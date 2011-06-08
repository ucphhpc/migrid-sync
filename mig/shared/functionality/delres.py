#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# delres - Deletes a resource
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

"""Deletion of a resource"""

import os
import fcntl

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables, find_entry
from shared.resource import resource_owners
from shared.vgridaccess import unmap_resource


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET}
    return ['resource_info', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

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

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    resource_list = accepted['unique_resource_name']
    res_name = resource_list.pop()

    res_dir = os.path.join(configuration.resource_home, res_name)

    # Prevent unauthorized access
    
    (owner_status, owner_list) = resource_owners(configuration,
                                                 unique_resource_name)
    if not owner_status:
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : "Could not look up '%s' owners - no such resource?" % res_name
             })
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif client_id not in owner_list:
        logger.warning('user %s tried to delete resource "%s" not owned' % \
                       (client_id, res_name))
        output_objects.append({'object_type': 'error_text', 'text'
                               : "You can't delete '%s' - you don't own it!"
                               % res_name})
        output_objects.append({'object_type': 'link', 'destination':
                               'resman.py', 'class': 'infolink', 'title':
                               'Show resources', 'text': 'Show resources'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Locking the access to resources and vgrids.
    lock_path_vgrid = os.path.join(configuration.resource_home, "vgrid.lock")
    lock_handle_vgrid = open(lock_path_vgrid, 'a')

    fcntl.flock(lock_handle_vgrid.fileno(), fcntl.LOCK_EX)

    lock_path_res = os.path.join(configuration.resource_home, "resource.lock")
    lock_handle_res = open(lock_path_res, 'a')

    fcntl.flock(lock_handle_res.fileno(), fcntl.LOCK_EX)

    # Only resources that are down may be deleted.
    # A "FE.PGID" file with a PGID in the resource's home directory means that
    # the FE is running.

    pgid_path = os.path.join(res_dir, 'FE.PGID')
    fe_running = True
    try:

        # determine if fe runs by finding out if pgid is numerical

        pgid_file = open(pgid_path, 'r')
        fcntl.flock(pgid_file, fcntl.LOCK_EX)
        pgid = pgid_file.readline().strip()
        fcntl.flock(pgid_file, fcntl.LOCK_UN)
        pgid_file.close()
        if not pgid.isdigit():
            raise Exception('FE already stopped')
    except:
        fe_running = False

    if fe_running:
        output_objects.append({'object_type': 'error_text', 'text'
                               : "Can't delete the running resource %s!"
                               % res_name})
        output_objects.append({'object_type': 'link', 'destination':
                               'resman.py', 'class': 'infolink', 'title':
                               'Show resources', 'text': 'Show resources'})
        lock_handle_vgrid.close()
        lock_handle_res.close()
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Deleting the resource files, but not the resource directory itself.
    # The resource directory is kept, to prevent hijacking of resource id's

    try:
        for name in os.listdir(res_dir):
            file_path = os.path.join(res_dir, name)
            if os.path.isfile(file_path):
                os.unlink(file_path)
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Deletion exception: ' + str(err)})
        output_objects.append({'object_type': 'link', 'destination':
                               'resman.py', 'class': 'infolink', 'title':
                               'Show resources', 'text': 'Show resources'})
        lock_handle_vgrid.close()
        lock_handle_res.close()
        return (output_objects, returnvalues.CLIENT_ERROR)

    # The resource has been deleted, and OK is returned.
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource Deletion'
    output_objects.append({'object_type': 'header', 'text'
                          : 'Deleting resource'})
    output_objects.append({'object_type': 'text', 'text'
                           : 'Sucessfully deleted resource: ' + res_name})
    output_objects.append({'object_type': 'link', 'destination': 'resman.py',
                           'class': 'infolink', 'title': 'Show resources',
                           'text': 'Show resources'})
    
    # Releasing locks
    lock_handle_vgrid.close()
    lock_handle_res.close()

    # Remove resource from resource and vgrid caches (after realeasing locks)
    unmap_resource(configuration, res_name)

    return (output_objects, returnvalues.OK)
