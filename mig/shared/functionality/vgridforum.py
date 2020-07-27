#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridforum - Access VGrid private forum for owners and members
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Access to a VGrid forum stored in a given vgrids private_base dir if the
client is an owner or a member of the vgrid. Members are allowed to read
private files but not write them, therefore they don't have a private_base
link where they can access them like owners do.
"""
from __future__ import absolute_import

import os

from .shared import returnvalues
from .shared.forum import list_single_thread, list_threads, reply, new_subject, \
    search_threads, toggle_subscribe, list_subscribers
from .shared.functional import validate_input_and_cert, REJECT_UNSET
from .shared.handlers import safe_handler, get_csrf_limit
from .shared.html import themed_styles
from .shared.init import initialize_main_variables, find_entry
from .shared.notification import notify_user_thread
from .shared.vgrid import vgrid_is_owner_or_member

get_actions = ['show_all', 'show_thread', 'search']
post_actions = ['new_thread', 'reply', 'toggle_subscribe']
valid_actions = get_actions + post_actions
default_pager_entries = 20


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'action': ['show_all'],
                'thread': [''], 'msg_subject': [''], 'msg_body': ['']}
    return ['forumview', defaults]


def notify_subscribers(configuration, forum_base, vgrid_name, thread, author,
                       url):
    """Send notifications to all users subscribing to forum in forum_base"""
    subscribers = list_subscribers(forum_base, thread)
    threads = []
    notify = []
    for proto in configuration.notify_protocols:
        notify.append('%s: SETTINGS' % proto)

    for target in subscribers:
        job_dict = {'NOTIFY': notify, 'JOB_ID': 'NOJOBID', 'USER_CERT': target}
        notifier = notify_user_thread(
            job_dict,
            [vgrid_name, author, url],
            'FORUMUPDATE',
            configuration.logger,
            '',
            configuration,
        )
        notifier.join(0)
        threads.append(notifier)

    for notifier in threads:
        # Try finishing delivery but do not block forever on one message
        notifier.join(30)


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = '%s Forum' % label
    user_settings = title_entry.get('user_settings', {})
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

    vgrid_name = accepted['vgrid_name'][-1]
    action = accepted['action'][-1]
    thread = accepted['thread'][-1]
    msg_subject = accepted['msg_subject'][-1].strip()
    msg_body = accepted['msg_body'][-1].strip()

    if not vgrid_is_owner_or_member(vgrid_name, client_id,
                                    configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''You must be an owner or member of %s %s to
access the forum.''' % (vgrid_name, label)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text': 'Invalid action "%s" (supported: %s)' %
                               (action, ', '.join(valid_actions))})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action in post_actions:
        if not safe_handler(configuration, 'post', op_name, client_id,
                            get_csrf_limit(configuration), accepted):
            output_objects.append(
                {'object_type': 'error_text', 'text': '''Only accepting
                CSRF-filtered POST requests to prevent unintended updates'''
                 })
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.vgrid_private_base,
                                            vgrid_name)) + os.sep

    forum_base = os.path.abspath(os.path.join(base_dir, '.vgridforum'))

    # TODO: can we update style inline to avoid explicit themed_styles?
    title_entry['style'] = themed_styles(configuration, advanced=['forum.css'],
                                         user_settings=user_settings)
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>
    '''
    add_init = '''
function toggle_new(form_elem_id, link_elem_id) {
    form_elem = document.getElementById(form_elem_id);
    form_focus = document.getElementById(form_elem_id + "_main");
    link_elem = document.getElementById(link_elem_id);
    if (!form_elem || !link_elem)
        return;
    if (form_elem.style.display != 'block') {
        form_elem.style.display = 'block';
        form_focus.focus();
        link_elem.style.display = 'none';
    } else {
        form_elem.style.display = 'none';
        link_elem.style.display = 'block';
        link_elem.focus();
    }
}
    '''
    add_ready = '''
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

          // table initially sorted by 0 (last update / date) 
          var sortOrder = [[0,1]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }

          $("#forumtable").tablesorter({widgets: ["zebra"],
                                        sortList:sortOrder,
                                        textExtraction: imgTitle
                                        })
                               .tablesorterPager({ container: $("#pager"),
                                        size: %s
                                        });
          $("#pagerrefresh").click(function() { location.reload(); });
    ''' % default_pager_entries
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'html_form',
                           'text': '''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="72" rows="10" id="confirm_input" style="display:none;"></textarea>
 </div>
'''})

    output_objects.append({'object_type': 'sectionheader', 'text':
                           '%s Forum for %s' % (label, vgrid_name)})

    try:
        os.makedirs(forum_base)
    except:
        pass
    if not os.path.isdir(forum_base):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''No forum available for %s!''' % vgrid_name})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    post_error = None
    msg = ''

    logger.info("vgridforum %s %s %s" % (vgrid_name, action, thread))

    if action in post_actions:
        if action == 'new_thread':
            try:
                (thread_hash, msg) = new_subject(forum_base, client_id,
                                                 msg_subject, msg_body)
                query = 'vgrid_name=%s&action=show_thread&thread=%s'\
                        % (vgrid_name, thread_hash)
                url = "%s?%s" % (os.environ['SCRIPT_URI'], query)
                notify_subscribers(configuration, forum_base, vgrid_name, '',
                                   client_id, url)
                thread = thread_hash
            except ValueError as error:
                post_error = str(error)
        elif action == 'reply':
            try:
                (thread_hash, msg) = reply(forum_base, client_id, msg_body,
                                           thread)
                query = 'vgrid_name=%s&action=show_thread&thread=%s'\
                        % (vgrid_name, thread_hash)
                url = "%s?%s" % (os.environ['SCRIPT_URI'], query)
                notify_subscribers(configuration, forum_base, vgrid_name, '',
                                   client_id, url)
                notify_subscribers(configuration, forum_base, vgrid_name,
                                   thread_hash, client_id, url)
            except ValueError as error:
                post_error = str(error)
        elif action == 'toggle_subscribe':
            try:
                msg = toggle_subscribe(forum_base, client_id, thread)
            except ValueError as error:
                post_error = str(error)
        else:
            msg = 'unexpected action: %s' % action

    if action == 'search':
        thread_list = search_threads(forum_base, msg_subject,
                                     msg_body, client_id)
        msg = "Found %d thread(s) matching subject '%s'" % (len(thread_list),
                                                            msg_subject)
    elif thread:
        try:
            message_list = list_single_thread(forum_base, thread, client_id)
        except ValueError as error:
            post_error = str(error)
    else:
        thread_list = list_threads(forum_base, client_id)

    if post_error:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Error handling %s forum operation: %s' %
                               (label, post_error)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if thread:
        output_objects.append({'object_type': 'table_pager',
                               'entry_name': 'messages',
                               'default_entries': default_pager_entries})
        output_objects.append({'object_type': 'forum_thread_messages',
                               'messages': message_list, 'status': msg,
                               'vgrid_name': vgrid_name, 'thread': thread})
    else:
        output_objects.append({'object_type': 'table_pager',
                               'entry_name': 'threads',
                               'default_entries': default_pager_entries})
        output_objects.append({'object_type': 'forum_threads',
                               'threads': thread_list, 'status': msg,
                               'vgrid_name': vgrid_name})
    return (output_objects, returnvalues.OK)
