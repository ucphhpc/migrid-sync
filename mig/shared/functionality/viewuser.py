#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# viewuser - Display public details about a user
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
from shared.defaults import any_vgrid
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.profilekeywords import get_profile_specs
from shared.settingskeywords import get_settings_specs
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

    profile_specs = get_profile_specs()
    user_specs = get_settings_specs()
    user_item = {
        'object_type': 'user_info',
        'user_id': user_id,
        'fields': [],
        }
    user_item['fields'].append(('Public user ID', user_id))
    public_image = user_dict[CONF].get('PUBLIC_IMAGE', [])
    if not public_image:
        public_image = ['/images/anonymous.png']
    img_html = '<div class="public_image">'
    for img_path in public_image:
        img_html += '<img src="%s"' % img_path
    img_html += '</div>'
    user_item['fields'].append(('Public image', img_html))
    public_profile = user_dict[CONF].get('PUBLIC_PROFILE', [])
    if not public_profile:
        public_profile = ['No public information provided']
    profile_html = '<div class="public_profile">'
    profile_html += '<br />'.join(public_profile)
    profile_html += '</div>'    
    user_item['fields'].append(('Public information', profile_html))
    vgrids_allow_email = user_dict[CONF].get('VGRIDS_ALLOW_EMAIL', [])
    vgrids_allow_im = user_dict[CONF].get('VGRIDS_ALLOW_IM', [])
    hide_email = user_dict[CONF].get('HIDE_EMAIL_ADDRESS', True)
    hide_im = user_dict[CONF].get('HIDE_IM_ADDRESS', True)
    if hide_email:
        email_vgrids = []
    elif any_vgrid in vgrids_allow_email:
        email_vgrids = allow_vgrids
    else:
        email_vgrids = set(vgrids_allow_email).intersection(allow_vgrids)
    if hide_im:
        im_vgrids = []
    elif any_vgrid in vgrids_allow_im:
        im_vgrids = allow_vgrids
    else:
        im_vgrids = set(vgrids_allow_im).intersection(allow_vgrids)
    show_contexts = ['notify']
    for (key, val) in user_specs:
        if not val['Context'] in show_contexts:
            continue
        if not email_vgrids and key == 'EMAIL':
            entry = 'User settings prevent display of email address'
        elif not im_vgrids and key != 'EMAIL':
            entry = 'User settings prevent display of IM address'
        else:
            entry = user_dict[CONF].get(key, None)
            if val['Type'] == 'multiplestrings':
                entry = ' '.join(entry)
        user_item['fields'].append((val['Title'], entry))
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
