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
from shared.base import client_id_dir
from shared.defaults import peers_filename
from shared.functional import validate_input, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables, find_entry
from shared.notification import send_email
from shared.serial import load, dump


def parse_peers_form(configuration, raw_lines, csv_sep=';'):
    """Parse CSV form of peers into a list of peers"""
    _logger = configuration.logger
    header = None
    peers = []
    for line in raw_lines.split('\n'):
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        parts = line.split(csv_sep)
        if not header:
            header = parts
            continue
        if len(header) != len(parts):
            _logger.warning('skip peers line with mismatch in field count')
            continue
        entry = dict(zip(header, parts))
        peers.append(entry)
    _logger.debug('parsed form into peers: %s' % peers)
    return peers


def parse_peers(configuration, peers_list, peers_upload, peers_form,
                peers_url):
    """Parse provided peer formats into a list of peer users"""
    _logger = configuration.logger
    peers = []
    if peers_list:
        peers += peers_list
    elif peers_upload:
        # TODO: extract upload
        raw_peers = ''
        peers += parse_peers_form(configuration, raw_peers)
    elif peers_form:
        peers += parse_peers_form(configuration, peers_form)
    elif peers_url:
        # TODO: fetch URL contents
        raw_peers = ''
        peers += parse_peers_form(configuration, raw_peers)
    else:
        _logger.error("no peers provided")
    return peers


def signature():
    """Signature of the main function"""

    defaults = {
        'peers_label': REJECT_UNSET,
        'peers_kind': REJECT_UNSET,
        'peers_expire': [''],
        'peers_list': [],
        'peers_upload': [''],
        'peers_form': [''],
        'peers_url': [''],
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

    # force name to capitalized form (henrik karlsen -> Henrik Karlsen)

    label = accepted['peers_label'][-1].strip()
    kind = accepted['peers_kind'][-1].strip()
    expire = accepted['peers_expire'][-1].strip()
    peers_list = accepted['peers_list']
    peers_upload = accepted['peers_upload'][-1].strip()
    peers_form = accepted['peers_form'][-1].strip()
    peers_url = accepted['peers_url'][-1].strip()

    # TODO: check valid kind and date
    if not expire:
        expire = datetime.datetime.now()
        expire += datetime.timedelta(days=30)

    peers_path = os.path.join(configuration.user_settings, client_dir,
                              peers_filename)
    try:
        all_peers = load(peers_path)
    except Exception, exc:
        logger.warning("could not load peers from: %s" % exc)
        all_peers = {}

    all_peers[label] = all_peers.get(label, {})
    peers = parse_peers(configuration, peers_list, peers_upload, peers_form,
                        peers_url)
    all_peers[label].update({
        'label': label,
        'kind': kind,
        'expire': expire,
        'peers': peers
    })

    try:
        dump(all_peers, peers_path)
        logger.debug('saved %s peers %s to %s' % (client_id, all_peers,
                                                  peers_path))
        output_objects.append(
            {'object_type': 'text', 'text': "Peers saved/updated"})
    except Exception, exc:
        logger.error('Failed to save %s peers to %s' % (client_id, peers_path))
        output_objects.append({'object_type': 'error_text', 'text': '''
Peers could not be saved. Please contact the site admins on %s if this error
persists.
''' % admin_email})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.info('Saved %s peers to %s' % (client_id, peers_path))
    email_header = '%s Peers Update' % configuration.short_title
    email_msg = """
User %s saved new peers data
""" % client_id
    email_msg += """
Label: %(label)s
Kind: %(kind)s
Expire: %(expire)s
Peers:
%(peers)s
""" % all_peers[label]

    logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                % (admin_email, email_header, email_msg, smtp_server))
    if not send_email(admin_email, email_header, email_msg, logger,
                      configuration):
        output_objects.append({'object_type': 'error_text', 'text': '''
An error occured trying to send the email with saved peers to the site
administrators. Please inform them (%s) if the problem persists.
''' % admin_email})
        return (output_objects, returnvalues.SYSTEM_ERROR)
    return (output_objects, returnvalues.OK)
