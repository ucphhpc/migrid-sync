#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addvgridres - add one or more vgrid resources
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

"""Add one or more resources to a given vgrid"""

from binascii import unhexlify
import os

from shared.accessrequests import delete_access_request
from shared.defaults import any_protocol
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_resource, \
     vgrid_list_subvgrids, vgrid_add_resources, allow_resources_adm
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'unique_resource_name': REJECT_UNSET,
                'request_name': ['']}
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    status = returnvalues.OK
    output_objects.append({'object_type': 'header', 'text'
                          : 'Add %s Resource(s)' % \
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
    res_id_list = accepted['unique_resource_name']
    request_name = unhexlify(accepted['request_name'][-1])

    # make sure vgrid settings allow this owner to edit resources

    (allow_status, allow_msg) = allow_resources_adm(configuration, vgrid_name,
                                                    client_id)
    if not allow_status:
        output_objects.append({'object_type': 'error_text', 'text': allow_msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    res_id_added = []
    for res_id in res_id_list:
        unique_resource_name = res_id.lower().strip()

        # Validity of user and vgrid names is checked in this init function so
        # no need to worry about illegal directory traversal through variables

        (ret_val, msg, ret_variables) = \
            init_vgrid_script_add_rem(vgrid_name, client_id,
                                      unique_resource_name, 'resource',
                                      configuration)
        if not ret_val:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : msg})
            status = returnvalues.CLIENT_ERROR
            continue
        elif msg:

            # In case of warnings, msg is non-empty while ret_val remains True

            output_objects.append({'object_type': 'warning', 'text': msg})

        # don't add if already in vgrid or parent vgrid

        if vgrid_is_resource(vgrid_name, unique_resource_name,
                             configuration):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '%s is already a resource in the %s'
                                   % (unique_resource_name,
                                      configuration.site_vgrid_label)})
            status = returnvalues.CLIENT_ERROR
            continue

        # don't add if already in subvgrid

        (list_status, subvgrids) = vgrid_list_subvgrids(vgrid_name,
                configuration)
        if not list_status:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Error getting list of sub%ss: %s'
                                   % (configuration.site_vgrid_label, subvgrids)})
            status = returnvalues.SYSTEM_ERROR
            continue
        skip_entity = False
        for subvgrid in subvgrids:
            if vgrid_is_resource(subvgrid, unique_resource_name,
                                 configuration):
                output_objects.append({'object_type': 'error_text', 'text':
                                       '''%(res_name)s is already in a
    sub-%(_label)s (%(subvgrid)s).
    Remove the resource from the sub-%(_label)s and try again''' % \
                                       {'res_name': unique_resource_name,
                                        'subvgrid': subvgrid,
                                        '_label': configuration.site_vgrid_label}})
                status = returnvalues.CLIENT_ERROR
                skip_entity = True
                break
        if skip_entity:
            continue
        
        base_dir = os.path.abspath(configuration.vgrid_home + os.sep
                                    + vgrid_name) + os.sep
        resources_file = base_dir + 'resources'

        # Add to list and pickle

        (add_status, add_msg) = vgrid_add_resources(configuration, vgrid_name,
                                                    [unique_resource_name])
        if not add_status:
            output_objects.append({'object_type': 'error_text', 'text': '%s'
                                   % add_msg})
            status = returnvalues.SYSTEM_ERROR
            continue
        res_id_added.append(unique_resource_name)

    if request_name:
        request_dir = os.path.join(configuration.vgrid_home, vgrid_name)
        if not delete_access_request(configuration, request_dir, request_name):
                logger.error("failed to delete res request for %s in %s" % \
                             (vgrid_name, request_name))
                output_objects.append({
                    'object_type': 'error_text', 'text':
                    'Failed to remove saved request for %s in %s!' % \
                    (vgrid_name, request_name)})

    if res_id_added:
        output_objects.append(
            {'object_type': 'html_form', 'text':
             'New resource(s)<br />%s<br />successfully added to %s %s!''' % \
             ('<br />'.join(res_id_added), vgrid_name,
              configuration.site_vgrid_label)
             })
        res_id_fields = ''
        for res_id in res_id_added:
            res_id_fields += """
<input type=hidden name=unique_resource_name value='%s' />""" % res_id
        output_objects.append({'object_type': 'html_form', 'text': """
<form method='post' action='sendrequestaction.py'>
<input type=hidden name=request_type value='vgridaccept' />
<input type=hidden name=vgrid_name value='%(vgrid_name)s' />
%(res_id_fields)s
<input type=hidden name=protocol value='%(protocol)s' />
<table>
<tr>
<td class='title'>Custom message to resource owners</td>
</tr><tr>
<td><textarea name=request_text cols=72 rows=10>
We have granted your resource access to our %(vgrid_name)s %(_label)s.
You can assign it to accept jobs from the %(vgrid_name)s %(_label)s from your
Resources page on %(short_title)s.

Regards, the %(vgrid_name)s %(_label)s owners
</textarea></td>
</tr>
<tr>
<td><input type='submit' value='Inform owners' /></td>
</tr>
</table>
</form>
<br />
""" % {'vgrid_name': vgrid_name, 'unique_resource_name': unique_resource_name,
       'protocol': any_protocol, '_label': configuration.site_vgrid_label,
       'short_title': configuration.short_title, 'res_id_fields':
       res_id_fields}})

    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)
