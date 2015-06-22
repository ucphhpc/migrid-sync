#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# viewuser - Display public details about a user
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

import base64
import os
from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import any_vgrid
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.html import html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.output import html_link
from shared.profilekeywords import get_profile_specs
from shared.settingskeywords import get_settings_specs
from shared.vgrid import vgrid_request_and_job_match
from shared.vgridaccess import user_visible_user_confs, user_allowed_vgrids, \
     CONF


def signature():
    """Signature of the main function"""

    defaults = {'cert_id': REJECT_UNSET}
    return ['user_info', defaults]

def inline_image(path):
    """Create inline image base64 string from file in path"""
    data = 'data:image/%s;base64,' % os.path.splitext(path)[1].strip('.')
    data += base64.b64encode(open(path).read())
    return data

def build_useritem_object_from_user_dict(configuration, visible_user_id,
                                         user_home, user_dict, allow_vgrids):
    """Build a user object based on input user_dict"""

    profile_specs = get_profile_specs()
    user_specs = get_settings_specs()
    user_item = {
        'object_type': 'user_info',
        'user_id': visible_user_id,
        'fields': [],
        }
    user_item['fields'].append(('Public user ID', visible_user_id))
    user_image = True
    public_image = user_dict[CONF].get('PUBLIC_IMAGE', [])
    if not public_image:
        user_image = False
        public_image = ['/images/anonymous.png']
    img_html = '<div class="public_image">'
    for img_path in public_image:
        if user_image:
            img_data = inline_image(os.path.join(user_home, img_path))
        else:
            img_data = img_path
        img_html += '<img alt="portrait" src="%s">' % img_data
    img_html += '</div>'
    public_profile = user_dict[CONF].get('PUBLIC_PROFILE', [])
    if not public_profile:
        public_profile = ['No public information provided']
    profile_html = '<div class="public_profile">'
    profile_html += '<br />'.join(public_profile)
    profile_html += '</div>'
    public_html = '<div class="public_frame">\n%s\n%s\n</div>' % (profile_html,
                                                                  img_html)
    profile_html += '<div class="clear"></div>'
    user_item['fields'].append(('Public information', public_html))
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
        proto = key.lower()
        if not val['Context'] in show_contexts:
            continue
        saved = user_dict[CONF].get(key, None)
        if val['Type'] != 'multiplestrings':
            saved = [saved]
        entry = ''
        if not email_vgrids and key == 'EMAIL':
            show_address = '(email address hidden)'
        elif not im_vgrids and key != 'EMAIL':
            show_address = '(IM address hidden)'
        else:
            show_address = ', '.join(saved)
        if saved:
            js_name = 'send%s%s' % (proto, hexlify(visible_user_id))
            helper = html_post_helper(js_name, 'sendrequestaction.py',
                                      {'cert_id': visible_user_id,
                                       'request_type': 'plain',
                                       'protocol': proto,
                                       'request_text': ''})
            entry += helper            
            link = 'send%slink' % proto
            link_obj = {'object_type': 'link',
                        'destination':
                        "javascript: confirmDialog(%s, '%s', '%s');"\
                        % (js_name, 'Send %s message to %s'\
                           % (proto, visible_user_id),
                           'request_text'),
                        'class': link,
                        'title': 'Send %s message to %s' % \
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

    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>

<script type="text/javascript" >

$(document).ready(function() {

          // init confirmation dialog
          $( "#confirm_dialog" ).dialog(
              // see http://jqueryui.com/docs/dialog/ for options
              { autoOpen: false,
                modal: true, closeOnEscape: true,
                width: 640,
                buttons: {
                   "Cancel": function() { $( "#" + name ).dialog("close"); }
                }
              });
     }
);
</script>
'''

    output_objects.append({'object_type': 'html_form',
                           'text':'''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="72" rows="10" id="confirm_input" style="display:none;"></textarea>
 </div>
'''                       })

    user_list = accepted['cert_id']

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep
    status = returnvalues.OK

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'User details'
    output_objects.append({'object_type': 'header', 'text'
                          : 'Show user details'})

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
                                                         base_dir,
                                                         user_dict,
                                                         allowed_vgrids)
        output_objects.append(user_item)
        
    return (output_objects, status)
