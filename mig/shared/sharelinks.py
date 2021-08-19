#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sharelinks - share link helper functions
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

"""Share link functions"""

from __future__ import absolute_import

from builtins import range
import datetime
import os
import time
from random import SystemRandom

from mig.shared.base import client_id_dir, extract_field
from mig.shared.defaults import sharelinks_filename, csrf_field, \
    share_mode_charset, share_id_charset
from mig.shared.fileio import makedirs_rec, make_symlink, delete_symlink
from mig.shared.serial import load, dump

# We split mode charset into ro, rw and rw substrings and pick one char at
# random from the corresponding substring when generating a share ID. In that
# way we keep the number of combinations high while preserving short IDs and
# a simple mapping for the apache configuration.
__mode_len = len(share_mode_charset) // 3
__ro_mode_chars = share_mode_charset[:__mode_len]
__rw_mode_chars = share_mode_charset[__mode_len:2 * __mode_len]
__wo_mode_chars = share_mode_charset[2 * __mode_len:]
mode_chars_map = {'read-only': __ro_mode_chars, 'read-write': __rw_mode_chars,
                  'write-only': __wo_mode_chars}

__bool_map = {True: 'Yes', False: 'No'}


def generate_sharelink_id(configuration, share_mode):
    """We use one random char from the substring matching share_mode and
    configuration.sharelink_length-1 random chars for the actual ID part. With
    the default sharelink_length of 10 that gives us ~ 1E18 possible ID
    strings, which should be enough to avoid collisions and brute force
    guessing.
    """
    share_id = SystemRandom().choice(mode_chars_map[share_mode])
    share_id += ''.join([SystemRandom().choice(share_id_charset) for _ in
                         range(configuration.site_sharelink_length-1)])
    return share_id


def extract_mode_id(configuration, share_id):
    """Extract mode from first char and return along with ID-only part.
    Please refer to generate_sharelink_id for details about the fixed format
    used to encode mode and a unique ID into one compact and URL-friendly
    string.
    """
    # We use [:1] and [1:] slicing to avoid IndexError on empty strings
    for (mode, mode_chars) in mode_chars_map.items():
        if share_id[:1] in mode_chars:
            return (mode, share_id[1:])
    raise ValueError("Invalid share_id '%s' !" % share_id)


def is_active(configuration, share_dict):
    """Check if share link inf share_dict is active in the sense that the
    symlink and target path both exist.
    """
    share_id = share_dict['share_id']
    rel_path = share_dict['path'].lstrip('/')
    client_id = share_dict['owner']
    single_file = share_dict['single_file']
    (access_dir, _) = extract_mode_id(configuration, share_id)
    symlink_path = os.path.join(configuration.sharelink_home, access_dir,
                                share_id)
    target_path = os.path.join(configuration.user_home,
                               client_id_dir(client_id), rel_path)
    if not os.path.islink(symlink_path):
        return False
    if single_file and not os.path.isfile(target_path):
        return False
    if not single_file and not os.path.isdir(target_path):
        return False
    return True


def build_sharelinkitem_object(configuration, share_dict):
    """Build a share link object based on input share_dict"""

    created_timetuple = share_dict['created_timestamp'].timetuple()
    created_asctime = time.asctime(created_timetuple)
    created_epoch = time.mktime(created_timetuple)
    share_item = {
        'object_type': 'sharelink',
        'created': "<div class='sortkey'>%d</div>%s" % (created_epoch,
                                                        created_asctime),
        # Legacy: make sure single_file is always set
        'single_file': False,
    }
    share_id = share_dict['share_id']
    share_item.update(share_dict)
    share_item['active'] = __bool_map[is_active(configuration, share_item)]
    access = '-'.join((share_item['access'] + ['only'])[:2])
    if share_item['single_file']:
        share_url = "%s/share_redirect/%s" \
                    % (configuration.migserver_https_sid_url,
                       share_id)
    else:
        share_url = "%s/sharelink/%s" % (configuration.migserver_https_sid_url,
                                         share_id)
    share_item['share_url'] = share_url
    share_item['opensharelink'] = {
        'object_type': 'link',
        'destination': share_url,
        'class': 'urllink iconspace',
        'title': 'Open share link %s' % share_id,
        'text': ''}
    edit_url = 'sharelink.py?action=edit;share_id=%s' % share_id
    share_item['editsharelink'] = {
        'object_type': 'link',
        'destination': edit_url,
        'class': 'editlink iconspace',
        'title': 'Edit or invite to share link %s' % share_id,
        'text': ''}
    # NOTE: datetime is not json-serializable so we force to string
    for field in ['created_timestamp']:
        share_item[field] = "%s" % share_item[field]
    return share_item


