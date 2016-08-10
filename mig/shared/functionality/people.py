#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# people - view and communicate with other users
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

"""View and communicate with other users that allow it"""

from urllib import quote

import shared.returnvalues as returnvalues
from shared.defaults import default_pager_entries, any_vgrid, csrf_field
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import jquery_ui_js, man_base_js, man_base_html, \
     html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.user import anon_to_real_user_map
from shared.vgridaccess import user_visible_user_confs, user_allowed_vgrids, \
     CONF

list_operations = ['showlist', 'list']
show_operations = ['show', 'showlist']
allowed_operations = list(set(list_operations + show_operations))

def signature():
    """Signature of the main function"""

    defaults = {'operation': ['show']}
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
    
    if not operation in allowed_operations:
        output_objects.append({'object_type': 'text', 'text':
                               '''Operation must be one of %s.''' % \
                               ', '.join(allowed_operations)})
        return (output_objects, returnvalues.OK)

    logger.info("%s %s begin for %s" % (op_name, operation, client_id))
    if operation in show_operations:

        # jquery support for tablesorter and confirmation on "send"
        # table initially sorted by 0 (name)

        refresh_call = 'ajax_people(%s)' % configuration.notify_protocols
        table_spec = {'table_id': 'usertable', 'sort_order': '[[0,0]]',
                      'refresh_call': refresh_call}
        (add_import, add_init, add_ready) = man_base_js(configuration,
                                                        [table_spec],
                                                        {'width': 640})
        if operation == "show":
            add_ready += refresh_call
        title_entry['style'] = themed_styles(configuration)
        title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                                 add_init, add_ready)

        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})

        output_objects.append({'object_type': 'header', 'text'
                              : 'People'})

        output_objects.append(
            {'object_type': 'text', 'text' :
             'View and communicate with other users.'
             })

        output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'All users'})

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
        # TODO: next 3 call are slow because we reload pickles and maps
        visible_user = user_visible_user_confs(configuration, client_id)
        allow_vgrids = user_allowed_vgrids(configuration, client_id)
        anon_map = anon_to_real_user_map(configuration)
        if not visible_user:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'no users found!'})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        for (visible_user_id, user_dict) in visible_user.items():
            user_id = visible_user_id
            if visible_user_id in anon_map.keys():
                user_id = anon_map[visible_user_id]
            user_obj = {'object_type': 'user', 'name': visible_user_id}
            user_obj.update(user_dict)
            # NOTE: datetime is not json-serializable so we force to string
            created = user_obj.get(CONF, {}).get('CREATED_TIMESTAMP', '')
            if created:
                user_obj[CONF]['CREATED_TIMESTAMP'] = str(created)
            user_obj['userdetailslink'] = \
                                        {'object_type': 'link',
                                         'destination':
                                         'viewuser.py?cert_id=%s'\
                                         % quote(visible_user_id),
                                         'class': 'infolink iconspace',
                                         'title': 'View details for %s' % \
                                         visible_user_id, 
                                         'text': ''}
            vgrids_allow_email = user_dict[CONF].get('VGRIDS_ALLOW_EMAIL', [])
            vgrids_allow_im = user_dict[CONF].get('VGRIDS_ALLOW_IM', [])
            if any_vgrid in vgrids_allow_email:
                email_vgrids = allow_vgrids
            else:
                email_vgrids = set(vgrids_allow_email).intersection(allow_vgrids)
            if any_vgrid in vgrids_allow_im:
                im_vgrids = allow_vgrids
            else:
                im_vgrids = set(vgrids_allow_im).intersection(allow_vgrids)
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
                        "javascript: confirmDialog(%s, '%s', '%s', %s);"\
                        % ('sendmsg', 'Really send %s message to %s?'\
                           % (proto, visible_user_id),
                           'request_text',
                           "{cert_id: '%s', 'protocol': '%s'}" % \
                           (visible_user_id, proto)),
                        'class': "%s iconspace" % link,
                        'title': 'Send %s message to %s' % \
                        (proto, visible_user_id), 
                        'text': ''}
            logger.debug("append user %s" % user_obj)
            users.append(user_obj)

    if operation == "show":
        # insert dummy placeholder to build table
        user_obj = {'object_type': 'user', 'name': ''}
        users.append(user_obj)

    output_objects.append({'object_type': 'user_list',
                          'users': users})

    logger.info("%s %s end for %s" % (op_name, operation, client_id))
    return (output_objects, returnvalues.OK)


