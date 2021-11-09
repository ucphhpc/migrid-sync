#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sharelink - backend to create and manage share links
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

from __future__ import absolute_import

from binascii import hexlify
import os
import datetime

from mig.shared import returnvalues
from mig.shared.base import client_id_dir, extract_field
from mig.shared.defaults import default_pager_entries, keyword_owners, \
    keyword_members, csrf_field
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from mig.shared.html import man_base_js, man_base_html, html_post_helper
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.notification import notify_user_thread
from mig.shared.pwhash import make_hash
from mig.shared.sharelinks import build_sharelinkitem_object, load_share_links, \
    create_share_link, update_share_link, delete_share_link, \
    create_share_link_form, invite_share_link_form, \
    invite_share_link_message, generate_sharelink_id
from mig.shared.validstring import valid_user_path
from mig.shared.vgrid import in_vgrid_share, vgrid_is_owner, vgrid_settings, \
    vgrid_add_sharelinks, vgrid_remove_sharelinks
from mig.shared.vgridaccess import is_vgrid_parent_placeholder


get_actions = ['show', 'edit']
post_actions = ['create', 'update', 'delete']
valid_actions = get_actions + post_actions
enabled_strings = ('on', 'yes', 'true')


def signature():
    """Signature of the main function"""

    defaults = {'action': ['show'], 'share_id': [''], 'path': [''],
                'read_access': [''], 'write_access': [''], 'expire': [''],
                'invite': [''], 'msg': ['']}
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
        # NOTE: path cannot use wildcards here
        typecheck_overrides={}
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    action = accepted['action'][-1]
    share_id = accepted['share_id'][-1]
    path = accepted['path'][-1]
    read_access = accepted['read_access'][-1].lower() in enabled_strings
    write_access = accepted['write_access'][-1].lower() in enabled_strings
    expire = accepted['expire'][-1]
    # Merge and split invite to make sure 'a@b, c@d' entries are handled
    invite_list = ','.join(accepted['invite']).split(',')
    invite_list = [i for i in invite_list if i]
    invite_msg = accepted['msg']

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Share Link'

    # jquery support for tablesorter and confirmation on delete/redo:
    # table initially sorted by 5, 4 reversed (active first and in growing age)

    table_spec = {'table_id': 'sharelinkstable', 'sort_order':
                  '[[5,1],[4,1]]'}
    (add_import, add_init, add_ready) = man_base_js(configuration,
                                                    [table_spec],
                                                    {'width': 600})
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

    header_entry = {'object_type': 'header', 'text': 'Manage share links'}
    output_objects.append(header_entry)

    if not configuration.site_enable_sharelinks:
        output_objects.append({'object_type': 'text', 'text': '''
Share links are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    logger.info('sharelink %s from %s' % (action, client_id))
    logger.debug('sharelink from %s: %s' % (client_id, accepted))

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid action "%s" (supported: %s)' %
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

    (load_status, share_map) = load_share_links(configuration, client_id)
    if not load_status:
        share_map = {}

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = 'sharelink'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    if action in get_actions:
        if action == "show":
            # Table columns to skip
            skip_list = ['owner', 'single_file', 'expire']
            sharelinks = []
            for (saved_id, share_dict) in share_map.items():
                share_item = build_sharelinkitem_object(configuration,
                                                        share_dict)
                js_name = 'delete%s' % hexlify(saved_id)
                helper = html_post_helper(js_name, '%s.py' % target_op,
                                          {'share_id': saved_id,
                                           'action': 'delete',
                                           csrf_field: csrf_token})
                output_objects.append({'object_type': 'html_form', 'text':
                                       helper})
                share_item['delsharelink'] = {
                    'object_type': 'link', 'destination':
                    "javascript: confirmDialog(%s, '%s');" %
                    (js_name, 'Really remove %s?' % saved_id),
                    'class': 'removelink iconspace', 'title':
                    'Remove share link %s' % saved_id, 'text': ''}
                sharelinks.append(share_item)

            # Display share links and form to add new ones

            output_objects.append(
                {'object_type': 'sectionheader', 'text': 'Share Links'})
            output_objects.append({'object_type': 'table_pager',
                                   'entry_name': 'share links',
                                   'default_entries': default_pager_entries})
            output_objects.append(
                {'object_type': 'sharelinks', 'sharelinks': sharelinks,
                 'skip_list': skip_list})

            output_objects.append(
                {'object_type': 'html_form', 'text': '<br/>'})
            output_objects.append(
                {'object_type': 'sectionheader', 'text': 'Create Share Link'})
            submit_button = '''<span>
    <input type=submit value="Create share link" />
    </span>'''
            sharelink_html = create_share_link_form(configuration, client_id,
                                                    'html', submit_button,
                                                    csrf_token)
            output_objects.append(
                {'object_type': 'html_form', 'text': sharelink_html})
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
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'share_id': saved_id,
                                       'action': 'delete',
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            # Hide link to self
            del share_item['editsharelink']
            share_item['delsharelink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" %
                (js_name, 'Really remove %s?' % saved_id),
                'class': 'removelink iconspace', 'title':
                'Remove share link %s' % saved_id, 'text': ''}
            sharelinks.append(share_item)
            output_objects.append(
                {'object_type': 'sharelinks', 'sharelinks': sharelinks})
            submit_button = '''<span>
    <input type=submit value="Send invitation(s)" />
    </span>'''
            sharelink_html = invite_share_link_form(configuration, client_id,
                                                    share_dict, 'html',
                                                    submit_button, csrf_token)
            output_objects.append(
                {'object_type': 'html_form', 'text': sharelink_html})
            output_objects.append({'object_type': 'link',
                                   'destination': 'sharelink.py',
                                   'text': 'Return to share link overview'})

        return (output_objects, returnvalues.OK)
    elif action in post_actions:
        share_dict = share_map.get(share_id, {})
        if not share_dict and action != 'create':
            logger.warning('%s tried to %s missing or not owned link %s!' %
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

        rel_share_path = share_path.lstrip(os.sep)
        # IMPORTANT: path must be expanded to abs for proper chrooting
        abs_path = os.path.abspath(os.path.join(base_dir, rel_share_path))
        relative_path = abs_path.replace(base_dir, '')
        real_path = os.path.realpath(abs_path)
        single_file = os.path.isfile(real_path)
        vgrid_name = in_vgrid_share(configuration, abs_path)
        # NOTE: use force vgrid map caching here to limit load
        vgrid_parent = is_vgrid_parent_placeholder(configuration,
                                                   relative_path,
                                                   real_path,
                                                   False,
                                                   client_id)

        if action == 'delete':
            header_entry['text'] = 'Delete Share Link'
            (save_status, _) = delete_share_link(share_id, client_id,
                                                 configuration,
                                                 share_map)
            if save_status and vgrid_name:
                logger.debug("del vgrid sharelink pointer %s" % share_id)
                (del_status, del_msg) = vgrid_remove_sharelinks(configuration,
                                                                vgrid_name,
                                                                [share_id],
                                                                'share_id')
                if not del_status:
                    logger.error("del vgrid sharelink pointer %s failed: %s"
                                 % (share_id, del_msg))
                    return (False, share_map)
            desc = "delete"
        elif action == "update":
            header_entry['text'] = 'Update Share Link'
            # Try to point replies to client_id email
            client_email = extract_field(client_id, 'email')
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
                                'USER_CERT': client_id, 'EMAIL_SENDER':
                                client_email}

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
                                            ''' %
                                           (', '.join(notify_sent),
                                            (auto_msg+msg).count('\n')+3,
                                            auto_msg, msg)
                                           })
            if expire:
                share_dict['expire'] = expire
            (save_status, _) = update_share_link(share_dict, client_id,
                                                 configuration, share_map)
            desc = "update"
        elif action == "create":
            header_entry['text'] = 'Create Share Link'
            if not read_access and not write_access:
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'No access set - please select read, write or both'})
                return (output_objects, returnvalues.CLIENT_ERROR)
            # NOTE: check path here as relative_path is empty for path='/'
            if not path:
                output_objects.append(
                    {'object_type': 'error_text', 'text': 'No path provided!'})
                return (output_objects, returnvalues.CLIENT_ERROR)
            # We refuse sharing of entire home for security reasons
            elif not valid_user_path(configuration, abs_path, base_dir,
                                     allow_equal=False):
                logger.warning('%s tried to %s restricted path %s ! (%s)' %
                               (client_id, action, abs_path, path))
                output_objects.append(
                    {'object_type': 'error_text', 'text': '''Illegal path "%s":
you can only share your own data, and not your entire home direcory.''' % path
                     })
                return (output_objects, returnvalues.CLIENT_ERROR)
            elif not os.path.exists(abs_path):
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'Provided path "%s" does not exist!' % path})
                return (output_objects, returnvalues.CLIENT_ERROR)
            # Refuse sharing of (mainly auth) dot dirs in root of user home
            elif real_path.startswith(os.path.join(base_dir, '.')):
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'Provided path "%s" cannot be shared for security reasons'
                     % path})
                return (output_objects, returnvalues.CLIENT_ERROR)
            elif single_file and write_access:
                output_objects.append(
                    {'object_type': 'error_text', 'text': '''Individual files
cannot be shared with write access - please share a directory with the file in
it or only share with read access.
                     '''})
                return (output_objects, returnvalues.CLIENT_ERROR)

            # We check if abs_path is in vgrid share, but do not worry about
            # private_base or public_base since they are only available to
            # owners, who can always share anyway.

            if vgrid_name is not None and \
                    not vgrid_is_owner(vgrid_name, client_id, configuration):
                # share is inside vgrid share so we must check that user is
                # permitted to create sharelinks there.
                (load_status, settings_dict) = vgrid_settings(vgrid_name,
                                                              configuration,
                                                              recursive=True,
                                                              as_dict=True)
                if not load_status:
                    # Probably owners just never saved settings, use defaults
                    settings_dict = {'vgrid_name': vgrid_name}
                allowed = settings_dict.get('create_sharelink', keyword_owners)
                if allowed != keyword_members:
                    output_objects.append(
                        {'object_type': 'error_text', 'text': '''The settings
for the %(vgrid_name)s %(vgrid_label)s do not permit you to re-share
%(vgrid_label)s shared folders. Please contact the %(vgrid_name)s owners if you
think you should be allowed to do that.
''' % {'vgrid_name': vgrid_name, 'vgrid_label': configuration.site_vgrid_label}
                        })
                    return (output_objects, returnvalues.CLIENT_ERROR)
            # Prohibit sharing of vgrid parent placeholder dirs to avoid
            # circumvention of any sub-vgrid sharing controls.
            if vgrid_parent is not None:
                output_objects.append(
                    {'object_type': 'error_text', 'text': '''Illegal path "%s":
you can only share your own data, and not folders with e.g. %s shared folders
nested in them.''' % (path, configuration.site_vgrid_label)
                     })
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

            # IMPORTANT: always use expanded path
            share_dict.update(
                {'path': relative_path, 'access': access_list, 'expire':
                 expire, 'invites': invite_list, 'single_file': single_file})
            attempts = 1
            generate_share_id = False
            if not share_id:
                attempts = 3
                generate_share_id = True
            for i in range(attempts):
                if generate_share_id:
                    share_id = generate_sharelink_id(configuration, share_mode)
                share_dict['share_id'] = share_id
                (save_status, save_msg) = create_share_link(share_dict,
                                                            client_id,
                                                            configuration,
                                                            share_map)
                if save_status:
                    logger.info('created sharelink: %s' % share_dict)
                    break
                else:
                    # ID Collision?
                    logger.warning('could not create sharelink: %s' %
                                   save_msg)
            if save_status and vgrid_name:
                logger.debug("add vgrid sharelink pointer %s" % share_id)
                (add_status, add_msg) = vgrid_add_sharelinks(configuration,
                                                             vgrid_name,
                                                             [share_dict])
                if not add_status:
                    logger.error("save vgrid sharelink pointer %s failed: %s "
                                 % (share_id, add_msg))
                    return (False, share_map)
        else:
            output_objects.append(
                {'object_type': 'error_text', 'text': 'No such action %s' %
                 action})
            return (output_objects, returnvalues.CLIENT_ERROR)

        if not save_status:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Error in %s share link %s: ' % (desc, share_id) +
                 'save updated share links failed!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

        output_objects.append({'object_type': 'text', 'text':
                               '%sd share link %s on %s .' % (desc.title(),
                                                              share_id,
                                                              relative_path)})
        if action in ['create', 'update']:
            sharelinks = []
            share_item = build_sharelinkitem_object(configuration,
                                                    share_dict)
            saved_id = share_item['share_id']
            js_name = 'delete%s' % hexlify(saved_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'share_id': saved_id,
                                       'action': 'delete',
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            share_item['delsharelink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" %
                (js_name, 'Really remove %s?' % saved_id),
                'class': 'removelink iconspace', 'title':
                'Remove share link %s' % saved_id, 'text': ''}
            sharelinks.append(share_item)
            output_objects.append(
                {'object_type': 'sharelinks', 'sharelinks': sharelinks})
            if action == 'create':
                # NOTE: Leave editsharelink here for use in fileman overlay
                # del share_item['editsharelink']
                output_objects.append({'object_type': 'html_form', 'text':
                                       '<br />'})
                submit_button = '''<span>
            <input type=submit value="Send invitation(s)" />
            </span>'''
                invite_html = invite_share_link_form(configuration, client_id,
                                                     share_dict, 'html',
                                                     submit_button, csrf_token)
                output_objects.append({'object_type': 'html_form', 'text':
                                       invite_html})
    else:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Invalid share link action: %s' % action})
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'html_form', 'text': '<br />'})
    output_objects.append({'object_type': 'link',
                           'destination': 'sharelink.py',
                           'text': 'Return to share link overview'})

    return (output_objects, returnvalues.OK)
