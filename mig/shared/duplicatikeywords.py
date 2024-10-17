#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# duplicatikeywords - keywords used in the duplicati settings file
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

"""Keywords in the duplicati files"""

from __future__ import absolute_import

from mig.shared.defaults import protocol_aliases, duplicati_schedule_choices
from mig.shared.url import urlencode


duplicati_conf_templates = {'version': '''    "CreatedBy": "%(short_title)s v1.0"''',
                            'schedule': '''    "Schedule": {
        "Repeat": "%(schedule_freq)s",
    }''',
                            'backup': '''    "Backup": {
        "Name": "%(backup_name)s",
        "TargetURL": "%(protocol)s://%(fqdn)s/%(backup_dir)s?%(credentials)s",
        "Settings": [
            {
                "Name": "encryption-module",
                "Value": null,
            },
            {
                "Name": "dblock-size",
                "Value": "50mb",
            }
        ],
    }'''
                            }

schedule_map = dict(duplicati_schedule_choices)


def get_duplicati_protocol_map(configuration, reverse=False):
    """Simple helper to extract supported storage protocols from conf and map
    them to user-friendly aliases. If the optional reverse argument is set the
    map is reversed to map from aliases to protocols instead of vice-versa.
    """
    if reverse:
        return {protocol_aliases[i]: i for i in configuration.storage_protocols}
    else:
        return {i: protocol_aliases[i] for i in configuration.storage_protocols}


# TODO: this function should probably move to shared.settings or something

def extract_duplicati_helper(configuration, client_id, duplicati_dict):
    """Fill helper dictionary with values used in duplicati_conf_templates"""
    # lookup fqdn, username, etc for specified protocol
    rev_proto_map = get_duplicati_protocol_map(configuration, reverse=True)
    if configuration.storage_protocols:
        default_alias = protocol_aliases[configuration.storage_protocols[0]]
    else:
        default_alias = ''
    protocol_alias = duplicati_dict.get('PROTOCOL', default_alias)
    username = duplicati_dict.get('USERNAME')
    password = duplicati_dict.get('PASSWORD', '')
    credentials = [('auth-username', username)]
    if password:
        credentials.append(('auth-password', password))
    # We hard-code knowledge about host user_sftp_key_pub type and size here
    # TODO: extract key information from key or add conf entry instead?
    fingerprint = 'ssh-rsa 2048 %s' % configuration.user_sftp_key_md5
    fingerprint_parts = fingerprint.split(' ', 2)
    if fingerprint_parts[1:]:
        bits_part = fingerprint_parts[1]
    else:
        bits_part = '__UNSET__'
    # NOTE: we can't use server key fingerprint helper for https/ftps since
    #       cert renew will change the hash and thus break existing confs.
    schedule_alias = duplicati_dict.get('SCHEDULE', '')
    schedule_freq = schedule_map.get(schedule_alias, '')
    protocol = rev_proto_map[protocol_alias]
    if protocol in ('webdavs', 'davs'):
        # Duplicati client requires webdavs://BLA
        protocol = 'webdavs'
        fqdn = "%s:%s" % (configuration.user_davs_show_address,
                          configuration.user_davs_show_port)
    elif protocol == 'sftp':
        # Duplicati client requires webdavs://BLA
        protocol = 'ssh'
        # Expose server key fingerprint to client to avoid prompt
        if fingerprint:
            credentials.append(('ssh-fingerprint', fingerprint))
        fqdn = "%s:%s" % (configuration.user_sftp_show_address,
                          configuration.user_sftp_show_port)
    elif protocol == 'ftps':
        # NOTE: we used to need this workaround due to port fwd routing issues
        # Duplicati client requires aftp://BLA with connection tweaks
        #protocol = 'aftp'
        #credentials.append(('aftp-encryption-mode', 'Explicit'))
        #credentials.append(('aftp-data-connection-type', 'PASV'))
        fqdn = "%s:%s" % (configuration.user_ftps_show_address,
                          configuration.user_ftps_show_ctrl_port)
    # NOTE: We must encode e.g. '@' in username and exotic chars in password.
    encoded_creds = urlencode(credentials)
    # NOTE: Duplicati requires '%20' space-encoding and urlencode produces '+'
    # TODO: drop this workaround once fixed in Duplicati
    encoded_creds = encoded_creds.replace('+%s+' % bits_part,
                                          '%%20%s%%20' % bits_part)
    fill_helper = {'short_title': configuration.short_title,
                   'protocol': protocol,
                   'fqdn': fqdn,
                   'credentials': encoded_creds,
                   'schedule_freq': schedule_freq}
    return fill_helper


def get_duplicati_specs():
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """

    specs = []
    specs.append(('BACKUPS', {
        'Title': 'Backup IDs',
        'Description': 'List of backup set IDs.',
        'Example': 'Documents\nMail\nExperiments',
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'input',
        'Context': 'duplicati',
        # We need to allow empty to let users disable again
        'Required': False,
    }))
    specs.append(('PROTOCOL', {
        'Title': 'Transfer protocol',
        'Description': 'Which protocol to use for communicating with the server.',
        'Example': 'sftp',
        'Type': 'string',
        'Value': '',
        'Editor': 'select',
        'Context': 'duplicati',
        'Required': True,
    }))
    specs.append(('USERNAME', {
        'Title': 'Username',
        'Description': 'Username for given protocol when communicating with the server.',
        'Example': 'bardino@nbi.ku.dk',
        'Type': 'string',
        'Value': '',
        'Editor': 'select',
        'Context': 'duplicati',
        'Required': True,
    }))
    specs.append(('PASSWORD', {
        'Title': 'Password',
        'Description': '''Optionally enter the password for given protocol when
communicating with the server. You can leave it out here and just enter it in
the client. It is the password you set on your corresponding protocol Settings
page here.''',
        'Example': '********',
        'Type': 'string',
        'Value': '',
        # We do not expose password as it would appear as clear text in json
        'Editor': 'hidden',
        'Context': 'duplicati',
        'Required': False,
    }))
    specs.append(('SCHEDULE', {
        'Title': 'Schedule',
        'Description': 'Optional scheduling of automatic runs this often.',
        'Example': 'Weekly',
        'Type': 'string',
        'Value': 'Daily',
        'Editor': 'select',
        'Context': 'duplicati',
        'Required': False,
    }))
    return specs


def get_keywords_dict():
    """Return mapping between duplicati keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_duplicati_specs())
