#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridkeywords - Mapping of available VGrid keywords and specs
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

"""Keywords in the VGrid context like event triggers and VGrid settings:
Works as a combined specification of and source of information about keywords.
"""

from shared.defaults import default_vgrid, any_vgrid, keyword_owners, \
     keyword_members, keyword_all, keyword_auto, keyword_never, \
     keyword_any, default_vgrid_settings_limit

# This is the main location for defining trigger keywords. All other trigger
# handling functions should only operate on keywords defined here.


def get_trigger_specs(configuration):
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """
    vgrid_label = configuration.site_vgrid_label
    specs = []
    specs.append(('rule_id', {
        'Title': 'Rule ID',
        'Description': 'Unique trigger rule ID',
        'Example': 'rule-xyz',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': True,
        }))
    specs.append(('vgrid_name', {
        'Title': '%s Name' % vgrid_label,
        'Description': 'Unique %s ID' % vgrid_label,
        'Example': 'myproject',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': True,
        }))
    specs.append(('path', {
        'Title': 'Path',
        'Description': 'A pattern or path to trigger events on',
        'Example': 'myfile.txt',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': True,
        }))
    specs.append(('changes', {
        'Title': 'Changes',
        'Description': 'A list of file changes to act on',
        'Example': '["modified", "created"]',
        'Type': 'multiplestrings',
        'Instance': list,
        'Value': [],
        'Required': True,
        }))
    specs.append(('run_as', {
        'Title': 'Run As User',
        'Description': '''The ID of the user owning the trigger and thus the
user associated with any resulting jobs''',
        'Example': '/C=DK/CN=John Doe/emailAddress=john@doe.org',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': True,
        }))
    specs.append(('action', {
        'Title': 'Action',
        'Description': 'An action to perform when the trigger applies',
        'Example': 'submit',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': True,
        }))
    specs.append(('arguments', {
        'Title': 'Arguments',
        'Description': 'List of arguments for the requested action',
        'Example': '["unzip +TRIGGERPATH+"]',
        'Type': 'multiplestrings',
        'Instance': list,
        'Value': [],
        'Required': True,
        }))
    specs.append(('rate_limit', {
        'Title': 'Rate Limit',
        'Description': '''Ignore additional events after detecting this many
events in specified period''',
        'Example': '1/m',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': False,
        }))
    specs.append(('settle_time', {
        'Title': 'Settle Time',
        'Description': 'Treat all events within this time frame as one',
        'Example': '10s',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': False,
        }))
    specs.append(('match_files', {
        'Title': 'Match Files',
        'Description': 'If trigger applies for files',
        'Example': 'True',
        'Type': 'boolean',
        'Instance': bool,
        'Value': True,
        'Required': False,
        }))
    specs.append(('match_dirs', {
        'Title': 'Match Directories',
        'Description': 'If trigger applies for directories',
        'Example': 'True',
        'Type': 'boolean',
        'Instance': bool,
        'Value': True,
        'Required': False,
        }))
    specs.append(('match_recursive', {
        'Title': 'Match Recursively',
        'Description': 'If trigger applies recursively for sub-directories',
        'Example': 'False',
        'Type': 'boolean',
        'Instance': bool,
        'Value': False,
        'Required': False,
        }))
    specs.append(('templates', {
        'Title': 'Templates',
        'Description': 'Internal list of parsed jobs for submit rules',
        'Example': '["::EXECUTE::\nuname -a\n"]',
        'Type': 'multiplestrings',
        'Instance': list,
        'Value': [],
        'Required': False,
        }))
    return specs

def get_trigger_keywords_dict(configuration):
    """Return mapping between trigger keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_trigger_specs(configuration))


