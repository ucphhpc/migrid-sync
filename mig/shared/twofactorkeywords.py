#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# twofactorkeywords - supported two factor settings
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

"""Keywords in the two factor settings"""


def check_twofactor_deps(configuration, client_id, twofactor_dict):
    """Go through 2FA dependencies and return a boolean to indicate if
    all dependencies are satisfied. I.e. web 2FA must be enabled before IO
    2FA is allowed.
    """
    dep_enabled, core_enabled = False, False
    specs_dict = get_keywords_dict(configuration)
    for (field, spec) in specs_dict.items():
        if spec.get('Context', None) == 'twofactor':
            if twofactor_dict.get(field, None):
                core_enabled = True
        elif spec.get('Context', None) == 'twofactor_dep':
            if twofactor_dict.get(field, None):
                dep_enabled = True

    if dep_enabled and not core_enabled:
        return False
    return True


def get_twofactor_specs(configuration):
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """

    specs = []
    # NOTE: we currently share OpenID 2.0 and Connect settings
    if configuration.migserver_https_mig_oid_url and \
            configuration.user_mig_oid_provider or \
            configuration.migserver_https_mig_oidc_url and \
            configuration.user_mig_oidc_provider:
        specs.append(('MIG_OID_TWOFACTOR', {
            'Title': 'Enable 2-FA for %s OpenID web login' %
            configuration.user_mig_oid_title,
            'Description': '''Add an extra layer of security to your %s OpenID
web logins through a personal auth token generator on your phone or tablet.
''' % configuration.user_mig_oid_title,
            'Example': 'True',
            'Type': 'boolean',
            'Value': False,
            'Editor': 'select',
            'Context': 'twofactor',
            'Required': False,
        }))
    if configuration.migserver_https_ext_oid_url and \
            configuration.user_ext_oid_provider or \
            configuration.migserver_https_ext_oidc_url and \
            configuration.user_ext_oidc_provider:
        specs.append(('EXT_OID_TWOFACTOR', {
            'Title': 'Enable 2-FA for %s OpenID web login' %
            configuration.user_ext_oid_title,
            'Description': '''Add an extra layer of security to your %s OpenID
web logins through a personal auth token generator on your phone or tablet.
''' % configuration.user_ext_oid_title,
            'Example': 'True',
            'Type': 'boolean',
            'Value': False,
            'Editor': 'select',
            'Context': 'twofactor',
            'Required': False,
        }))
    if configuration.site_enable_davs:
        specs.append(('WEBDAVS_TWOFACTOR', {
            'Title': 'Enable 2-FA for WebDAVS network drive or client login',
            'Description': '''Add an extra layer of security to your WebDAVS
logins through a personal auth token generator on your phone or tablet.
Works by logging in to the %s web site with 2FA enabled to start
an authenticated session and then logging into WebDAVS as usual.
''' % configuration.short_title,
            'Example': 'True',
            'Type': 'boolean',
            'Value': False,
            'Editor': 'select',
            'Context': 'twofactor_dep',
            'Required': False,
        }))
    if configuration.site_enable_sftp \
            or configuration.site_enable_sftp_subsys:
        specs.append(('SFTP_PASSWORD_TWOFACTOR', {
            'Title': 'Enable 2-FA for SFTP network drive or client login with password',
            'Description': '''Add an extra layer of security to your SFTP password
logins through a personal auth token generator on your phone or tablet.
Works by logging in to the %s web site with 2FA enabled to start
an authenticated session and then logging into SFTP as usual.
''' % configuration.short_title,
            'Example': 'True',
            'Type': 'boolean',
            'Value': False,
            'Editor': 'select',
            'Context': 'twofactor_dep',
            'Required': False,
        }))
    if configuration.site_enable_sftp \
            or configuration.site_enable_sftp_subsys:
        specs.append(('SFTP_KEY_TWOFACTOR', {
            'Title': 'Enable 2-FA for SFTP network drive or client login with key',
            'Description': '''Add an extra layer of security to your SFTP key
logins through a personal auth token generator on your phone or tablet.
Works by logging in to the %s web site with 2FA enabled to start
an authenticated session and then logging into SFTP as usual.
''' % configuration.short_title,
            'Example': 'True',
            'Type': 'boolean',
            'Value': False,
            'Editor': 'select',
            'Context': 'twofactor_dep',
            'Required': False,
        }))
    if configuration.site_enable_ftps:
        specs.append(('FTPS_TWOFACTOR', {
            'Title': 'Enable 2-FA for FTPS network drive or client login',
            'Description': '''Add an extra layer of security to your FTPS
logins through a personal auth token generator on your phone or tablet.
Works by logging in to the %s web site with 2FA enabled to start
an authenticated session and then logging into FTPS as usual.
''' % configuration.short_title,
            'Example': 'True',
            'Type': 'boolean',
            'Value': False,
            'Editor': 'select',
            'Context': 'twofactor_dep',
            'Required': False,
        }))

    return specs


def get_keywords_dict(configuration):
    """Return mapping between profile keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_twofactor_specs(configuration))
