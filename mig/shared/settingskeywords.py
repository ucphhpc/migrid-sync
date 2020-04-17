#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settingskeywords - keywords for basic user settings
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Keywords in the settings files"""


def get_settings_specs():
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """

    specs = []
    specs.append(('EMAIL', {
        'Title': 'E-mail address',
        'Description': 'List of E-mail addresses',
        'Example': 'my@email.com, my_other@email.com',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'notify',
        'Required': False,
    }))
    """ specs.append(('JABBER', {
        'Title': 'Jabber address',
        'Description': 'List of Jabber addresses',
        'Example': 'me@jabber.com, me2@jabber.com',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'notify',
        'Required': False,
        })) """
    """ specs.append(('MSN', {
        'Title': 'MSN address',
        'Description': 'List of MSN addresses',
        'Example': 'me@hotmail.com, me2@hotmail.com',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'notify',
        'Required': False,
        })) """
    """ specs.append(('ICQ', {
        'Title': 'ICQ address',
        'Description': 'List of ICQ numbers',
        'Example': '2364236, 2342342',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'notify',
        'Required': False,
        })) """
    """ specs.append(('AOL', {
        'Title': 'AOL address',
        'Description': 'List of AOL addresses',
        'Example': 'me@aol.com, me2@aol.com',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'notify',
        'Required': False,
        })) """
    """ specs.append(('YAHOO', {
        'Title': 'Yahoo messenger address',
        'Description': 'List of Yahoo! addresses',
        'Example': 'me@yahoo.com, me2@hotmail.com',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'notify',
        'Required': False,
        })) """
    specs.append(('LANGUAGE', {
        'Title': 'Language',
        'Description': 'Your preferred interface language',
        'Example': 'English',
        'Type': 'string',
        'Value': 'English',
        'Context': 'localization',
        'Required': False,
    }))
    specs.append(('USER_INTERFACE', {
        'Title': 'User Interface',
        'Description': 'Your preferred web interface',
        'Example': 'V3',
        'Type': 'string',
        'Value': 'V2',
        'Context': 'appearance',
        'Required': False,
    }))
    specs.append(('DEFAULT_PAGE', {
        'Title': 'Default Page',
        'Description': 'Your preferred page opened on login',
        'Example': 'fileman',
        'Type': 'string',
        'Value': 'home',
        'Context': 'appearance',
        'Required': False,
    }))
    specs.append(('SUBMITUI', {
        'Title': 'Submit interface',
        'Description': 'Your preferred Submit Job interface',
        'Example': 'fields',
        'Type': 'string',
        'Value': 'textarea',
        'Context': 'appearance',
        'Required': False,
    }))
    specs.append(('SITE_BASE_MENU', {
        'Title': 'Base menu',
        'Description': 'Which base menu to use.',
        'Example': 'simple',
        'Type': 'string',
        'Value': 'default',
        'Context': 'appearance',
        'Required': False,
    }))
    specs.append(('SITE_USER_MENU', {
        'Title': 'User menu items',
        # can be chosen from configuration.user_menu
        'Description': 'Additional menu items.',
        'Example': '...choose from the list',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'appearance',
        'Required': False,
    }))
    specs.append(('SITE_COLLABORATION_LINKS', {
        'Title': 'Collaboration links',
        'Description': 'Which group collaboration components to use.',
        'Example': 'advanced',
        'Type': 'string',
        'Value': 'default',
        'Context': 'appearance',
        'Required': False,
    }))
    specs.append(('ENABLE_WIDGETS', {
        'Title': 'Enable widgets',
        'Description': 'If you want to be able to customize your grid pages '
        'with custom content. Widgets are specified on your widgets settings '
        'page when enabled.',
        'Example': 'True',
        'Type': 'boolean',
        'Value': True,
        'Context': 'appearance',
        'Required': False,
    }))
    return specs


def get_keywords_dict():
    """Return mapping between settings keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_settings_specs())