def create_share_link_form(configuration, client_id, output_format,
                           form_append='', csrf_token=''):
    """HTML for the creation of share links"""
    fill_helpers = {'vgrid_label': configuration.site_vgrid_label,
                    'output_format': output_format, 'form_append': form_append,
                    'csrf_field': csrf_field, 'csrf_token': csrf_token,
                    'target_op': 'sharelink', 'form_method': 'post'}
    html = '''
    <form id="create_sharelink_form" method="%(form_method)s" action="%(target_op)s.py">
    <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
    <fieldset>
        <input type="hidden" name="output_format" value="%(output_format)s" />
        <input type="hidden" name="action" value="create" />
        <p>
        You can explicitly share files and directories with anyone using
        <em>share links</em>. That is especially useful when sharing data with
        people who do not have an account here, so that basic %(vgrid_label)s
        sharing is impossible.<br/>
        Individual files can only be shared read-only, but folders can
        additionally be shared with read-write or write-only access to allow
        recipients of the share link to write and upload in the share.
        </p>
        <p class="warningtext">
        Please be careful about giving write access to anyone you do not fully
        trust, and note that you can always delete share links again later to
        limit the risks of abuse.
        </p>
        <table>
        <tr><td colspan=2>
        <label for="path">File/folder to share:</label>
        <input id="extpath" class="singlefield" type="text" name="path" size=50
        value="" required pattern="[^ ]+"
        title="relative file or directory path to share" />
        </td></tr>
        <tr><td colspan=2>
        <br/>
        </td></tr>
        <tr><td>
        <label for="read_access" class="widefield_center">Read Access</label>
        <input id="extreadaccess" type="checkbox" name="read_access" checked />
        </td><td>
        <label for="write_access" class="widefield_center">Write Access</label>
        <input id="extwriteaccess" type="checkbox" name="write_access" />
        </td></tr>
        <tr><td colspan=2>
        <br/>
        </td></tr>
        <tr class="hidden"><td colspan=2>
        Optionally set expire time or leave empty for none.
        </td></tr>
        <tr class="hidden"><td colspan=2>
        <label for="expire">Expire:</label>
        <input id="extexpire" class="singlefield" type="text" name="expire" size=40  value="" />
        </td></tr>
        <tr><td colspan=2>
        %(form_append)s
        </td></tr>
        </table>
    </fieldset>
    </form>
''' % fill_helpers
    return html


def import_share_link_form(configuration, client_id, output_format,
                           form_append='', csrf_token=''):
    """HTML for the import of share links"""
    fill_helpers = {'vgrid_label': configuration.site_vgrid_label,
                    'output_format': output_format, 'form_append': form_append,
                    'csrf_field': csrf_field, 'csrf_token': csrf_token,
                    'target_op': 'cp', 'form_method': 'post'}
    # TODO: move js to separate function?
    html = ''
    html += '''
    <script>
    function toggle_overwrite_warning() {
        if ($("#overwrite_check").prop("checked")) {
            $("#overwrite_warn").show();
        } else {
            $("#overwrite_warn").hide();
        }
    }
    </script>
    '''
    html += '''
    <form id="import_sharelink_form" method="%(form_method)s" action="%(target_op)s.py">
    <fieldset>
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="output_format" value="%(output_format)s" />
        <input type="hidden" name="action" value="create" />
        <p>
        You can import the files and directories someone shared with you in
        <em>share links</em>, e.g. to get your own copy of read-only material.
        Just leave Source path to "*" to import entire share link content.
        </p>
        <p class="warningtext">
        Please select a destination folder where the import does not interfere
        with your existing data.
        </p>
        <table>
        <tr><td colspan=2>
        <label for="share_id">Share Link ID:</label>
        <input id="importshareid" class="singlefield" type="text" name="share_id" size=50
        value="" required pattern="[^ ]+"
        title="id string of share link to import from" />
        </td></tr>
        <tr><td colspan=2>
        <label for="src">Source path:</label>
        <input id="importsrc" class="singlefield" type="text" name="src" size=50
        value="" required pattern="[^ ]+"
        title="relative path or pattern of files to import from sharelink" />
        <tr><td colspan=2>
        <label for="dst">Destination folder:</label>
        <input id="importdst" class="singlefield" type="text" name="dst" size=50
        value="" required pattern="[^ ]+" readonly
        title="relative directory path to import sharelink into" />
        </td></tr>
        <tr class="hidden"><td colspan=2>
        <br />
        </td></tr>
        <tr><td colspan=2>
        <br/>
        </td></tr>
        <tr class="hidden"><td colspan=2>
        <!-- NOTE: we translate individual flag helpers in jquery fileman -->
        <!-- always use recursive -->
        <label for="recursive">Recursive:</label>
        <input type="checkbox" name="recursive" checked="checked" />
        </td></tr>
        <tr><td colspan=2>
        <!-- toggle force on/off -->
        <label for="overwrite">Overwrite files:</label>
        <input id="overwrite_check" type="checkbox" name="overwrite"
            onClick="toggle_overwrite_warning();" />
        <span id="overwrite_warn" class="hidden iconspace leftpad warn">
        careful - may result in data loss!</span>
        </td></tr>
        <tr><td colspan=2>
        %(form_append)s
        </td></tr>
        </table>
    </fieldset>
    </form>
''' % fill_helpers
    return html


