#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# profilekeywords - [insert a few words of module description on this line]
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""Keywords in the profile files"""
from __future__ import absolute_import

from .shared.defaults import profile_img_max_kb

def get_profile_specs():
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """

    specs = []
    specs.append(('PUBLIC_PROFILE', {
        'Title': 'Public profile information visible to other users',
        'Description': 'Free text profile information visible to any user.',
        'Example': 'Hello! My name is John Doe. My email is john@doe.net .',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'profile',
        'Required': False,
        }))
    specs.append(('PUBLIC_IMAGE', {
        'Title': 'Public profile image visible to other users',
        'Description': 'Path to small (<%dkb) png or jpg image in your user home.' % profile_img_max_kb,
        'Example': 'pics/me.png',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'profile',
        'Required': False,
        }))
    specs.append(('VGRIDS_ALLOW_EMAIL', {
        'Title': 'VGrids allowed to email you',
        'Description': 'List of VGrids for which members can send you emails.',
        'Example': 'ANY',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'appearance',
        'Required': False,
        }))
    specs.append(('VGRIDS_ALLOW_IM', {
        'Title': 'VGrids allowed to send you instant messages',
        'Description': 'List of VGrids for which members can send you IMs.',
        'Example': 'ANY',
        'Type': 'multiplestrings',
        'Value': [],
        'Context': 'appearance',
        'Required': False,
        }))
    specs.append(('HIDE_EMAIL_ADDRESS', {
        'Title': 'Hide your raw email address even from VGrids allowed to contact you?',
        'Description': 'Disable to unmask your email address to VGrids that you have granted contact access.',
        'Example': 'True',
        'Type': 'boolean',
        'Value': True,
        'Context': 'appearance',
        'Required': False,
        }))
    specs.append(('HIDE_IM_ADDRESS', {
        'Title': 'Hide your raw IM addresses even from VGrids allowed to contact you?',
        'Description': 'Disable to unmask your IM addresses to VGrids that you have granted contact access.',
        'Example': 'True',
        'Type': 'boolean',
        'Value': True,
        'Context': 'appearance',
        'Required': False,
        }))
    specs.append(('ANONYMOUS', {
        'Title': 'User ID visible to other user? ',
        'Description': 'Disable to unmask your user ID to other users.',
        'Example': 'True',
        'Type': 'boolean',
        'Value': True,
        'Context': 'appearance',
        'Required': False,
        }))
    return specs

def get_keywords_dict():
    """Return mapping between profile keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_profile_specs())
