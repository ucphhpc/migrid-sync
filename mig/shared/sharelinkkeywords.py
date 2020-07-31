#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sharelinkkeywords - Mapping of available sharelink keywords and specs
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

"""Keywords in the sharelink dictionaries:
Works as a combined specification of and source of information about keywords.
"""
from __future__ import absolute_import

import datetime

from mig.shared.defaults import keyword_all

# This is the main location for defining sharelink keywords. All other
# sharelink handling functions should only operate on keywords defined here.

def get_sharelink_specs(configuration):
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """
    specs = []
    specs.append(('share_id', {
        'Title': 'Share Link ID',
        'Description': 'Unique share link ID',
        'Example': 'hoDcSikTC6',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': True,
        }))
    specs.append(('path', {
        'Title': 'Path',
        'Description': 'The file or directory to share',
        'Example': 'myfile.txt',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': True,
        }))
    specs.append(('access', {
        'Title': 'Access List',
        'Description': 'List of access modes: read or write',
        'Example': '["read"]',
        'Type': 'multiplestrings',
        'Instance': list,
        'Value': ['read'],
        'Required': True,
        }))
    specs.append(('invites', {
        'Title': 'Invite List',
        'Description': 'List of invited email addresses',
        'Example': '["john@doe.org"]',
        'Type': 'multiplestrings',
        'Instance': list,
        'Value': ['john@doe.org'],
        'Required': True,
        }))
    specs.append(('single_file', {
        'Title': 'Single File Share',
        'Description': 'If sharelink points to a single file and not a folder',
        'Example': 'True',
        'Type': 'boolean',
        'Instance': bool,
        'Value': True,
        'Required': True,
        }))    
    specs.append(('expire', {
        'Title': 'Expire',
        'Description': 'When the share link expires if ever',
        'Example': '42',
        'Type': 'string',
        'Instance': basestring,
        'Value': '-1',
        'Required': False,
        }))
    specs.append(('owner', {
        'Title': 'Owner',
        'Description': 'ID of the sharelink owner',
        'Example': '/C=DK/CN=John Doe/emailAddress=john@doe.org',
        'Type': 'string',
        'Instance': basestring,
        'Value': '',
        'Required': False,
        }))
    specs.append(('created_timestamp', {
        'Title': 'Creation Time',
        'Description': 'Timestamp for when sharelink was created',
        'Example': '%s' % datetime.datetime.now(),
        'Type': 'datetime.datetime',
        'Instance': datetime.datetime,
        'Value': datetime.datetime.now(),
        'Required': False,
        }))    
    return specs

def get_sharelink_keywords_dict(configuration):
    """Return mapping between sharelink keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_sharelink_specs(configuration))

