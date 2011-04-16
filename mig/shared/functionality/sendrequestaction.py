#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sendrequestaction - send request for e.g. member or ownership action handler
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""Send request e.g. for ownership or membership action back end"""

import shared.returnvalues as returnvalues
from shared.defaults import default_vgrid, any_vgrid, any_protocol
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables, find_entry
from shared.notification import notify_user_thread
from shared.resource import anon_to_real_res_map
from shared.user import anon_to_real_user_map
from shared.vgrid import vgrid_list, vgrid_is_owner, vgrid_is_member
from shared.vgridaccess import user_allowed_vgrids, get_user_map, \
     get_resource_map, CONF, OWNERS


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': [''],
                'vgrid_name': [''], 'cert_id': [''],
                'protocol': [''],
                'request_type': REJECT_UNSET,
                'request_text': REJECT_UNSET}
    return ['html_form', defaults]


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

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s send request' % \
                            configuration.short_title
    output_objects.append({'object_type': 'header', 'text'
                          : '%s send request' % \
                            configuration.short_title})

    vgrid_name = accepted['vgrid_name'][-1].strip()
    visible_user_name = accepted['cert_id'][-1].strip()
    visible_res_name = accepted['unique_resource_name'][-1].strip()
    request_type = accepted['request_type'][-1].strip().lower()
    request_text = accepted['request_text'][-1].strip()
    protocol = accepted['protocol'][-1].strip()

    valid_request_types = ['resourceowner', 'vgridowner', 'vgridmember',
                           'plain']
    if not request_type in valid_request_types:
        output_objects.append({
            'object_type': 'error_text', 'text'
            : '%s is not a valid request_type (valid types: %s)!'
            % (request_type.lower(),
               valid_request_types)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if request_type == "plain":
        if not visible_user_name:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'No user ID specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        if not protocol:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'No protocol specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

        user_id = visible_user_name
        anon_map = anon_to_real_user_map(configuration.user_home)
        if anon_map.has_key(visible_user_name):
            user_id = anon_map[visible_user_name]
        target_name = user_id
        user_map = get_user_map(configuration)
        if not user_map.has_key(user_id):
            output_objects.append({'object_type': 'error_text',
                                   'text': 'No such user: %s' % \
                                   visible_user_name
                                   })
            return (output_objects, returnvalues.CLIENT_ERROR)
        user_dict = user_map[user_id][CONF]
        allowed_vgrids = user_allowed_vgrids(configuration, client_id)
        visible_vgrids = user_dict.get('VISIBLE_VGRIDS', [])
        if any_vgrid in visible_vgrids:
            shared_vgrids = allowed_vgrids
        else:
            shared_vgrids = set(visible_vgrids).intersection(allowed_vgrids)
        if not shared_vgrids:
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'You are not allowed to send messages to %s!' % \
                visible_user_name
                })
            return (output_objects, returnvalues.CLIENT_ERROR)
        if not user_dict[protocol.upper()]:
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'User %s does not accept %s messages!' % \
                (visible_user_name, protocol)
                })
            return (output_objects, returnvalues.CLIENT_ERROR)
        target_list = [user_id]
    elif request_type == "resourceowner":
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
        target_list = res_map[unique_resource_name][OWNERS]
        if client_id in target_list:
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
        (status, target_list) = vgrid_list(vgrid_name, 'owners', configuration)
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

    # Now send request to all targets in turn
    # TODO: inform requestor if no owners have mail/IM set in their settings
    
    for target in target_list:
        # USER_CERT entry is destination

        notify = []
        if protocol:
            notify.append('%s: SETTINGS' % protocol)
        else:
            for proto in configuration.notify_protocols:
                notify.append('%s: SETTINGS' % proto)
        job_dict = {'NOTIFY': notify, 'JOB_ID': 'NOJOBID', 'USER_CERT': target}

        notifier = notify_user_thread(
            job_dict,
            [client_id, target_name, request_type, request_text],
            'SENDREQUEST',
            logger,
            '',
            configuration,
            )

        # Try finishing delivery but do not block forever on one message
        notifier.join(30)
    output_objects.append({'object_type': 'text', 'text':
                           'Sent %s message to %d people' % \
                           (request_type, len(target_list))})
    
    return (output_objects, returnvalues.OK)
