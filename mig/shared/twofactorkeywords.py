#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# twofactorkeywords - supported web access settings
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Keywords in the web access settings"""


def get_twofactor_specs(configuration):
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """

    specs = []
    if configuration.migserver_https_mig_oid_url and \
            configuration.user_mig_oid_provider:
        specs.append(('MIG_OID_TWOFACTOR', {
            'Title': 'Enable 2-FA for %s OpenID login' %
            configuration.user_mig_oid_title,
            'Description': '''Add an extra layer of security to your %s OpenID
logins through a personal auth token generator on your phone or tablet.
''' % configuration.user_mig_oid_title,
            'Example': 'True',
            'Type': 'boolean',
            'Value': False,
            'Editor': 'select',
            'Context': 'twofactor',
            'Required': False,
        }))
    if configuration.migserver_https_ext_oid_url and \
            configuration.user_ext_oid_provider:
        specs.append(('EXT_OID_TWOFACTOR', {
            'Title': 'Enable 2-FA for %s OpenID login' %
            configuration.user_ext_oid_title,
            'Description': '''Add an extra layer of security to your %s OpenID
logins through a personal auth token generator on your phone or tablet.
''' % configuration.user_ext_oid_title,
            'Example': 'True',
            'Type': 'boolean',
            'Value': False,
            'Editor': 'select',
            'Context': 'twofactor',
            'Required': False,
        }))
    return specs


def get_keywords_dict(configuration):
    """Return mapping between profile keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_twofactor_specs(configuration))
