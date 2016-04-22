#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sharelinks - share link helper functions
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

"""Share link functions"""

import datetime
import os
import time

from shared.defaults import sharelinks_filename
from shared.fileio import makedirs_rec, make_symlink, delete_symlink
from shared.serial import load, dump
from shared.useradm import client_id_dir, extract_field

def build_sharelinkitem_object(configuration, share_dict):
    """Build a share link object based on input share_dict"""

    created_timetuple = share_dict['created_timestamp'].timetuple()
    created_asctime = time.asctime(created_timetuple)
    created_epoch = time.mktime(created_timetuple)
    share_item = {
        'object_type': 'sharelink',
        'created': "<div class='sortkey'>%d</div>%s" % (created_epoch,
                                                        created_asctime),
        }
    share_id = share_dict['share_id']
    share_item.update(share_dict)
    access = '-'.join((share_item['access'] + ['only'])[:2])
    id_args = 'sharelink_mode=%s;sharelink_id=%s' % (access, share_id)
    share_url = "%s/cgi-sid/ls.py?%s" \
                % (configuration.migserver_https_sid_url, id_args)
    share_item['share_url'] = share_url
    share_item['opensharelink'] = {
        'object_type': 'link',
        'destination': share_url,
        'class': 'urllink', 
        'title': 'Open share link %s' % share_id,
        'text': ''}
    edit_url = 'sharelink.py?action=edit;share_id=%s' % share_id
    share_item['editsharelink'] = {
        'object_type': 'link',
        'destination': edit_url,
        'class': 'editlink', 
        'title': 'Edit or invite to share link %s' % share_id,
        'text': ''}
    # NOTE: datetime is not json serializable so we remove
    del share_item['created_timestamp']
    return share_item

def create_share_link_form(configuration, client_id, output_format, form_append=''):
    """HTML for the creation of share links"""
    html = '''
    <form id="sharelink_form" method="post" action="sharelink.py">
    <fieldset>
        <input type="hidden" name="output_format" value="%(output_format)s" />
        <input type="hidden" name="action" value="create" />
        <h4>Create Share Link</h4>
        <p>
        You can explicitly share files and directories with anyone using
        <em>share links</em>. That is especially useful when sharing data with
        people who do not have an account here, i.e. when basic %(vgrid_label)s
        sharing is impossible.</p>
        <table>
        <tr><td colspan=2>
        <label for="path">File/folder to share:</label>
        <input id="extpath" class="singlefield" type="text" name="path" size=50  value="" />
        </td></tr>
        <tr><td colspan=2>
        <br/>
        </td></tr>
        <tr><td>
        <label for="read_access" class="widefield">Read Access</label>
        <input id="extreadaccess" type="checkbox" name="read_access" checked />
        </td><td>
        <label for="write_access" class="widefield">Write Access</label>
        <input id="extwriteaccess" type="checkbox" name="write_access" />
        </td></tr>
        <tr><td colspan=2>
        <br/>
        </td></tr>
        <tr class="hidden"><td colspan=2>
        Optionally set expire time and password or leave empty for none.
        </td></tr>
        <tr class="hidden"><td colspan=2>
        <label for="expire">Expire:</label>
        <input id="extexpire" class="singlefield" type="text" name="expire" size=40  value="" />
        </td></tr>
        <tr class="hidden"><td colspan=2>
        <label for="password">Password:</label>
        <input id="extpassword" class="singlefield" type="password"
            name="password" size=40  value="" />
        </td></tr>
        <tr class="hidden"><td colspan=2>
        Optionally provide one or more recipients of the share link and a
        message to also invite someone to use the share. Just leave empty if
        you prefer to manually send out the share link by other means.
        </td></tr>
        <tr class="hidden"><td colspan=2>
        <label for="invite">Recipient(s):</label>
        <input id="extinvite" class="singlefield" type="text" name="invite" size=40  value="" />
        </td></tr>
        <tr class="hidden"><td colspan=2>
        <label for="msg">Message:</label>
        <textarea id="extmsg" class="singlefield" name="msg" rows=4></textarea>
        </td></tr>
        <tr><td colspan=2>
        %(form_append)s
        </td></tr>
        </table>
    </fieldset>
    </form>
''' %  {'vgrid_label': configuration.site_vgrid_label, 'output_format':
        output_format, 'form_append': form_append}
    return html

