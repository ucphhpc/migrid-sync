#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# viewuser - Display public details about a user
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

"""Get info about a user"""
from __future__ import absolute_import

import hashlib
import os
from binascii import hexlify
from urllib import urlencode

from mig.shared import returnvalues
from mig.shared.base import client_id_dir, pretty_format_user, extract_field
from mig.shared.defaults import any_vgrid, csrf_field
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.html import confirm_js, confirm_html, html_post_helper
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.output import html_link
from mig.shared.profilekeywords import get_profile_specs
from mig.shared.settingskeywords import get_settings_specs
from mig.shared.user import user_gravatar_url, inline_image
from mig.shared.vgrid import vgrid_request_and_job_match
from mig.shared.vgridaccess import user_visible_user_confs, user_vgrid_access, \
    CONF


def signature():
    """Signature of the main function"""

    defaults = {'cert_id': REJECT_UNSET}
    return ['user_info', defaults]


def build_useritem_object_from_user_dict(configuration, client_id,
                                         visible_user_id, user_home, user_dict,
                                         allow_vgrids):
    """Build a user object based on input user_dict"""

    profile_specs = get_profile_specs()
    user_specs = get_settings_specs()
    user_item = {
        'object_type': 'user_info',
        'user_id': visible_user_id,
        'fields': [],
    }
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
    if visible_user_id.find('@') != -1:
        show_user_id = pretty_format_user(visible_user_id)
        visible_email = extract_field(visible_user_id, 'email')
    else:
        show_user_id = visible_user_id
        if email_vgrids:
            visible_email = user_dict[CONF].get('EMAIL', [''])[0]
        else:
            visible_email = ''
    user_item['fields'].append(('Public user ID', show_user_id))

    public_image = user_dict[CONF].get('PUBLIC_IMAGE', [])
    public_image = [rel_path for rel_path in public_image if
                    os.path.exists(os.path.join(user_home, rel_path))]

    img_html = '<div class="public_image">'
    if not public_image:
        if configuration.site_enable_gravatars:
            gravatar_url = user_gravatar_url(configuration, visible_email, 256)
            img_html += '<img alt="portrait" class="profile-img" src="%s">' % \
                        gravatar_url
        else:
            img_html += '<span class="anonymous-profile-img"></span>'

    for rel_path in public_image:
        img_path = os.path.join(user_home, rel_path)
        img_data = inline_image(configuration, img_path)
        img_html += '<img alt="portrait" class="profile-img" src="%s">' % \
                    img_data
    img_html += '</div>'
    public_profile = user_dict[CONF].get('PUBLIC_PROFILE', [])
    if not public_profile:
        public_profile = ['No public information provided']
    profile_html = ''
    profile_html += '<br/>'.join(public_profile)
    profile_html += ''
    public_html = '<div class="">\n%s\n</div>' % profile_html
    profile_html += '<div class="clear"></div>'
    public_html += '<div class="public_frame">\n%s\n</div>' % img_html
    profile_html += '<div class="clear"></div>'
    user_item['fields'].append(('Public information', public_html))
    show_contexts = ['notify']
    for (key, val) in user_specs:
        proto = key.lower()
        if not val['Context'] in show_contexts:
            continue
        saved = user_dict[CONF].get(key, None)
        if val['Type'] != 'multiplestrings':
            saved = [saved]
        entry = ''
        if not email_vgrids and key == 'EMAIL':
            show_address = ' (email address hidden)'
        elif not im_vgrids and key != 'EMAIL':
            show_address = '(IM address hidden)'
        else:
            show_address = ', '.join(saved)
        if saved:
            form_method = 'post'
            csrf_limit = get_csrf_limit(configuration)
            target_op = 'sendrequestaction'
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            js_name = 'send%s%s' % (proto, hexlify(visible_user_id))
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'cert_id': visible_user_id,
                                       'request_type': 'plain',
                                       'protocol': proto,
                                       'request_text': '',
                                       csrf_field: csrf_token})
            entry += helper
            link = 'send%slink' % proto
            link_obj = {'object_type': 'link',
                        'destination':
                        "javascript: confirmDialog(%s, '%s', '%s');"
                        % (js_name, 'Send %s message to %s'
                           % (proto, visible_user_id),
                           'request_text'),
                        'class': link,
                        'title': 'Send %s message to %s' %
                        (proto, visible_user_id),
                        'text': show_address}
            entry += "%s " % html_link(link_obj)
        user_item['fields'].append((val['Title'], entry))
    return user_item


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
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
    title_entry['text'] = 'People'

    # jquery support for confirmation-style popup:
    (add_import, add_init, add_ready) = confirm_js(configuration)

    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    output_objects.append({'object_type': 'html_form',
                           'text': confirm_html(configuration)})

    user_list = accepted['cert_id']

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep
    status = returnvalues.OK

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'User details'
    output_objects.append({'object_type': 'header', 'text':
                           'Show user details'})

    visible_user = user_visible_user_confs(configuration, client_id)
    vgrid_access = user_vgrid_access(configuration, client_id)

    for visible_user_name in user_list:
        if not visible_user_name in visible_user.keys():
            logger.error("viewuser: invalid user %s" % visible_user_name)
            logger.debug("viewuser: %s not found in %s" %
                         (visible_user_name, visible_user.keys()))
            output_objects.append({'object_type': 'error_text',
                                   'text': 'invalid user %s' %
                                   visible_user_name})
            continue
        user_dict = visible_user[visible_user_name]
        user_item = build_useritem_object_from_user_dict(configuration,
                                                         client_id,
                                                         visible_user_name,
                                                         base_dir,
                                                         user_dict,
                                                         vgrid_access)
        output_objects.append(user_item)

    return (output_objects, status)
