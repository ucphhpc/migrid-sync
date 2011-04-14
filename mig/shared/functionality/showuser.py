#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showuser - Display a user
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

"""Get info about a user"""

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.profilekeywords import profilekeywords
from shared.user import is_user, get_user_dict
from shared.validstring import valid_dir_input


def signature():
    """Signature of the main function"""

    defaults = {'user_id': REJECT_UNSET}
    return ['user', defaults]


def build_useritem_object(configuration, user_dict):
    """Build a user object based on input user_dict"""

    profile_list = []
    prof = user_dict['PROFILE']
    prof_keywords = profilekeywords(configuration)
    if len(prof) > 0:
        for profile_item in prof:
            item = {'object_type': 'profile'}
            for key in prof_keywords.items():
                item[key] = profile_item.get(key, '')
            profile_list.append(item)

    # anything specified?

    notifications = []
    notify = user_dict['NOTIFY']
    if len(notify) > 0:
        for notify_item in notify:
            notifications.append({
                'object_type': 'notify',
                'name': notify_item['name'],
                'protocol': notify_item['protocol'],
                })
    return {
        'object_type': 'user',
        'user_id': user_dict['USERID'],
        'profile': profile_list,
        'notifications': notifications,
        }


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
    user_id = accepted['user_id'][-1]

    if not valid_dir_input(configuration.user_home, user_id):
        logger.warning(
            "possible illegal directory traversal attempt user_id '%s'"
            % user_id)
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Illegal user name: "%s"'
                               % user_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not is_user(user_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                               : "'%s' is not an existing user!"
                               % user_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'User details'

    output_objects.append({'object_type': 'header', 'text'
                          : 'Show user details'})

    (user_dict, msg) = get_user_dict(user_id, configuration)
    if not user_dict:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Could not read details for "%s"' % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append(build_useritem_object(configuration, user_dict))

    return (output_objects, returnvalues.OK) 