def get_settings_specs(configuration):
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """
    vgrid_label = configuration.site_vgrid_label
    specs = []
    specs.append(('vgrid_name', {
        'Title': '%s Name' % vgrid_label,
        'Description': 'Unique %s ID' % vgrid_label,
        'Example': 'myproject',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Inherit': keyword_never,
        'Required': True,
        }))
    specs.append(('description', {
        'Title': '%s Description' % vgrid_label,
        'Description': 'A short public description of %s' % vgrid_label,
        'Example': 'This is our shared project workspace',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Inherit': keyword_never,
        'Required': True,
        }))
    specs.append(('visible_owners', {
        'Title': 'Visibility of Owners List',
        'Description': 'A keyword to define who can see the list of owners',
        'Example': '%s' % keyword_owners,
        'Type': 'string',
        'Instance': basestring,
        'Value': keyword_owners,
        'Inherit': keyword_auto,
        'Required': True,
        }))
    specs.append(('visible_members', {
        'Title': 'Visibility of Members List',
        'Description': 'A keyword to define who can see the list of members',
        'Example': '%s' % keyword_owners,
        'Type': 'string',
        'Instance': basestring,
        'Value': keyword_owners,
        'Inherit': keyword_auto,
        'Required': True,
        }))
    specs.append(('visible_resources', {
        'Title': 'Visibility of Resources List',
        'Description': 'A keyword to define who can see the list of resources',
        'Example': '%s' % keyword_owners,
        'Type': 'string',
        'Instance': basestring,
        'Value': keyword_owners,
        'Inherit': keyword_auto,
        'Required': True,
        }))
    specs.append(('create_sharelink', {
        'Title': 'Limit Sharelink Creation',
        'Description': '''A keyword to limit who can create sharelinks inside
shared folder''',
        'Example': '%s' % keyword_owners,
        'Type': 'string',
        'Instance': basestring,
        'Value': keyword_owners,
        'Inherit': keyword_auto,
        'Required': False,
        }))
    specs.append(('request_recipients', {
        'Title': 'Request Recipients',
        'Description': 'Notify only first N owners about access requests',
        'Example': '%d' % default_vgrid_settings_limit,
        'Type': 'int',
        'Instance': int,
        'Value': default_vgrid_settings_limit,
        'Inherit': keyword_auto,
        'Required': True,
        }))
    specs.append(('restrict_settings_adm', {
        'Title': 'Restrict Settings Administration',
        'Description': 'Allow only first N owners to manage settings',
        'Example': '%d' % default_vgrid_settings_limit,
        'Type': 'int',
        'Instance': int,
        'Value': default_vgrid_settings_limit,
        'Inherit': keyword_auto,
        'Required': False,
        }))
    specs.append(('restrict_owners_adm', {
        'Title': 'Restrict Owner Administration',
        'Description': 'Allow only first N owners to manage owners',
        'Example': '%d' % default_vgrid_settings_limit,
        'Type': 'int',
        'Instance': int,
        'Value': default_vgrid_settings_limit,
        'Inherit': keyword_auto,
        'Required': False,
        }))
    specs.append(('restrict_members_adm', {
        'Title': 'Restrict Member Administration',
        'Description': 'Allow only first N owners to manage members',
        'Example': '%d' % default_vgrid_settings_limit,
        'Type': 'int',
        'Instance': int,
        'Value': default_vgrid_settings_limit,
        'Inherit': keyword_auto,
        'Required': False,
        }))
    specs.append(('restrict_resources_adm', {
        'Title': 'Restrict Resource Administration',
        'Description': 'Allow only first N owners to manage resources',
        'Example': '%d' % default_vgrid_settings_limit,
        'Type': 'int',
        'Instance': int,
        'Value': default_vgrid_settings_limit,
        'Inherit': keyword_auto,
        'Required': False,
        }))
    specs.append(('hidden', {
        'Title': 'Hidden on Public %s List' % vgrid_label,
        'Description': '''If %s should be hidden except to participants
(recursively)''' % vgrid_label,
        'Example': 'False',
        'Type': 'boolean',
        'Instance': bool,
        'Value': False,
        'Inherit': keyword_any,
        'Required': False,
        }))
    specs.append(('read_only', {
        'Title': 'Read-only Data',
        'Description': 'If shared data is write-protected (recursively)',
        'Example': 'False',
        'Type': 'boolean',
        'Instance': bool,
        'Value': False,
        'Inherit': keyword_any,
        'Required': False,
        }))
    return specs

def get_settings_keywords_dict(configuration):
    """Return mapping between settings keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_settings_specs(configuration))
