#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# widgetskeywords - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Keywords in the widgets files"""


def get_widgets_specs():
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """

    specs = []
    specs.append(('SITE_SCRIPT_DEPS', {
        'Description': 'Scripts needed for your widgets',
        'Example': 'jquery',
        'Type': 'multiplestrings',
        'Value': ['jquery.js'],
        'Context': 'select',
        'Required': False,
        }))
    specs.append(('PREMENU', {
        'Description': 'Widgets displayed before menu',
        'Example': '',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'menu',
        'Required': False,
        }))
    specs.append(('POSTMENU', {
        'Description': 'Widgets displayed after menu',
        'Example': '',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'menu',
        'Required': False,
        }))
    specs.append(('PRECONTENT', {
        'Description': 'Widgets displayed before content',
        'Example': '',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'content',
        'Required': False,
        }))
    specs.append(('POSTCONTENT', {
        'Description': 'Widgets displayed after content',
        'Example': '',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'content',
        'Required': False,
        }))
    return specs

def get_keywords_dict():
    """Return mapping between widgets keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_widgets_specs())
