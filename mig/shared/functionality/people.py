#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# people - view and communicate with other users
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""View and communicate with other users that allow it"""

from urllib import quote

import shared.returnvalues as returnvalues
from shared.base import pretty_format_user, extract_field
from shared.defaults import default_pager_entries, any_vgrid, csrf_field
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import man_base_js, man_base_html, html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.modified import pending_users_update, pending_vgrids_update
from shared.user import anon_to_real_user_map, user_gravatar_url
from shared.vgridaccess import user_visible_user_confs, user_vgrid_access, \
    CONF

list_operations = ['showlist', 'list']
show_operations = ['show', 'showlist']
allowed_operations = list(set(list_operations + show_operations))


def signature():
    """Signature of the main function"""

    defaults = {'operation': ['show'],
                'caching': ['false']}
    return ['users', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'People'
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

    operation = accepted['operation'][-1]
    caching = (accepted['caching'][-1].lower() in ('true', 'yes'))

    if not operation in allowed_operations:
        output_objects.append({'object_type': 'text', 'text':
                               '''Operation must be one of %s.''' %
                               ', '.join(allowed_operations)})
        return (output_objects, returnvalues.OK)

    logger.info("%s %s begin for %s" % (op_name, operation, client_id))
    pending_updates = False
    if operation in show_operations:

        # jquery support for tablesorter and confirmation on "send"
        # table initially sorted by 0 (name)

        # NOTE: We distinguish between caching on page load and forced refresh
        refresh_helper = 'ajax_people(%s, %%s)'
        refresh_call = refresh_helper % configuration.notify_protocols
        table_spec = {'table_id': 'usertable', 'sort_order': '[[0,0]]',
                      'refresh_call': refresh_call % 'false'}
        (add_import, add_init, add_ready) = man_base_js(configuration,
                                                        [table_spec],
                                                        {'width': 640})
        if operation == "show":
            add_ready += '%s;' % (refresh_call % 'true')
        title_entry['script']['advanced'] += add_import
        title_entry['script']['init'] += add_init
        title_entry['script']['ready'] += add_ready

        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})

        output_objects.append({'object_type': 'header', 'text': 'People'})

        output_objects.append(
            {'object_type': 'text', 'text':
             'View and communicate with other users.'
             })

        output_objects.append(
            {'object_type': 'sectionheader', 'text': 'All users'})

        # Helper form for sends

        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        target_op = 'sendrequestaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        helper = html_post_helper('sendmsg', '%s.py' % target_op,
                                  {'cert_id': '__DYNAMIC__',
                                   'protocol': '__DYNAMIC__',
                                   'request_type': 'plain',
                                   'request_text': '',
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text':
                               helper})

        output_objects.append({'object_type': 'table_pager', 'entry_name':
                               'people', 'default_entries':
                               default_pager_entries})

    users = []
    if operation in list_operations:
        logger.info("get vgrid and user map with caching %s" % caching)
        visible_user = user_visible_user_confs(configuration, client_id,
                                               caching)
        vgrid_access = user_vgrid_access(configuration, client_id,
                                         caching=caching)
        anon_map = anon_to_real_user_map(configuration)
        if not visible_user:
            output_objects.append(
                {'object_type': 'error_text', 'text': 'no users found!'})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # NOTE: use simple pending check if caching to avoid lock during update
        if caching:
            pending_updates = pending_vgrids_update(configuration) or \
                pending_users_update(configuration)
        else:
            pending_updates = False
        if pending_updates:
            logger.debug("found pending cache updates: %s" % pending_updates)
        else:
            logger.debug("no pending cache updates")

        for (visible_user_id, user_dict) in visible_user.items():
            user_id = visible_user_id
            if visible_user_id in anon_map.keys():
                # Maintain user anonymity
                pretty_id = 'Anonymous user with unique ID %s' % visible_user_id
                user_id = anon_map[visible_user_id]
            else:
                # Show user-friendly version of user ID
                hide_email = user_dict.get(CONF, {}).get('HIDE_EMAIL_ADDRESS',
                                                         True)
                pretty_id = pretty_format_user(user_id, hide_email)
            anon_img = "%s/anonymous.png" % configuration.site_images
            avatar_size = 32
            user_obj = {'object_type': 'user', 'name': visible_user_id,
                        'pretty_id': pretty_id, 'avatar_url': anon_img}
            user_obj.update(user_dict)
            # NOTE: datetime is not json-serializable so we force to string
            created = user_obj.get(CONF, {}).get('CREATED_TIMESTAMP', '')
            if created:
                user_obj[CONF]['CREATED_TIMESTAMP'] = str(created)
            # TODO: consider ALWAYS using anon_id format in link here
            user_obj['userdetailslink'] = \
                {'object_type': 'link',
                 'destination':
                 'viewuser.py?cert_id=%s'
                 % quote(visible_user_id),
                 'class': 'infolink iconspace',
                 'title': 'View details for %s' %
                 visible_user_id,
                 'text': ''}
            vgrids_allow_email = user_dict[CONF].get('VGRIDS_ALLOW_EMAIL', [])
            vgrids_allow_im = user_dict[CONF].get('VGRIDS_ALLOW_IM', [])
            if any_vgrid in vgrids_allow_email:
                email_vgrids = vgrid_access
            else:
                email_vgrids = set(
                    vgrids_allow_email).intersection(vgrid_access)

            if email_vgrids and configuration.site_enable_gravatars:
                visible_email = extract_field(user_id, 'email')
                user_obj['avatar_url'] = user_gravatar_url(
                    configuration, visible_email, avatar_size)

            if any_vgrid in vgrids_allow_im:
                im_vgrids = vgrid_access
            else:
                im_vgrids = set(vgrids_allow_im).intersection(vgrid_access)
            for proto in configuration.notify_protocols:
                if not email_vgrids and proto == 'email':
                    continue
                if not im_vgrids and proto != 'email':
                    continue
                if user_obj[CONF].get(proto.upper(), None):
                    link = 'send%slink' % proto
                    user_obj[link] = {
                        'object_type': 'link',
                        'destination':
                        "javascript: confirmDialog(%s, '%s', '%s', %s);"
                        % ('sendmsg', 'Really send %s message to %s?'
                           % (proto, visible_user_id),
                           'request_text',
                           "{cert_id: '%s', 'protocol': '%s'}" %
                           (visible_user_id, proto)),
                        'class': "%s iconspace" % link,
                        'title': 'Send %s message to %s' %
                        (proto, visible_user_id),
                        'text': ''}
            logger.debug("append user %s" % user_obj)
            users.append(user_obj)

    if operation == "show":
        # insert dummy placeholder to build table
        user_obj = {'object_type': 'user', 'name': ''}
        users.append(user_obj)

    output_objects.append({'object_type': 'user_list',
                           'pending_updates': pending_updates,
                           'users': users})

    logger.info("%s %s end for %s" % (op_name, operation, client_id))
    return (output_objects, returnvalues.OK)
