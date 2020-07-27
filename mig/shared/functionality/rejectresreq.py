#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rejectresreq - reject a resource access request
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

"""Reject access request to a given resource"""
from __future__ import absolute_import

from binascii import unhexlify
import os

from .shared.accessrequests import load_access_request, delete_access_request
from .shared.defaults import any_protocol, csrf_field
from .shared.findtype import is_owner
from .shared.functional import validate_input_and_cert, REJECT_UNSET
from .shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from .shared.init import initialize_main_variables
from .shared.validstring import valid_user_path
from .shared import returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET,
                'request_name': ['']}
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Reject Resource Request'})
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
                               'You must be an owner of %s to reject requests!'
                               % unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # resource dirs when own name is a prefix of another user name

    base_dir = \
        os.path.abspath(os.path.join(configuration.resource_home,
                        unique_resource_name)) + os.sep

    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_path = os.path.abspath(os.path.join(base_dir, request_name))
    if not valid_user_path(configuration, abs_path, base_dir, allow_equal=False):
        logger.warning('%s tried to access restricted path %s ! (%s)' % \
                       (client_id, abs_path, request_name))
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Illegal request name "%s":
you can only reject requests to your own resources.''' % request_name})
        return (output_objects, returnvalues.CLIENT_ERROR)
            
    if request_name:
        request_dir = os.path.join(configuration.resource_home,
                                   unique_resource_name)
        req = load_access_request(configuration, request_dir, request_name)
    if not req or not delete_access_request(configuration, request_dir,
                                            request_name):
            logger.error("failed to delete owner request for %s in %s" % \
                         (unique_resource_name, request_name))
            output_objects.append({
                'object_type': 'error_text', 'text':
                'Failed to remove saved resource request for %s in %s!'\
                % (unique_resource_name, request_name)})
            return (output_objects, returnvalues.CLIENT_ERROR)
    output_objects.append({'object_type': 'text', 'text': '''
Deleted %(request_type)s access request to %(target)s for %(entity)s .
''' % req})
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'protocol': any_protocol,
                    'unique_resource_name': unique_resource_name, 
                    'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    fill_helpers.update(req)
    target_op = 'sendrequestaction'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    output_objects.append({'object_type': 'html_form', 'text':
                           """
<p>
You can use the reply form below if you want to additionally send an
explanation for rejecting the request.
</p>
<form method='%(form_method)s' action='%(target_op)s.py'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<input type=hidden name=request_type value='resourcereject' />
<input type=hidden name=unique_resource_name value='%(target)s' />
<input type=hidden name=cert_id value='%(entity)s' />
<input type=hidden name=protocol value='%(protocol)s' />
<table>
<tr>
<td class='title'>Optional reject message to requestor(s)</td>
</tr><tr>
<td><textarea name=request_text cols=72 rows=10>
We have decided to reject your %(request_type)s request to our %(target)s
resource.

Regards, the %(target)s resource owners
</textarea></td>
</tr>
<tr>
<td><input type='submit' value='Inform requestor(s)' /></td>
</tr>
</table>
</form>
<br />
""" % fill_helpers})
    output_objects.append({
        'object_type': 'link', 'destination':
        'resadmin.py?unique_resource_name=%s' % unique_resource_name,
        'text': 'Back to administration for %s' % unique_resource_name})
    return (output_objects, returnvalues.OK)
