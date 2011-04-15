#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# viewuser - Display public details about a user
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

"""Get info about a user"""

import shared.returnvalues as returnvalues
from shared.defaults import any_vgrid
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.settingskeywords import get_keywords_dict
from shared.vgrid import vgrid_request_and_job_match
from shared.vgridaccess import user_visible_user_confs, user_allowed_vgrids, \
     CONF


def signature():
    """Signature of the main function"""

    defaults = {'cert_id': REJECT_UNSET}
    return ['user_info', defaults]


def build_useritem_object_from_user_dict(configuration, user_id,
                                       user_dict, allow_vgrids):
    """Build a user object based on input user_dict"""

    user_keywords = get_keywords_dict()
    user_item = {
        'object_type': 'user_info',
        'user_id': user_id,
        'fields': [],
        }
    user_item['fields'].append(('Public user ID', user_id))
    visible_vgrids = user_dict[CONF].get('VISIBLE_VGRIDS', [])
    if any_vgrid in visible_vgrids:
        shared_vgrids = allow_vgrids
    else:
        shared_vgrids = set(visible_vgrids).intersection(allow_vgrids)
    show_contexts = ['notify']
    if shared_vgrids:
        for (key, val) in user_keywords.items():
            if not val['Context'] in show_contexts:
                continue
            entry = user_dict[CONF].get(key, 'unknown')
            if val['Type'] == 'multiplestrings':
                entry = ' '.join(entry)
            if entry:
                user_item['fields'].append((user_keywords[key]['Title'], entry))
    else:
        user_item['fields'].append(('User settings prevent communication info',
                                    'hiding notification details'))
    return user_item


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'User details'
    output_objects.append({'object_type': 'header', 'text'
                          : 'Show user details'})

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
    user_list = accepted['cert_id']
    status = returnvalues.OK
    visible_user = user_visible_user_confs(configuration, client_id)
    allowed_vgrids = user_allowed_vgrids(configuration, client_id)

    for visible_user_name in user_list:
        if not visible_user_name in visible_user.keys():
            output_objects.append({'object_type': 'error_text',
                                   'text': 'invalid user %s (%s)' % \
                                   (visible_user_name, visible_user)})
            continue
        user_dict = visible_user[visible_user_name]
        user_item = build_useritem_object_from_user_dict(configuration,
                                                      visible_user_name,
                                                      user_dict,
                                                      allowed_vgrids)
        output_objects.append(user_item)
        
    return (output_objects, status)
