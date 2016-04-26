#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sharelink - backend to create and manage share links
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

"""Create and manage external sharing links"""

from binascii import hexlify
import os
import datetime

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.sharelinks import build_sharelinkitem_object, load_share_links, \
     create_share_link, update_share_link, delete_share_link
from shared.defaults import  default_pager_entries, keyword_owners, \
     keyword_members
from shared.functional import validate_input_and_cert
from shared.handlers import correct_handler
from shared.html import html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.notification import notify_user_thread
from shared.pwhash import make_hash
from shared.sharelinks import create_share_link_form, invite_share_link_form, \
     invite_share_link_message, generate_sharelink_id 
from shared.validstring import valid_user_path
from shared.vgrid import in_vgrid_share, vgrid_is_owner, vgrid_settings


get_actions = ['show', 'edit']
post_actions = ['create', 'update', 'delete']
valid_actions = get_actions + post_actions
enabled_strings = ('on', 'yes', 'true')

def signature():
    """Signature of the main function"""

    defaults = {'action': ['show'], 'share_id': [''], 'path': [''],
                'read_access':[''], 'write_access':[''], 'expire': [''],
                'password':[''], 'invite': [''], 'msg': ['']}
    return ['text', defaults]

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

    action = accepted['action'][-1]
    share_id = accepted['share_id'][-1]
    path = os.path.normpath(accepted['path'][-1])
    read_access = accepted['read_access'][-1].lower() in enabled_strings
    write_access = accepted['write_access'][-1].lower() in enabled_strings
    expire = accepted['expire'][-1]
    password = accepted['password'][-1]
    # Merge and split invite to make sure 'a@b, c@d' entries are handled
    invite_list = ','.join(accepted['invite']).split(',')
    invite_list = [i for i in invite_list if i]
    invite_msg = accepted['msg']
    
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Share Link'

    # jquery support for tablesorter and confirmation on delete/redo:

    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] += '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.widgets.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>

<script type="text/javascript">
    $(document).ready(function() {
        // init confirmation dialog
        $( "#confirm_dialog" ).dialog(
              // see http://jqueryui.com/docs/dialog/ for options
              { autoOpen: false,
                modal: true, closeOnEscape: true,
                width: 600,
                buttons: {
                   "Cancel": function() { $( "#" + name ).dialog("close"); }
                }
        });

        /* init create dialog */
        /* setup table with tablesorter initially sorted by 3 (created) */
        var sortOrder = [[3,0]];
        $("#sharelinkstable").tablesorter({widgets: ["zebra", "saveSort"],
                                        sortList:sortOrder
                                        })
                               .tablesorterPager({ container: $("#pager"),
                                        size: %s
                                        });
        $("#pagerrefresh").click(function() { location.reload(); });
    });
</script>
''' % default_pager_entries
    header_entry = {'object_type': 'header', 'text'
                           : 'Manage share links'}
    output_objects.append(header_entry)

    if not configuration.site_enable_sharelinks:
        output_objects.append({'object_type': 'text', 'text': '''
