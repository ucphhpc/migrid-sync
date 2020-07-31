#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# peersaction - handle management of peers
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

"""Peers management action back end"""
from __future__ import absolute_import

import datetime
import os
import tempfile
import base64
import re

from mig.shared import returnvalues
from mig.shared.accountreq import parse_peers, peers_permit_allowed, \
    manage_pending_peers
from mig.shared.base import client_id_dir, fill_distinguished_name
from mig.shared.defaults import peers_filename, peer_kinds, peers_fields, \
    csrf_field
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.html import html_post_helper
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.notification import send_email
from mig.shared.serial import load, dump
from mig.shared.useradm import get_full_user_map

default_expire_days = 7
peer_actions = ['import', 'add', 'remove', 'update', 'accept', 'reject']


def signature():
    """Signature of the main function"""

    defaults = {
        'action': REJECT_UNSET,
        'peers_label': [''],
        'peers_kind': REJECT_UNSET,
        'peers_expire': REJECT_UNSET,
        'peers_format': REJECT_UNSET,
        'peers_content': REJECT_UNSET,
    }
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature()[1]
    client_dir = client_id_dir(client_id)
    logger.debug('in peersaction: %s' % user_arguments_dict)
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Save Peers'
    output_objects.append({'object_type': 'header', 'text': 'Save Peers'})

    admin_email = configuration.admin_email
    smtp_server = configuration.smtp_server
    user_pending = os.path.abspath(configuration.user_pending)

    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    # Optional site-wide limitation of peers permission
    if not user_dict or \
            not peers_permit_allowed(configuration, user_dict):
        logger.warning(
            "user %s is not allowed to permit peers!" % client_id)
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Only privileged users can permit external peers!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    action = accepted['action'][-1].strip()
    label = accepted['peers_label'][-1].strip()
    kind = accepted['peers_kind'][-1].strip()
    raw_expire = accepted['peers_expire'][-1].strip()
    peers_content = accepted['peers_content']
    peers_format = accepted['peers_format'][-1].strip()

    try:
        expire = datetime.datetime.strptime(raw_expire, '%Y-%m-%d')
        if datetime.datetime.now() > expire:
            raise ValueError("specified expire value is in the past!")
    except Exception as exc:
        logger.error("expire %r could not be parsed into a (future) date" %
                     raw_expire)
        output_objects.append(
            {'object_type': 'text', 'text':
             'No valid expire provided - using default: %d days' %
             default_expire_days})
        expire = datetime.datetime.now()
        expire += datetime.timedelta(days=default_expire_days)
    expire = expire.date().isoformat()

    if not action in peer_actions:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Unsupported peer action %r - only %s are allowed' %
             (action, ', '.join(peer_actions))})
        return (output_objects, returnvalues.CLIENT_ERROR)
    if not kind in peer_kinds:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Unsupported peer kind %r - only %s are allowed' %
             (kind, ', '.join(peer_kinds))})
        return (output_objects, returnvalues.CLIENT_ERROR)
    # TODO: implement and enable more formats?
    if peers_format not in ("csvform", 'userid'):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Only Import Peers is implemented so far!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    peers_path = os.path.join(configuration.user_settings, client_dir,
                              peers_filename)
    try:
        all_peers = load(peers_path)
    except Exception as exc:
        logger.warning("could not load peers from: %s" % exc)
        all_peers = {}

    # Extract peer(s) from request
    (peers, err) = parse_peers(configuration, peers_content, peers_format)
    if not err and not peers:
        err = ["No valid peers provided"]
    if err:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Parsing failed: %s' % '.\n '.join(err)})
        output_objects.append({'object_type': 'link', 'destination':
                               'peers.py', 'text': 'Back to peers'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # NOTE: general cases of operation here:
    # * import multiple peers in one go (add new, update existing)
    # * add one or more new peers
    # * update one or more existing peers
    # * remove one or more existing peers
    # * accept one or more pending requests
    # * reject one or more pending requests
    # The kind and expire values are generally applied for all included peers.

    # NOTE: we check all peers before any action
    for user in peers:
        fill_distinguished_name(user)
        peer_id = user['distinguished_name']
        cur_peer = all_peers.get(peer_id, {})
        if 'add' == action and cur_peer:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Peer %r already exists!' % peer_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        elif 'update' == action and not cur_peer:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Peer %r does not exists!' % peer_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        elif 'remove' == action and not cur_peer:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Peer %r does not exists!' % peer_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        elif 'accept' == action and cur_peer:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Peer %r already accepted!' % peer_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        elif 'reject' == action and cur_peer:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Peer %r already accepted!' % peer_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        elif 'import' == action and cur_peer:
            # Only warn on import with existing match
            output_objects.append(
                {'object_type': 'text', 'text':
                 'Updating existing peer %r' % peer_id})

    # Now apply changes
    for user in peers:
        peer_id = user['distinguished_name']
        cur_peer = all_peers.get(peer_id, {})
        user.update({'label': label, 'kind': kind, 'expire': expire})
        if 'add' == action:
            all_peers[peer_id] = user
        elif 'update' == action:
            all_peers[peer_id] = user
        elif 'remove' == action:
            del all_peers[peer_id]
        elif 'accept' == action:
            all_peers[peer_id] = user
        elif 'reject' == action:
            pass
        elif 'import' == action:
            all_peers[peer_id] = user
        logger.info("%s peer %s" % (action, peer_id))

    try:
        dump(all_peers, peers_path)
        logger.debug('%s %s peers %s in %s' % (client_id, action, all_peers,
                                               peers_path))
        output_objects.append(
            {'object_type': 'text', 'text': "Completed %s peers" % action})
        for user in peers:
            output_objects.append(
                {'object_type': 'text', 'text': "%(distinguished_name)s" % user})
    except Exception as exc:
        logger.error('Failed to save %s peers to %s: %s' %
                     (client_id, peers_path, exc))
        output_objects.append({'object_type': 'error_text', 'text': '''
Could not %s peers %r. Please contact the site admins on %s if this error
persists.
''' % (action, label, admin_email)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if action in ["accept", "reject"]:
        changed = [(i['distinguished_name'], i) for i in peers]
        if not manage_pending_peers(configuration, client_id, "remove",
                                    changed):
            logger.warning('could not update pending peers for %s after %s' %
                           (client_id, action))

    logger.info('%s completed for %s peers for %s in %s' %
                (action, label, client_id, peers_path))

    user_lines = []
    pretty_peers = {'label': label, 'kind': kind, 'expire': expire}
    for user in peers:
        user_lines.append(user['distinguished_name'])
    pretty_peers['user_lines'] = '\n'.join(user_lines)
    email_header = '%s Peers %s' % (configuration.short_title, action)
    email_msg = """Received %s peers from %s
""" % (action, client_id)
    email_msg += """
Kind: %(kind)s , Expire: %(expire)s, Label: %(label)s , Peers:
%(user_lines)s
""" % pretty_peers

    logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                % (admin_email, email_header, email_msg, smtp_server))
    if not send_email(admin_email, email_header, email_msg, logger,
                      configuration):
        output_objects.append({'object_type': 'error_text', 'text': '''
An error occured trying to send the email about your %s peers to the site
administrators. Please manually inform them (%s) if the problem persists.
''' % (action, admin_email)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text': '''
Informed the site admins about your %s peers action.''' % action})

    output_objects.append({'object_type': 'link', 'destination':
                           'peers.py', 'text': 'Back to peers'})
    return (output_objects, returnvalues.OK)
