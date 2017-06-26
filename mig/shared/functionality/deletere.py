#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#

# deletere - delete a runtime environment
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Deletion of runtime environments"""

import shared.returnvalues as returnvalues
from shared.base import valid_dir_input
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables, find_entry
from shared.refunctions import is_runtime_environment, \
     get_re_dict, delete_runtimeenv
from shared.vgridaccess import resources_using_re


def signature():
    """Signature of the main function"""

    defaults = {'re_name': REJECT_UNSET}
    return ['runtimeenvironment', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Delete runtime environment'
    output_objects.append({'object_type': 'header', 'text'
                           : 'Delete runtime environment'})
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
    
    re_name = accepted['re_name'][-1]

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not valid_dir_input(configuration.re_home, re_name):
        logger.warning(
            "possible illegal directory traversal attempt re_name '%s'"
            % re_name)
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Illegal runtime environment name: "%s"'
                               % re_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Check whether re_name represents a runtime environment
    if not is_runtime_environment(re_name, configuration):
        output_objects.append({'object_type': 'error_text',
                               'text': "No such runtime environment: '%s'"
                               % re_name})
        return (output_objects, returnvalues.CLIENT_ERROR)
    
    (re_dict, load_msg) = get_re_dict(re_name, configuration)
    if not re_dict:
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'Could not read runtime environment details for %s: %s'
             % (re_name, load_msg)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Make sure the runtime environment belongs to the user trying to delete it
    if client_id != re_dict['CREATOR']:
        output_objects.append({'object_type': 'error_text', 'text': \
        'You are not the owner of runtime environment "%s"' % re_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Prevent delete if the runtime environment is used by any resources
    actives = resources_using_re(configuration, re_name)

    # If the runtime environment is active, an error message is printed, along
    # with a list of the resources using the runtime environment
    if actives:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "Can't delete runtime environment '%s' in use by resources:"
             % re_name})
        output_objects.append({'object_type': 'list', 'list'
                               : actives})
        output_objects.append({'object_type': 'link', 'destination': 'redb.py',
                               'class': 'infolink iconspace', 'title':
                               'Show runtime environments',
                               'text': 'Show runtime environments'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Delete the runtime environment
    (del_status, msg) = delete_runtimeenv(re_name, configuration)
    
    # If something goes wrong when trying to delete runtime environment
    # re_name, an error is displayed.
    if not del_status:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Could not remove %s runtime environment: %s'
                               % (re_name, msg)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # If deletion of runtime environment re_name is successful, we just
    # return OK
    else:
        output_objects.append(
            {'object_type': 'text', 'text'
             : 'Successfully deleted runtime environment: "%s"' % re_name})
        output_objects.append({'object_type': 'link', 'destination': 'redb.py',
                               'class': 'infolink iconspace',
                               'title': 'Show runtime environments',
                               'text': 'Show runtime environments'})
        return (output_objects, returnvalues.OK) 
