#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# accessrequestaction - request memebership or ownership action handler
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

"""Request access (ownership or membership) action back end"""

import shared.returnvalues as returnvalues
from shared.defaults import default_vgrid
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.notification import notify_user_thread
from shared.resource import anon_to_real_res_map
from shared.vgrid import vgrid_list, vgrid_is_owner, vgrid_is_member
from shared.vgridaccess import get_resource_map, OWNERS


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': [''],
                'vgrid_name': [''],
                'request_type': REJECT_UNSET,
                'request_text': REJECT_UNSET}
    return ['', defaults]


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

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s access request' % \
                            configuration.short_title
    output_objects.append({'object_type': 'header', 'text'
                          : '%s access request' % \
                            configuration.short_title})

    vgrid_name = accepted['vgrid_name'][-1].strip()
    visible_res_name = accepted['unique_resource_name'][-1].strip()
    request_type = accepted['request_type'][-1].strip().lower()
    request_text = accepted['request_text'][-1].strip()

    valid_request_types = ['resourceowner', 'vgridowner', 'vgridmember']
    if not request_type in valid_request_types:
        output_objects.append({
            'object_type': 'error_text', 'text'
            : '%s is not a valid request_type (valid types: %s)!'
            % (request_type.lower(),
               valid_request_types)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if request_type == "resourceowner":
        if not visible_res_name:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'No resource ID specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        
        unique_resource_name = visible_res_name
        anon_map = anon_to_real_res_map(configuration.resource_home)
        if anon_map.has_key(visible_res_name):
            unique_resource_name = anon_map[visible_res_name]
        target_name = unique_resource_name
        res_map = get_resource_map(configuration)
        if not res_map.has_key(unique_resource_name):
            output_objects.append({'object_type': 'error_text',
                                   'text': 'No such resource: %s' % \
                                   visible_res_name
                                   })
            return (output_objects, returnvalues.CLIENT_ERROR)
        owner_list = res_map[unique_resource_name][OWNERS]
        if client_id in owner_list:
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'You are already an owner of %s!' % unique_resource_name
                })
            return (output_objects, returnvalues.CLIENT_ERROR)
    elif request_type in ["vgridmember", "vgridowner"]:
        if not vgrid_name:
            output_objects.append({
                'object_type': 'error_text', 'text': 'No VGrid specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # default vgrid is read-only
        
        if vgrid_name.upper() == default_vgrid.upper():
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'Member and owner requests for %s are not allowed!' % \
                default_vgrid
                })
            return (output_objects, returnvalues.CLIENT_ERROR)

        # stop if already an owner

        if vgrid_is_owner(vgrid_name, client_id, configuration):
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'You are already an owner of %s or a parent vgrid!' % \
                vgrid_name})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # only ownership requests are allowed for existing members

        if request_type == 'vgridmember':
            if vgrid_is_member(vgrid_name, client_id, configuration):
                output_objects.append({
                    'object_type': 'error_text', 'text'
                    : 'You are already a member of %s or a parent vgrid.' % \
                    vgrid_name})
                return (output_objects, returnvalues.CLIENT_ERROR)

        # Find all VGrid owners

        target_name = vgrid_name
        (status, owner_list) = vgrid_list(vgrid_name, 'owners', configuration)
        if not status:
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'Could not load list of current owners for %s vgrid!'
                % vgrid_name})
            return (output_objects, returnvalues.CLIENT_ERROR)

    else:
        output_objects.append({
            'object_type': 'error_text', 'text': 'Invalid request type: %s' % \
            request_type})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Now send request to all owners in turn
    # TODO: inform requestor if no owners have mail/IM set in their settings
    
    owner_number = 1
    for owner in owner_list:
        output_objects.append({'object_type': 'text', 'text'
                              : 'Sending message to owner number %s'
                               % owner_number})
        owner_number += 1

        # USER_CERT entry is destination

        job_dict = {'NOTIFY': [
            'jabber: SETTINGS',
            'msn: SETTINGS',
            'email: SETTINGS',
            'icq: SETTINGS',
            'aol: SETTINGS',
            'yahoo: SETTINGS',
            ], 'JOB_ID': 'NOJOBID', 'USER_CERT': owner}

        notifier = notify_user_thread(
            job_dict,
            [client_id, target_name, request_type, request_text],
            'ACCESSREQUEST',
            logger,
            '',
            configuration,
            )

        # Try finishing delivery but do not block forever on one message
        notifier.join(30)
        
    return (output_objects, returnvalues.OK)


