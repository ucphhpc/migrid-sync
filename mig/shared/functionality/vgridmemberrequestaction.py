#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridmemberrequestaction - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.notification import notify_user_thread
from shared.vgrid import vgrid_list, vgrid_is_owner, vgrid_is_member


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'request_type': REJECT_UNSET,
                'request_text': REJECT_UNSET}
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
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
    title_entry['text'] = '%s VGrid membership request' % \
                            configuration.short_title
    output_objects.append({'object_type': 'header', 'text'
                          : '%s VGrid membership request' % \
                            configuration.short_title})

    vgrid_name = accepted['vgrid_name'][-1]
    request_type = accepted['request_type'][-1].strip().lower()
    request_text = accepted['request_text'][-1].strip()
    if vgrid_name.upper() == 'GENERIC':

        # not allowed!

        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Member and owner requests for the GENERIC VGrid are not allowed!'
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    valid_request_types = ['owner', 'member']
    if not request_type.lower() in valid_request_types:
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is not a valid request_type (valid types: %s)!'
                               % (request_type.lower(),
                              valid_request_types)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # stop if already an owner

    if vgrid_is_owner(vgrid_name, client_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'You are already an owner of %s or a parent vgrid!'
                               % vgrid_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # if already member do not allow a request to become a member (but allow an owner request)

    if request_type == 'member':
        if vgrid_is_member(vgrid_name, client_id, configuration):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'You are already a member of %s or a parent vgrid.'
                                   % vgrid_name})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Send messages to all VGrid owners

    (status, msg) = vgrid_list(vgrid_name, 'owners', configuration)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not get list of current owners for %s vgrid. Are you sure a vgrid with this name exists?'
                               % vgrid_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # TODO: If no owners have mail/IM set in their settings then inform the requester

    # msg is list of owners

    owner_number = 1
    for owner in msg:
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
            ], 'JOB_ID': 'NOJOBIDVGRIDMEMBERREQUESTMESSAGE',
                'USER_CERT': owner}

        notifier = notify_user_thread(
            job_dict,
            [client_id, vgrid_name, request_type, request_text],
            'VGRIDMEMBERREQUEST',
            logger,
            '',
            configuration,
            )

        # Try finishing delivery but do not block forever on one message
        notifier.join(30)
        
    return (output_objects, returnvalues.OK)