def invite_share_link_helper(configuration, client_id, share_dict,
                             output_format, form_append=''):
    """Build share link invitation helper dict to fill strings"""
    fill_helper = {'vgrid_label': configuration.site_vgrid_label, 'short_title':
                   configuration.short_title, 'output_format': output_format}
    fill_helper.update(share_dict)
    fill_helper['mode'] = '-'.join((share_dict['access'] + ['only'])[:2])
    id_args = 'sharelink_mode=%s;sharelink_id=%s' % (fill_helper['mode'],
                                                     fill_helper['share_id'])
    fill_helper['share_url'] = "%s/cgi-sid/ls.py?%s" \
                               % (configuration.migserver_https_sid_url,
                                  id_args)
    fill_helper['name'] = extract_field(client_id, 'full_name')
    fill_helper['email'] = extract_field(client_id, 'email')
    fill_helper['form_append'] = form_append
    fill_helper['auto_msg'] = '''Hi,
%(name)s (%(email)s) has shared %(short_title)s data with you on:
%(share_url)s

--- Optional invitation message follows below ---''' % fill_helper
    return fill_helper

def invite_share_link_message(configuration, client_id, share_dict,
                              output_format, form_append=""):
    """Get automatic message preamble for invitation mails"""
    fill_helper = invite_share_link_helper(configuration, client_id,
                                           share_dict, output_format,
                                           form_append)
    return fill_helper['auto_msg']

def invite_share_link_form(configuration, client_id, share_dict, output_format,
                           form_append=''):
    """HTML for the inviting people to share links"""
    fill_helper = invite_share_link_helper(configuration, client_id,
                                           share_dict, output_format,
                                           form_append)
    html = '''
    <form id="sharelink_form" method="post" action="sharelink.py">
    <fieldset>
        <input type="hidden" name="output_format" value="%(output_format)s" />
        <input type="hidden" name="action" value="update" />
        <h4>Send Share Link Invitations</h4>
        <p>
        After creating a share link you can manually give the link to anyone
        you want to share the data with and/or use this form to send
        invitations on email. Please note that abuse of this service to send
        out spam mail is strictly prohibited and will be sanctioned.
        </p>
        <table>
        <tr><td colspan=2>
        <label for="share_id">Share Link ID:</label>
        <input id="extshare_id" class="singlefield" type="text"
            name="share_id" size=50  value="%(share_id)s"
            readonly="readonly" />
        </td></tr>
        <tr><td colspan=2>
        <br/>
        </td></tr>
        <tr><td colspan=2>
        <label for="invite">Recipient(s):</label>
        <input id="extinvite" class="singlefield" type="text" name="invite"
            size=50  value="" />
        </td></tr>
        <tr><td colspan=2>
        <label for="extromessage">Automatic Message:</label>
        <textarea id="extromessage" class="singlefield fillwidth"
        rows=3 readonly="readonly">%(auto_msg)s</textarea>
        </td></tr>
        <tr><td colspan=2>
        <label for="extmessage">Optional Message:</label>
        <textarea id="extmessage" class="singlefield fillwidth" name="msg"
        rows=10></textarea>
        </td></tr>
        <tr><td colspan=2>
        %(form_append)s
        </td></tr>
        </table>
    </fieldset>
    </form>
''' %  fill_helper
    return html

def load_share_links(configuration, client_id):
    """Find all share links owned by user"""
    logger = configuration.logger
    logger.debug("load share links for %s" % client_id)
    try:
        sharelinks_path = os.path.join(configuration.user_settings,
                                      client_id_dir(client_id),
                                      sharelinks_filename)
        logger.debug("load sharelinks from %s" % sharelinks_path)
        if os.path.isfile(sharelinks_path):
            sharelinks = load(sharelinks_path)
        else:
            sharelinks = {}
    except Exception, exc:
        return (False, "could not load saved share links: %s" % exc)
    return (True, sharelinks)

