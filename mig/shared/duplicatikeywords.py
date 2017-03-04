#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# duplicatikeywords - keywords used in the duplicati settings file
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

conf_template = '''{
    "CreatedBy": "%(short_title)s v1.0",
    "Schedule": {
        "Repeat": "1D"
    },
    "Backup": {
        "Name": "%(backup_name)s",
        "TargetURL": "%(protocol)s://%(fqdn)s/%(backup_dir)s?auth-username=%(username)s&auth-password=%(password)s",
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
    }
}
'''

def extract_duplicati_helper(configuration, client_id, duplicati_dict):
    """Fill helper dictionary with values used in conf_template"""
    # lokop fqdn, username and password for specified protocol
    protocol = duplicati_dict.get('PROTOCOL',
                                  configuration.user_duplicati_protocol)
    username = duplicati_dict.get('USERNAME')
    password = duplicati_dict.get('PASSWORD', '')
    if protocol in ('webdavs', 'davs'):
        fqdn = "%s:%s" % (configuration.user_davs_show_address,
                          configuration.user_davs_show_port)
    elif protocol == 'sftp':
        fqdn = "%s:%s" % (configuration.user_sftp_show_address,
                          configuration.user_sftp_show_port)
    elif protocol == 'ftps':
        fqdn = "%s:%s" % (configuration.user_ftps_show_address,
                          configuration.user_ftps_show_port)
    fill_helper = {'short_title': configuration.short_title,
                   'protocol': protocol,
                   'fqdn': fqdn, 
                   'username': username,
                   'password': password}
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
        'Required': True,
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
        'Description': 'Password for given protocol when communicating with the server.',
        'Example': '********',
        'Type': 'string',
        'Value': '',
        'Editor': 'password',
        'Context': 'duplicati',
        'Required': True,
        }))
    return specs

def get_keywords_dict():
    """Return mapping between duplicati keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_duplicati_specs())
