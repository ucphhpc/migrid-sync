#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addresowner - add one or more resource owners
# Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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

"""Add one or more users to the list of administrators for a given resource"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.accessrequests import delete_access_request
from mig.shared.base import unhexlify
from mig.shared.defaults import any_protocol, csrf_field
from mig.shared.findtype import is_user, is_owner
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables
from mig.shared.resource import resource_is_owner, resource_add_owners


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
    status = returnvalues.OK
    output_objects.append(
        {'object_type': 'header', 'text': 'Add Resource Owner(s)'})
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

    unique_resource_name = accepted['unique_resource_name'][-1].strip()
    cert_id_list = accepted['cert_id']
    request_name = unhexlify(accepted['request_name'][-1])

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append({'object_type': 'error_text', 'text':
                               'You must be an owner of %s to add a new owner!'
                               % unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # is_owner incorporates unique_resource_name verification - no need to
    # specifically check for illegal directory traversal

    cert_id_added = []
    for cert_id in cert_id_list:
        cert_id = cert_id.strip()
        if not cert_id:
            continue
        if not is_user(cert_id, configuration):
            output_objects.append({'object_type': 'error_text', 'text':
                                   '%s is not a valid %s user!'
                                   % (cert_id, configuration.short_title)})
            status = returnvalues.CLIENT_ERROR
            continue

        # don't add if already an owner

        if resource_is_owner(unique_resource_name, cert_id, configuration):
            output_objects.append({'object_type': 'error_text', 'text':
                                   '%s is already an owner of %s.'
                                   % (cert_id, unique_resource_name)})
            status = returnvalues.CLIENT_ERROR
            continue

        # Add owner

        (add_status, add_msg) = resource_add_owners(configuration,
                                                    unique_resource_name,
                                                    [cert_id])
        if not add_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not add new owner, reason: %s'
                                   % add_msg})
            status = returnvalues.SYSTEM_ERROR
            continue
        cert_id_added.append(cert_id)

    if request_name:
        request_dir = os.path.join(configuration.resource_home,
                                   unique_resource_name)
        if not delete_access_request(configuration, request_dir, request_name):
            logger.error("failed to delete owner request for %s in %s" %
                         (unique_resource_name, request_name))
            output_objects.append({
                'object_type': 'error_text', 'text':
                'Failed to remove saved request for %s in %s!' %
                (unique_resource_name, request_name)})

    if cert_id_added:
        output_objects.append({'object_type': 'html_form', 'text':
                               'New owner(s)<br/>%s<br/>successfully added to %s!'
                               % ('<br />'.join(cert_id_added),
                                  unique_resource_name)})
        cert_id_fields = ''
        for cert_id in cert_id_added:
            cert_id_fields += """<input type=hidden name=cert_id value='%s' />
""" % cert_id

        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        fill_helpers = {'res_id': unique_resource_name,
                        'cert_id_fields': cert_id_fields,
                        'any_protocol': any_protocol,
                        'form_method': form_method,
                        'csrf_field': csrf_field,
                        'csrf_limit': csrf_limit}
        target_op = 'sendrequestaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': """
<form method='%(form_method)s' action='%(target_op)s.py'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<input type=hidden name=request_type value='resourceaccept' />
<input type=hidden name=unique_resource_name value='%(res_id)s' />
%(cert_id_fields)s
<input type=hidden name=protocol value='%(any_protocol)s' />
<table>
<tr>
<td class='title'>Custom message to user(s)</td>
</tr>
<tr>
<td><textarea name=request_text cols=72 rows=10>
We have granted you ownership access to our %(res_id)s resource.
You can access the resource administration page from the Resources page.

Regards, the %(res_id)s resource owners
</textarea></td>
</tr>
<tr>
<td><input type='submit' value='Inform user(s)' /></td>
</tr>
</table>
</form>
<br />
""" % fill_helpers})

    output_objects.append({'object_type': 'link', 'destination':
                           'resadmin.py?unique_resource_name=%s' %
                           unique_resource_name, 'class':
                           'adminlink iconspace', 'title':
                           'Administrate resource', 'text': 'Manage resource'})
    return (output_objects, status)
