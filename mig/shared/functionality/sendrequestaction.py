#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sendrequestaction - send request for e.g. member or ownership action handler
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

"""Send request e.g. for ownership or membership action back end"""

import os

import shared.returnvalues as returnvalues
from shared.defaults import default_vgrid, any_vgrid, any_protocol, \
     email_keyword_list, default_vgrid_settings_limit
from shared.accessrequests import save_access_request
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables, find_entry
from shared.notification import notify_user_thread
from shared.resource import anon_to_real_res_map, resource_owners
from shared.user import anon_to_real_user_map
from shared.vgrid import vgrid_owners, vgrid_settings, vgrid_is_owner, \
     vgrid_is_member, vgrid_is_owner_or_member, vgrid_is_resource
from shared.vgridaccess import get_user_map, get_resource_map, \
     user_vgrid_access, CONF, OWNERS, USERID


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': [],
                'vgrid_name': [''], 'cert_id': [],
                'protocol': [any_protocol],
                'request_type': REJECT_UNSET,
                'request_text': REJECT_UNSET}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = '%s send request' % configuration.short_title
    output_objects.append({'object_type': 'header', 'text':
                           '%s send request' % configuration.short_title})
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

    target_id = client_id
    vgrid_name = accepted['vgrid_name'][-1].strip()
    visible_user_names = accepted['cert_id']
    visible_res_names = accepted['unique_resource_name']
    request_type = accepted['request_type'][-1].strip().lower()
    request_text = accepted['request_text'][-1].strip()
    protocols = [proto.strip() for proto in accepted['protocol']]
    use_any = False
    if any_protocol in protocols:
        use_any = True
        protocols = configuration.notify_protocols
    protocols = [proto.lower() for proto in protocols]

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)


    valid_request_types = ['resourceowner', 'resourceaccept', 'resourcereject',
                           'vgridowner', 'vgridmember','vgridresource',
                           'vgridaccept', 'vgridreject', 'plain']
    if not request_type in valid_request_types:
        output_objects.append({
            'object_type': 'error_text', 'text'
            : '%s is not a valid request_type (valid types: %s)!'
            % (request_type.lower(),
               valid_request_types)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not protocols:
        output_objects.append({
            'object_type': 'error_text', 'text':
            'No protocol specified!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    user_map = get_user_map(configuration)
    reply_to = user_map[client_id][USERID]

    if request_type == "plain":
        if not visible_user_names:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'No user ID specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

        user_id = visible_user_names[-1].strip()
        anon_map = anon_to_real_user_map(configuration)
        if anon_map.has_key(user_id):
            user_id = anon_map[user_id]
        if not user_map.has_key(user_id):
            output_objects.append({'object_type': 'error_text',
                                   'text': 'No such user: %s' % \
                                   user_id
                                   })
            return (output_objects, returnvalues.CLIENT_ERROR)
        target_name = user_id
        user_dict = user_map[user_id]
        vgrid_access = user_vgrid_access(configuration, client_id)
        vgrids_allow_email = user_dict[CONF].get('VGRIDS_ALLOW_EMAIL', [])
        vgrids_allow_im = user_dict[CONF].get('VGRIDS_ALLOW_IM', [])
        if any_vgrid in vgrids_allow_email:
            email_vgrids = vgrid_access
        else:
            email_vgrids = set(vgrids_allow_email).intersection(vgrid_access)
        if any_vgrid in vgrids_allow_im:
            im_vgrids = vgrid_access
        else:
            im_vgrids = set(vgrids_allow_im).intersection(vgrid_access)
        if use_any:
            # Do not try disabled protocols if ANY was requested
            if not email_vgrids:
                protocols = [proto for proto in protocols \
                             if proto not in email_keyword_list]
            if not im_vgrids:
                protocols = [proto for proto in protocols \
                             if proto in email_keyword_list]
        if not email_vgrids and [proto for proto in protocols \
                                 if proto in email_keyword_list]:
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'You are not allowed to send emails to %s!' % \
                user_id
                })
            return (output_objects, returnvalues.CLIENT_ERROR)
        if not im_vgrids and [proto for proto in protocols \
                              if proto not in email_keyword_list]:
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'You are not allowed to send instant messages to %s!' % \
                user_id
                })
            return (output_objects, returnvalues.CLIENT_ERROR)
        for proto in protocols:
            if not user_dict[CONF].get(proto.upper(), False):
                if use_any:
                    # Remove missing protocols if ANY protocol was requested
                    protocols = [i for i in protocols if i != proto]
                else:
                    output_objects.append({
                        'object_type': 'error_text', 'text'
                        : 'User %s does not accept %s messages!' % \
                        (user_id, proto)
                        })
                    return (output_objects, returnvalues.CLIENT_ERROR)
        if not protocols:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'User %s does not accept requested protocol(s) messages!' % \
                user_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        target_list = [user_id]
    elif request_type in ["vgridaccept", "vgridreject"]:
        # Always allow accept messages but only between owners/members
        if not visible_user_names and not visible_res_names:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'No user or resource ID specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        if not vgrid_name:
            output_objects.append({
                'object_type': 'error_text', 'text': 'No vgrid_name specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        if vgrid_name.upper() == default_vgrid.upper():
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'No requests for %s are allowed!' % \
                default_vgrid
                })
            return (output_objects, returnvalues.CLIENT_ERROR)
        if not vgrid_is_owner(vgrid_name, client_id, configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'You are not an owner of %s or a parent %s!' % \
                 (vgrid_name, label)})
            return (output_objects, returnvalues.CLIENT_ERROR)
        # NOTE: we support exactly one vgrid but multiple users/resources here
        if visible_user_names:
            logger.info("setting user recipients: %s" % visible_user_names)
            target_list = [user_id.strip() for user_id in visible_user_names]
        elif visible_res_names:
            # vgrid resource accept - lookup and notify resource owners
            logger.info("setting res owner recipients: %s" % visible_res_names)
            target_list = []
            for unique_resource_name in visible_res_names:
                logger.info("loading res owners for %s" % unique_resource_name)
                (load_status, res_owners) = resource_owners(
                    configuration, unique_resource_name)
                if not load_status:
                    output_objects.append({
                        'object_type': 'error_text', 'text':
                        'Could not lookup owners of %s!' % \
                        unique_resource_name})
                    continue
                logger.info("adding res owners to recipients: %s" % res_owners)
                target_list += [user_id for user_id in res_owners]

        target_id = '%s %s owners' % (vgrid_name, label)
        target_name = vgrid_name
    elif request_type in ["resourceaccept", "resourcereject"]:
        # Always allow accept messages between actual resource owners
        if not visible_user_names:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'No user ID specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        if not visible_res_names:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'No resource ID specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        # NOTE: we support exactly one resource but multiple users here
        unique_resource_name = visible_res_names[-1].strip()
        target_name = unique_resource_name
        res_map = get_resource_map(configuration)
        if not res_map.has_key(unique_resource_name):
            output_objects.append({'object_type': 'error_text',
                                   'text': 'No such resource: %s' % \
                                   unique_resource_name
                                   })
            return (output_objects, returnvalues.CLIENT_ERROR)
        owners_list = res_map[unique_resource_name][OWNERS]
        if not client_id in owners_list:
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'You are not an owner of %s!' % unique_resource_name})
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Invalid resource %s message!' % \
                                   request_type})
            return (output_objects, returnvalues.CLIENT_ERROR)
        target_id = '%s resource owners' % unique_resource_name
        target_name = unique_resource_name
        target_list = [user_id.strip() for user_id in visible_user_names]
    elif request_type == "resourceowner":
        if not visible_res_names:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'No resource ID specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)        
        # NOTE: we support exactly one resource but multiple users here
        unique_resource_name = visible_res_names[-1].strip()
        anon_map = anon_to_real_res_map(configuration.resource_home)
        if anon_map.has_key(unique_resource_name):
            unique_resource_name = anon_map[unique_resource_name]
        target_name = unique_resource_name
        res_map = get_resource_map(configuration)
        if not res_map.has_key(unique_resource_name):
            output_objects.append({'object_type': 'error_text',
                                   'text': 'No such resource: %s' % \
                                   unique_resource_name
                                   })
            return (output_objects, returnvalues.CLIENT_ERROR)
        target_list = res_map[unique_resource_name][OWNERS]
        if client_id in target_list:
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'You are already an owner of %s!' % unique_resource_name
                })
            return (output_objects, returnvalues.CLIENT_ERROR)
        
        request_dir = os.path.join(configuration.resource_home,
                                   unique_resource_name)
        access_request = {'request_type': request_type, 'entity': client_id,
                          'target': unique_resource_name, 'request_text':
                          request_text}
        if not save_access_request(configuration, request_dir, access_request):
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'Could not save request - owners may still manually add you'
                })
            return (output_objects, returnvalues.SYSTEM_ERROR)
    elif request_type in ["vgridmember", "vgridowner", "vgridresource"]:
        if not vgrid_name:
            output_objects.append({
                'object_type': 'error_text', 'text': 'No vgrid_name specified!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # default vgrid is read-only
        
        if vgrid_name.upper() == default_vgrid.upper():
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'No requests for %s are not allowed!' % \
                default_vgrid
                })
            return (output_objects, returnvalues.CLIENT_ERROR)

        # stop owner or member request if already an owner
        # and prevent repeated resource access requests

        if request_type == 'vgridresource':
            # NOTE: we support exactly one resource here
            unique_resource_name = visible_res_names[-1].strip()
            target_id = entity = unique_resource_name
            if vgrid_is_resource(vgrid_name, unique_resource_name,
                                 configuration):
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'You already have access to %s or a parent %s.' % \
                     (vgrid_name, label)})
                return (output_objects, returnvalues.CLIENT_ERROR)
        else:
            target_id = entity = client_id
            if vgrid_is_owner(vgrid_name, client_id, configuration):
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'You are already an owner of %s or a parent %s!' % \
                     (vgrid_name, label)})
                return (output_objects, returnvalues.CLIENT_ERROR)

        # only ownership requests are allowed for existing members

        if request_type == 'vgridmember':
            if vgrid_is_member(vgrid_name, client_id, configuration):
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'You are already a member of %s or a parent %s.' % \
                     (vgrid_name, label)})
                return (output_objects, returnvalues.CLIENT_ERROR)

        # Find all VGrid owners configured to receive notifications

        target_name = vgrid_name
        (settings_status, settings_dict) = vgrid_settings(vgrid_name,
                                                          configuration,
                                                          recursive=True,
                                                          as_dict=True)
        if not settings_status:
            settings_dict = {}
        request_recipients = settings_dict.get('request_recipients',
                                               default_vgrid_settings_limit)
        # We load inherited owners and reverse it to take direct owners first
        (owners_status, owners_list) = vgrid_owners(vgrid_name, configuration,
                                             recursive=True)
        if not owners_status:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Failed to lookup owners for %s %s - are you sure it exists?'
                 % (vgrid_name, label)})
            return (output_objects, returnvalues.CLIENT_ERROR)
        prioritized_list = owners_list[::-1]
        target_list = prioritized_list[:request_recipients]

        request_dir = os.path.join(configuration.vgrid_home, vgrid_name)
        access_request = {'request_type': request_type, 'entity': entity,
                          'target': vgrid_name, 'request_text': request_text}
        if not save_access_request(configuration, request_dir, access_request):
            output_objects.append({
                'object_type': 'error_text', 'text'
                : 'Could not save request - owners may still manually add you'
                })
            return (output_objects, returnvalues.SYSTEM_ERROR)
        
    else:
        output_objects.append({
            'object_type': 'error_text', 'text': 'Invalid request type: %s' % \
            request_type})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Now send request to all targets in turn
    # TODO: inform requestor if no owners have mail/IM set in their settings

    logger.debug("sending notification to recipients: %s" % target_list)

    for target in target_list:

        if not target:
            logger.warning("skipping empty notify target: %s" % target_list)
            continue
        
        # USER_CERT entry is destination

        notify = []
        for proto in protocols:
            notify.append('%s: SETTINGS' % proto)
        job_dict = {'NOTIFY': notify, 'JOB_ID': 'NOJOBID', 'USER_CERT': target}

        notifier = notify_user_thread(
            job_dict,
            [target_id, target_name, request_type, request_text, reply_to],
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
    output_objects.append({'object_type': 'text', 'text':
                           """Please make sure you have notifications
configured on your Setings page if you expect a reply to this message"""})
    
    return (output_objects, returnvalues.OK)