def invite_share_link_helper(configuration, client_id, share_dict,
                             output_format, form_append=''):
    """Build share link invitation helper dict to fill strings"""
    fill_helpers = {'vgrid_label': configuration.site_vgrid_label, 'short_title':
                    configuration.short_title, 'output_format': output_format,
                    # Legacy: make sure single_file is always set
                    'single_file': False}
    fill_helpers.update(share_dict)
    if fill_helpers['single_file']:
        fill_helpers['share_url'] = "%s/share_redirect/%s" \
            % (configuration.migserver_https_sid_url,
               fill_helpers['share_id'])
    else:
        fill_helpers['share_url'] = "%s/sharelink/%s" \
            % (configuration.migserver_https_sid_url,
               fill_helpers['share_id'])
    fill_helpers['name'] = extract_field(client_id, 'full_name')
    fill_helpers['email'] = extract_field(client_id, 'email')
    fill_helpers['form_append'] = form_append
    fill_helpers['auto_msg'] = '''Hi,
%(name)s (%(email)s) has shared %(short_title)s data with you on:
%(share_url)s

--- Optional invitation message follows below ---''' % fill_helpers
    return fill_helpers


def invite_share_link_message(configuration, client_id, share_dict,
                              output_format, form_append=""):
    """Get automatic message preamble for invitation mails"""
    fill_helpers = invite_share_link_helper(configuration, client_id,
                                            share_dict, output_format,
                                            form_append)
    return fill_helpers['auto_msg']


def invite_share_link_form(configuration, client_id, share_dict, output_format,
                           form_append='', csrf_token=''):
    """HTML for the inviting people to share links"""
    fill_helpers = invite_share_link_helper(configuration, client_id,
                                            share_dict, output_format,
                                            form_append)
    fill_helpers.update({'csrf_field': csrf_field, 'csrf_token': csrf_token,
                         'target_op': 'sharelink', 'form_method': 'post'})
    html = '''
    <form id="sharelink_form" method="%(form_method)s" action="%(target_op)s.py">
    <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
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
        <!-- NOTE: rather loose email validation to inform user about most
        basic errors before the backend does full validation -->
        <input id="extinvite" class="singlefield" type="text" name="invite"
            size=50  value="" required
            pattern="[^, @]+@[^, @]+([ ]*,[ ]*[^, @]+@[^, @]+)*"
            title="one or more valid email addresses separated by commas" />
        </td></tr>
        <tr><td colspan=2>
        <label for="extromessage">Automatic Message:</label>
        <textarea id="extromessage" class="singlefield fillwidth"
        rows=5 readonly="readonly">%(auto_msg)s</textarea>
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
''' % fill_helpers
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
    except Exception as exc:
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
        return (False, 'No such share in saved share links: %s' %
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
            logger.error("modify_share_links failed in load: %s" %
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
            logger.error("could not make share symlink: %s (already exists?)"
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
            logger.error("could not update share symlink: %s" % symlink_path)
            return (False, share_map)
        share_dict['created_timestamp'] = datetime.datetime.now()
        share_map[share_id].update(share_dict)
    elif action == "delete":
        if not delete_symlink(symlink_path, configuration.logger):
            logger.error("could not delete share symlink: %s (missing?)" %
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
    except Exception as err:
        logger.error("modify_share_links failed: %s" % err)
        return (False, 'Error updating share links: %s' % err)
    return (True, share_id)


def create_share_link(share_dict, client_id, configuration,
                      share_map=None):
    """Create a new share link for client_id. The optional share_map argument
    can be used to pass an already loaded dictionary of saved share links to
    avoid reloading.
    """
    return modify_share_links("create", share_dict, client_id, configuration,
                              share_map)


def update_share_link(share_dict, client_id, configuration,
                      share_map=None):
    """Update existing share link for client_id. The optional share_map
    argument can be used to pass an already loaded dictionary of saved share
    links to avoid reloading.
    """
    return modify_share_links("modify", share_dict, client_id, configuration,
                              share_map)


def delete_share_link(share_id, client_id, configuration, share_map=None):
    """Delete an existing share link without checking ownership. The optional
    share_map argument can be used to pass an already loaded dictionary of
    saved share links to avoid reloading.
    """
    share_dict = {'share_id': share_id}
    return modify_share_links("delete", share_dict, client_id, configuration,
                              share_map)
