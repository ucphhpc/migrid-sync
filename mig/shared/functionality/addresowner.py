#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addresowner - add resource owner
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

# Minimum Intrusion Grid

"""Add a user ID to the list of administrators for a given
resource. 
"""

from binascii import unhexlify
import os

import shared.returnvalues as returnvalues
from shared.accessrequests import delete_access_request
from shared.defaults import any_protocol
from shared.findtype import is_user, is_owner
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.resource import resource_is_owner, resource_add_owners


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET,
                'cert_id': REJECT_UNSET,
                'request_name': ['']}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Add Resource Owner'})
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

    unique_resource_name = accepted['unique_resource_name'][-1].strip()
    cert_id = accepted['cert_id'][-1].strip()
    request_name = unhexlify(accepted['request_name'][-1])

    if not is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'You must be an owner of %s to add a new owner!'
                               % unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # is_owner incorporates unique_resource_name verification - no need to
    # specifically check for illegal directory traversal

    if not is_user(cert_id, configuration.mig_server_home):
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is not a valid %s user!'
                               % (cert_id, configuration.short_title)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't add if already an owner

    if resource_is_owner(unique_resource_name, cert_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                               : '%s is already an owner of %s.'
                               % (cert_id, unique_resource_name)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Add owner

    (add_status, add_msg) = resource_add_owners(configuration,
                                                unique_resource_name,
                                                [cert_id])
    if not add_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not add new owner, reason: %s'
                               % add_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if request_name:
        request_dir = os.path.join(configuration.resource_home,
                                   unique_resource_name)
        if not delete_access_request(configuration, request_dir, request_name):
                logger.error("failed to delete owner request for %s in %s" % \
                             (unique_resource_name, request_name))
                output_objects.append({
                    'object_type': 'error_text', 'text':
                    'Failed to remove saved request for %s in %s!' % \
                    (unique_resource_name, request_name)})

    output_objects.append({'object_type': 'text', 'text'
                          : 'New owner %s successfully added to %s!'
                           % (cert_id, unique_resource_name)})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<form method='post' action='sendrequestaction.py'>
<input type=hidden name=request_type value='resourceaccept' />
<input type=hidden name=unique_resource_name value='%s' />
<input type=hidden name=cert_id value='%s' />
<input type=hidden name=protocol value='%s' />
<table>
<tr>
<td class='title'>Custom message to user</td>
</tr>
<tr>
<td><textarea name=request_text cols=72 rows=10>
We have granted you ownership access to our %s resource.
You can access the resource administration page from the Resources page.

Regards, the %s resource owners
</textarea></td>
</tr>
<tr>
<td><input type='submit' value='Inform user' /></td>
</tr>
</table>
</form>
<br />
""" % (unique_resource_name, cert_id, any_protocol,
              unique_resource_name, unique_resource_name)})
    output_objects.append({'object_type': 'link', 'destination':
                           'resadmin.py?unique_resource_name=%s' % \
                           unique_resource_name, 'class':
                           'adminlink iconspace', 'title':
                           'Administrate resource', 'text': 'Manage resource'})
    return (output_objects, returnvalues.OK)


