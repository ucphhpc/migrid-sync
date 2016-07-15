#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rejectvgridreq - reject a vgrid access request
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

"""Reject access request to a given vgrid"""

from binascii import unhexlify
import os

from shared.accessrequests import load_access_request, delete_access_request
from shared.defaults import any_protocol
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_resource, \
     vgrid_list_subvgrids, vgrid_add_resources
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'request_name': ['']}
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Reject %s Request' % \
                           configuration.site_vgrid_label})
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

    vgrid_name = accepted['vgrid_name'][-1].strip()
    request_name = unhexlify(accepted['request_name'][-1])

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, client_id, request_name,
                                  'request', configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif msg:

        # In case of warnings, msg is non-empty while ret_val remains True

        output_objects.append({'object_type': 'warning', 'text': msg})

    if request_name:
        request_dir = os.path.join(configuration.vgrid_home, vgrid_name)
        req = load_access_request(configuration, request_dir, request_name)
    if not req or not delete_access_request(configuration, request_dir,
                                            request_name):
            logger.error("failed to delete owner request for %s in %s" % \
                         (vgrid_name, request_name))
            output_objects.append({
                'object_type': 'error_text', 'text':
                'Failed to remove saved vgrid request for %s in %s!'\
                % (vgrid_name, request_name)})
            return (output_objects, returnvalues.CLIENT_ERROR)
    output_objects.append({'object_type': 'text', 'text': '''
Deleted %(request_type)s access request to %(target)s for %(entity)s .
''' % req})
    if req['request_type'] == 'vgridresource':
        id_field = "unique_resource_name"
    else:
        id_field = "cert_id"
    fill_helper = {'protocol': any_protocol, 'id_field': id_field,
                   '_label': configuration.site_vgrid_label}
    fill_helper.update(req)
    output_objects.append({'object_type': 'html_form', 'text':
                           """
<p>
You can use the reply form below if you want to additionally send an
explanation for rejecting the request.
</p>
<form method='post' action='sendrequestaction.py'>
<input type=hidden name=request_type value='vgridreject' />
<input type=hidden name=vgrid_name value='%(target)s' />
<input type=hidden name=%(id_field)s value='%(entity)s' />
<input type=hidden name=protocol value='%(protocol)s' />
<table>
<tr>
<td class='title'>Optional reject message to requestor(s)</td>
</tr><tr>
<td><textarea name=request_text cols=72 rows=10>
We have decided to reject your %(request_type)s request to our %(target)s
%(_label)s.

Regards, the %(target)s %(_label)s owners
</textarea></td>
</tr>
<tr>
<td><input type='submit' value='Inform requestor(s)' /></td>
</tr>
</table>
</form>
<br />
""" % fill_helper})
    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)
