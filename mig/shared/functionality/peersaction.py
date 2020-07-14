#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# peersaction - handle saving of peers
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

"""Peers save action back end"""

import datetime
import os
import tempfile
import base64
import re

import shared.returnvalues as returnvalues
from shared.accountreq import parse_peers, peers_permit_allowed
from shared.base import client_id_dir, fill_distinguished_name
from shared.defaults import peers_filename, peer_kinds, peers_fields, \
    csrf_field
from shared.functional import validate_input, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.html import html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.notification import send_email
from shared.parseflags import force
from shared.serial import load, dump
from shared.useradm import get_full_user_map

default_expire_days = 30


def signature():
    """Signature of the main function"""

    defaults = {
        'peers_label': REJECT_UNSET,
        'peers_kind': REJECT_UNSET,
        'peers_expire': [''],
        'peers_format': [],
        'peers_content': [''],
        'flags': ['']
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

    # force name to capitalized form (henrik karlsen -> Henrik Karlsen)

    label = accepted['peers_label'][-1].strip()
    kind = accepted['peers_kind'][-1].strip()
    raw_expire = accepted['peers_expire'][-1].strip()
    peers_content = accepted['peers_content'][-1].strip()
    peers_format = accepted['peers_format'][-1].strip()
    # TODO: implement and enable more providers
    flags = ''.join(accepted['flags']).strip()

    # TODO: check valid kind and date
    try:
        expire = datetime.datetime.strptime(raw_expire, '%Y-%m-%d')
        if datetime.datetime.now() > expire:
            raise ValueError("specified expire value is in the past!")
    except Exception, exc:
        logger.error("expire %r could not be parsed into a (future) date" %
                     raw_expire)
        output_objects.append(
            {'object_type': 'text', 'text':
             'No valid expire provided - using default: %d days' %
             default_expire_days})
        expire = datetime.datetime.now()
        expire += datetime.timedelta(days=default_expire_days)
    expire = expire.date().isoformat()

    if not kind in peer_kinds:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Unsupported peer kind %r - only %s are allowed' %
             (kind, ', '.join(peer_kinds))})
        return (output_objects, returnvalues.CLIENT_ERROR)
    if "csvform" != peers_format:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Only Import Peers is supported so far!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    peers_path = os.path.join(configuration.user_settings, client_dir,
                              peers_filename)
    try:
        all_peers = load(peers_path)
    except Exception, exc:
        logger.warning("could not load peers from: %s" % exc)
        all_peers = {}

    if all_peers.get(label, None):
        actual_action = 'updated'
    else:
        actual_action = 'created'
        all_peers[label] = {}

    (peers, err) = parse_peers(configuration, peers_content, peers_format)
    if err:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Parsing failed: %s' % '.\n '.join(err)})
        output_objects.append({'object_type': 'link', 'destination':
                               'peers.py', 'text': 'Back to peers'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if peers:
        all_peers[label].update({
            'label': label,
            'kind': kind,
            'expire': expire,
            'peers': peers
        })
        pretty_peers = all_peers[label].copy()
    elif force(flags):
        actual_action = 'deleted'
        logger.info('delete %s peers %s in %s' % (client_id, all_peers,
                                                  peers_path))
        pretty_peers = all_peers[label].copy()
        del all_peers[label]
    else:
        output_objects.append({'object_type': 'text', 'text': '''
No peers provided - saving with empty list will result in the %r peers getting
deleted. Please use either of the links below to confirm or cancel.
''' % label})
        # Reuse csrf token from this request
        target_op = 'peersaction'
        js_name = target_op
        csrf_token = accepted[csrf_field][-1]
        helper = html_post_helper(js_name, '%s.py' % target_op,
                                  {'peers_label': label, 'peers_kind': kind,
                                   'peers_expire': raw_expire,
                                   'peers_content': '',
                                   'peers_format': 'csvform', 'flags': 'f',
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        output_objects.append({'object_type': 'link', 'destination':
                               "javascript: %s();" % js_name, 'class':
                               'removelink iconspace', 'text':
                               'Really delete %r peers' % label})
        output_objects.append({'object_type': 'text', 'text': ''})
        output_objects.append({'object_type': 'link', 'destination':
                               'peers.py', 'text': 'Back to peers'})
        return (output_objects, returnvalues.OK)

    try:
        dump(all_peers, peers_path)
        logger.debug('%s %s peers %s in %s' % (actual_action, client_id,
                                               all_peers, peers_path))
        output_objects.append(
            {'object_type': 'text', 'text': "Peers %r %s" % (label,
                                                             actual_action)})
    except Exception, exc:
        logger.error('Failed to save %s peers to %s: %s' %
                     (client_id, peers_path, exc))
        output_objects.append({'object_type': 'error_text', 'text': '''
Peers %r could not be %s. Please contact the site admins on %s if this error
persists.
''' % (label, actual_action, admin_email)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.info('%s %r peers for %s in %s' % (actual_action, label, client_id,
                                              peers_path))
    user_lines = []
    for user in pretty_peers['peers']:
        fill_distinguished_name(user)
        user_lines.append(user['distinguished_name'])
    pretty_peers['user_lines'] = '\n'.join(user_lines)
    email_header = '%s Peers %s' % (configuration.short_title, actual_action)
    email_msg = """
User %s %s peers data
""" % (client_id, actual_action)
    email_msg += """
Label:
%(label)s
Kind:
%(kind)s
Expire:
%(expire)s
Peers:
%(user_lines)s
""" % pretty_peers

    logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                % (admin_email, email_header, email_msg, smtp_server))
    if not send_email(admin_email, email_header, email_msg, logger,
                      configuration):
        output_objects.append({'object_type': 'error_text', 'text': '''
An error occured trying to send the email about %s peers to the site
administrators. Please inform them (%s) if the problem persists.
''' % (actual_action, admin_email)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'link', 'destination':
                           'peers.py', 'text': 'Back to peers'})
    return (output_objects, returnvalues.OK)