Share links are disabled on this site.
Please contact the Grid admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    output_objects.append({'object_type': 'html_form',
                           'text':'''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="40" rows="4" id="confirm_input"
       style="display:none;"></textarea>
 </div>
'''                       })

    logger.info('sharelink %s from %s' % (action, client_id))
    logger.debug('sharelink from %s: %s' % (client_id, accepted))

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid action "%s" (supported: %s)' % \
                               (action, ', '.join(valid_actions))})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action in post_actions:
        if not correct_handler('POST'):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : 'Only accepting POST requests to prevent unintended updates'})
            return (output_objects, returnvalues.CLIENT_ERROR)

    (load_status, share_map) = load_share_links(configuration, client_id)
    if not load_status:
        share_map = {}

    if action in get_actions:
        if action == "show":
            sharelinks = []
            for (saved_id, share_dict) in share_map.items():
                share_item = build_sharelinkitem_object(configuration,
                                                        share_dict)
                js_name = 'delete%s' % hexlify(saved_id)
                helper = html_post_helper(js_name, 'sharelink.py',
                                          {'share_id': saved_id,
                                           'action': 'delete'})
                output_objects.append({'object_type': 'html_form', 'text': helper})
                share_item['delsharelink'] = {
                    'object_type': 'link', 'destination':
                    "javascript: confirmDialog(%s, '%s');" % \
                    (js_name, 'Really remove %s?' % saved_id),
                    'class': 'removelink iconspace', 'title': 'Remove share link %s' % \
                    saved_id, 'text': ''}
                sharelinks.append(share_item)

            # Display share links and form to add new ones

            output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Share Links'})
            output_objects.append({'object_type': 'table_pager',
                                   'entry_name': 'share links',
                                   'default_entries': default_pager_entries})
            output_objects.append({'object_type': 'sharelinks', 'sharelinks'
                                  : sharelinks})

            output_objects.append({'object_type': 'html_form', 'text': '<br/>'})
            output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Create Share Link'})
            submit_button = '''<span>
    <input type=submit value="Create share link" />
    </span>'''
            sharelink_html = create_share_link_form(configuration, client_id,
                                                    'html', submit_button)
            output_objects.append({'object_type': 'html_form', 'text'
                                  : sharelink_html})
        elif action == "edit":
            header_entry['text'] = 'Edit Share Link'
            share_dict = share_map.get(share_id, {})
            if not share_dict:
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': 'existing share link is required for edit'})
                return (output_objects, returnvalues.CLIENT_ERROR)

            output_objects.append({'object_type': 'html_form', 'text': '''
<p>
Here you can send invitations for your share link %(share_id)s to one or more
comma-separated recipients.
</p>
                                   ''' % share_dict
                                   })
            sharelinks = []
            share_item = build_sharelinkitem_object(configuration,
                                                    share_dict)
            saved_id = share_item['share_id']
            js_name = 'delete%s' % hexlify(saved_id)
            helper = html_post_helper(js_name, 'sharelink.py',
                                      {'share_id': saved_id,
                                       'action': 'delete'})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            # Hide link to self
            del share_item['editsharelink']
            share_item['delsharelink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" % \
                (js_name, 'Really remove %s?' % saved_id),
                'class': 'removelink iconspace', 'title': 'Remove share link %s' % \
                saved_id, 'text': ''}
            sharelinks.append(share_item)
            output_objects.append({'object_type': 'sharelinks', 'sharelinks'
                                  : sharelinks})
            submit_button = '''<span>
    <input type=submit value="Send invitation(s)" />
    </span>'''
            sharelink_html = invite_share_link_form(configuration, client_id,
                                                    share_dict, 'html',
                                                    submit_button)
            output_objects.append({'object_type': 'html_form', 'text'
                                  : sharelink_html})
            output_objects.append({'object_type': 'link',
                                   'destination': 'sharelink.py',
                                   'text': 'Return to share link overview'})
            
        return (output_objects, returnvalues.OK)
    elif action in post_actions:
        share_dict = share_map.get(share_id, {})
        if not share_dict and action != 'create':
            logger.warning('%s tried to %s missing or not owned link %s!' % \
                               (client_id, action, share_id))
            output_objects.append(
                {'object_type': 'error_text',
                 'text': '%s requires existing share link' % action})
            return (output_objects, returnvalues.CLIENT_ERROR)

        share_path = share_dict.get('path', path)

        # Please note that base_dir must end in slash to avoid access to other
        # user dirs when own name is a prefix of another user name
        
        base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                                client_dir)) + os.sep
        
        abs_path = os.path.join(base_dir, path.lstrip(os.sep))

        if action == 'delete':
            header_entry['text'] = 'Delete Share Link'
            (save_status, _) = delete_share_link(share_id, client_id,
                                                 configuration,
                                                 share_map)
            desc = "delete"
        elif action == "update":
            header_entry['text'] = 'Update Share Link'
            if invite_list:
                invites = share_dict.get('invites', []) + invite_list
                invites_uniq = list(set([i for i in invites if i]))
                invites_uniq.sort()
                share_dict['invites'] = invites_uniq
                auto_msg = invite_share_link_message(configuration, client_id,
                                                     share_dict, 'html')
                msg = '\n'.join(invite_msg)
                # Now send request to all targets in turn
                threads = []
                for target in invite_list:
                    job_dict = {'NOTIFY': [target.strip()], 'JOB_ID': 'NOJOBID',
                                'USER_CERT': client_id}

                    logger.debug('invite %s to %s' % (target, share_id))
                    threads.append(notify_user_thread(
                        job_dict,
                        [auto_msg, msg],
                        'INVITESHARE',
                        logger,
                        '',
                        configuration,
                        )
                                            )
                    
                # Try finishing delivery but do not block forever on one message
                notify_done = [False for _ in threads]
                for _ in range(3):
                    for i in range(len(invite_list)):
                        if not notify_done[i]:
                            logger.debug('check done %s' % invite_list[i])
                            notify = threads[i]
                            notify.join(3)
                            notify_done[i] = not notify.isAlive()
                notify_sent, notify_failed = [], []
                for i in range(len(invite_list)):
                    if notify_done[i]:
                        notify_sent.append(invite_list[i])
                    else:
                        notify_failed.append(invite_list[i])
                logger.debug('notify sent %s, failed %s' % (notify_sent,
                                                            notify_failed))
                if notify_failed:
                    output_objects.append({'object_type': 'html_form', 'text':
                                           '''
<p>Failed to send invitation to %s</p>''' % ', '.join(notify_failed)
                                           })
                if notify_sent:
                    output_objects.append({'object_type': 'html_form', 'text':
                                           '''<p>Invitation sent to %s</p>
<textarea class="fillwidth padspace" rows="%d" readonly="readonly">
%s
%s
</textarea>
                                            ''' % (', '.join(notify_sent),
                                                   (auto_msg+msg).count('\n')+3,
                                                   auto_msg, msg)
                                           })
            if expire:
                share_dict['expire'] = expire
            if password:
                # Only store password hash on disk
                password_hash = make_hash(password)
                share_dict['password_hash'] = password_hash
            else:
                password_hash = share_dict.get("password_hash", "")
            (save_status, _) = update_share_link(share_dict, client_id,
                                                 configuration, share_map)
            desc = "update"
        elif action == "create":
            header_entry['text'] = 'Create Share Link'
            if not path:
                output_objects.append(
                    {'object_type': 'error_text', 'text'
                     : 'No path provided!'})
                return (output_objects, returnvalues.CLIENT_ERROR)
            elif not valid_user_path(abs_path, base_dir, True):
                logger.warning('%s tried to %s restricted path %s ! (%s)' % \
                               (client_id, action, abs_path, path))
                output_objects.append(
                    {'object_type': 'error_text', 'text'
                     : 'Illegal path "%s": you can only share your own data!'
                     % path
                     })
                return (output_objects, returnvalues.CLIENT_ERROR)
            elif not os.path.exists(abs_path):
                output_objects.append(
                    {'object_type': 'error_text', 'text'
                     : 'Provided path "%s" does not exist!' % path})
                return (output_objects, returnvalues.CLIENT_ERROR)
            vgrid_name = in_vgrid_share(configuration, abs_path)
            if vgrid_name is not None and \
                   not vgrid_is_owner(vgrid_name, client_id, configuration):
                # share is inside vgrid share so we must check that user is
                # permitted to create sharelinks there.
                (load_status, settings_dict) = vgrid_settings(vgrid_name,
                                                              configuration,
                                                              recursive=False,
                                                              as_dict=True)
                if not load_status:
                    # Probably owners just never saved settings, use defaults
                    settings_dict = {'vgrid_name': vgrid_name}
                allowed = settings_dict.get('create_sharelink', keyword_owners)
                if allowed != keyword_members:
                     output_objects.append(
                         {'object_type': 'error_text', 'text'
                          : 'You are not allowed to re-share %s %s shares!' % \
                          (vgrid_name, configuration.site_vgrid_label)})
                     return (output_objects, returnvalues.CLIENT_ERROR)

            if not read_access and not write_access:
                output_objects.append(
                    {'object_type': 'error_text', 'text'
                     : 'No access set!'})
                return (output_objects, returnvalues.CLIENT_ERROR)

            access_list = []
            if read_access:
                access_list.append('read')
            if write_access:
                access_list.append('write')

            share_mode = '-'.join((access_list + ['only'])[:2])

            # TODO: more validity checks here

            if share_dict:
                desc = "update"
            else:
                desc = "create"

            if password:
                # Only store password hash on disk
                password_hash = make_hash(password)
            else:
                password_hash = ''
            share_dict.update(
                {'path': path, 'access': access_list, 'expire': expire,
                 'password_hash': password_hash, 'invites': invite_list})
            if not share_id:
                # Make share with random ID and retry a few times on collision
                for i in range(3):
                    share_id = generate_sharelink_id(configuration, share_mode)
                    share_dict['share_id']  = share_id
                    (save_status, save_msg) = create_share_link(share_dict,
                                                                client_id,
                                                                configuration,
                                                                share_map)
                    if save_status:
                        logger.info('created sharelink: %s' % share_dict)
                        break
                    else:
                        # ID Collision?
                        logger.warning('could not create sharelink: %s' % \
                                       save_msg)
        else:
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : 'No such action %s' % (action)})
            return (output_objects, returnvalues.CLIENT_ERROR)

        if not save_status:
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : 'Error in %s share link %s: ' % (desc, share_id) + \
                 'save updated share links failed!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

        output_objects.append({'object_type': 'text', 'text'
                               : '%sd share link %s on %s .' % (desc.title(),
                                                                share_id,
                                                                share_path)})
        if action in ['create', 'update']:
            sharelinks = []
            share_item = build_sharelinkitem_object(configuration,
                                                    share_dict)
            saved_id = share_item['share_id']
            js_name = 'delete%s' % hexlify(saved_id)
            helper = html_post_helper(js_name, 'sharelink.py',
                                      {'share_id': saved_id,
                                       'action': 'delete'})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            share_item['delsharelink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" % \
                (js_name, 'Really remove %s?' % saved_id),
                'class': 'removelink iconspace', 'title': 'Remove share link %s' % \
                saved_id, 'text': ''}
            sharelinks.append(share_item)
            output_objects.append({'object_type': 'sharelinks', 'sharelinks'
                                  : sharelinks})
            if action == 'create':
                # NOTE: Leave editsharelink here for use in fileman overlay
                #del share_item['editsharelink']
                output_objects.append({'object_type': 'html_form', 'text':
                                       '<br />'})
                submit_button = '''<span>
            <input type=submit value="Send invitation(s)" />
            </span>'''
                invite_html = invite_share_link_form(configuration, client_id,
                                                     share_dict, 'html',
                                                     submit_button)
                output_objects.append({'object_type': 'html_form', 'text':
                                       invite_html})
    else:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Invalid share link action: %s' % action})
        return (output_objects, returnvalues.CLIENT_ERROR)
                
    output_objects.append({'object_type': 'html_form', 'text': '<br />'})
    output_objects.append({'object_type': 'link',
                           'destination': 'sharelink.py',
                           'text': 'Return to share link overview'})
    return (output_objects, returnvalues.OK)

