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


def get_keywords_dict():
    site_script_deps = {
        'Description': 'Widget script dependencies',
        'Example': 'jquery',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'select',
        'Required': False,
        }
    premenu = {
        'Description': 'Widget before menu',
        'Example': '',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'menu',
        'Required': False,
        }
    postmenu = {
        'Description': 'Widget after menu',
        'Example': '',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'menu',
        'Required': False,
        }
    precontent = {
        'Description': 'Widget before content',
        'Example': '',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'content',
        'Required': False,
        }
    postcontent = {
        'Description': 'Widget after content',
        'Example': '',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'content',
        'Required': False,
        }
    
    # create the keywords in a single dictionary

    keywords_dict = {
        'SITE_SCRIPT_DEPS': site_script_deps,
        'PREMENU': premenu,
        'POSTMENU': postmenu,
        'PRECONTENT': precontent,
        'POSTCONTENT': postcontent,
        }

    return keywords_dict


