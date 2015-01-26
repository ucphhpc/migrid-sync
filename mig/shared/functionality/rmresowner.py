#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmresowner - remove resource owner
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""Add a CN to the list of administrators for a given resource. The CN is
not required to be that of an existing MiG user.
"""

import os

import shared.returnvalues as returnvalues
from shared.findtype import is_user, is_owner
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.resource import resource_is_owner, resource_remove_owners


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET,
                'cert_id': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Remove Resource Owner'})
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

    unique_resource_name = accepted['unique_resource_name'][-1]
    cert_id = accepted['cert_id'][-1]

    if not is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'You must be an owner of %s to remove another owner!'
                               % unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # is_owner incorporates unique_resource_name verification - no need to
    # specifically check for illegal directory traversal

    if not is_user(cert_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is not a valid %s user!' % \
                                (cert_id, configuration.short_title) })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # reject remove if cert_id is not an owner

    if not resource_is_owner(unique_resource_name, cert_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                               : '%s is not an owner of %s.'
                               % (cert_id, unique_resource_name)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    base_dir = os.path.abspath(os.path.join(configuration.resource_home,
                                            unique_resource_name)) + os.sep

    # Remove owner

    owners_file = os.path.join(base_dir, 'owners')
    (rm_status, rm_msg) = resource_remove_owners(configuration,
                                                 unique_resource_name,
                                                 [cert_id])
    if not rm_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not remove owner, reason: %s'
                               % rm_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : '%s was successfully removed and is no longer an owner of %s!'
                           % (cert_id, unique_resource_name)})
    output_objects.append({'object_type': 'link', 'destination':
                        'resadmin.py?unique_resource_name=%s' % \
                           unique_resource_name, 'class': 'adminlink', 'title':
                           'Administrate resource', 'text': 'Manage resource'})
    return (output_objects, returnvalues.OK)