def get_share_link(share_id, client_id, configuration, share_map=None):
    """Helper to extract all details for a share link. The optional
    share_map argument can be used to pass an already loaded dictionary of
    saved share links to avoid reloading.
    """
    if share_map is None:
        (load_status, share_map) = load_share_links(configuration,
                                                       client_id)
        if not load_status:
            return (load_status, share_map)
    share_dict = share_map.get(share_id, None)
    if share_dict is None:
        return (False, 'No such share in saved share links: %s' % \
                share_id)
    return (True, share_dict)


def modify_share_links(action, share_dict, client_id, configuration,
                       share_map=None):
    """Modify share links with given action and share_dict for client_id.
    In practice this a shared helper to add or remove share links from the
    saved dictionary. The optional share_map argument can be used to pass an
    already loaded dictionary of saved share links to avoid reloading.
    """
    logger = configuration.logger
    share_id = share_dict['share_id']
    if share_map is None:
        (load_status, share_map) = load_share_links(configuration,
                                                       client_id)
        if not load_status:
            logger.error("modify_share_links failed in load: %s" % \
                         share_map)
            return (load_status, share_map)

    share_dict.update(share_map.get(share_id, {}))
    rel_path = share_dict['path'].lstrip(os.sep)
    access = share_dict['access']
    if 'read' in access and 'write' in access:
        access_dir = 'read-write'
    elif 'read' in access:
        access_dir = 'read-only'
    elif 'write' in access:
        access_dir = 'write-only'
    else:
        logger.error("modify_share_links invalid access: %s" % access)
        return (load_status, share_map)
    symlink_path = os.path.join(configuration.sharelink_home, access_dir,
                                share_id)
    target_path = os.path.join(configuration.user_home,
                               client_id_dir(client_id), rel_path)
    if action == "create":
        if not make_symlink(target_path, symlink_path, configuration.logger,
                            False):
            logger.error("could not make share symlink: %s (already exists?)" \
                         % symlink_path)
            return (False, share_map)
        share_dict.update({
            'created_timestamp': datetime.datetime.now(),
            'owner': client_id,
            })
        share_map[share_id] = share_dict
    elif action == "modify":
        if not make_symlink(target_path, symlink_path, configuration.logger,
                            True):
            logger.error("could not update share symlink: %s"  % symlink_path)
            return (False, share_map)
        share_dict['created_timestamp'] = datetime.datetime.now()
        share_map[share_id].update(share_dict)
    elif action == "delete":
        if not delete_symlink(symlink_path, configuration.logger):
            logger.error("could not delete share symlink: %s (missing?)" % \
                         symlink_path)
            return (False, share_map)
        del share_map[share_id]        
    else:
        return (False, "Invalid action %s on share links" % action)
        
    try:
        sharelinks_path = os.path.join(configuration.user_settings,
                                      client_id_dir(client_id),
                                      sharelinks_filename)
        dump(share_map, sharelinks_path)
    except Exception, err:
        logger.error("modify_share_links failed: %s" % err)
        return (False, 'Error updating share links: %s' % err)
    return (True, share_id)


def create_share_link(share_dict, client_id, configuration,
                         share_map=None):
    """Create a new share link for client_id. The optional share_map argument
    can be used to pass an already loaded dictionary of saved share links to
    avoid reloading.
    """
    return modify_share_links("create", share_dict, client_id,
                              configuration, share_map)

def update_share_link(share_dict, client_id, configuration,
                         share_map=None):
    """Update existing share link for client_id. The optional share_map
    argument can be used to pass an already loaded dictionary of saved share
    links to avoid reloading.
    """
    return modify_share_links("modify", share_dict, client_id,
                              configuration, share_map)

def delete_share_link(share_id, client_id, configuration, share_map=None):
    """Delete an existing share link without checking ownership. The optional
    share_map argument can be used to pass an already loaded dictionary of
    saved share links to avoid reloading.    """
    share_dict = {'share_id': share_id}
    return modify_share_links("delete", share_dict, client_id,
                              configuration, share_map)
