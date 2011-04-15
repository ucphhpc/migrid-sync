#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# user - helper functions for user related tasks
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

"""User related functions - especially for People interface"""

import dircache
import os
try:
    from hashlib import md5 as hash_algo
except ImportError:
    from md5 import new as hash_algo

from shared.base import client_dir_id
from shared.findtype import is_user
from shared.settings import load_settings
from shared.useradm import client_id_dir

def anon_user_id(user_id):
    """Generates an anonymous but (practically) unique user ID for user with
    provided unique user_id. The anonymous ID is just a md5 hash of the
    user_id to keep ID relatively short.
    """
    anon_id = hash_algo(user_id).hexdigest()
    return anon_id

def list_users(user_home):
    """Return a list of all users by listing the user homes in user_home.
    Uses dircache for efficiency when used more than once per session.
    """
    users = []
    children = dircache.listdir(user_home)
    for name in children:
        path = os.path.join(user_home, name)

        # skip all files and dot dirs - they are _not_ users
        
        if not os.path.isdir(path):
            continue
        if path.find(os.sep + '.') != -1:
            continue
        if path.find('no_grid_jobs_in_grid_scheduler') != -1:
            continue
        users.append(client_dir_id(name))
    return users

def anon_to_real_user_map(user_home):
    """Return a mapping from anonymous user names to real names"""
    anon_map = {}
    for name in list_users(user_home):
        anon_map[anon_user_id(name)] = name
    return anon_map

def real_to_anon_user_map(user_home):
    """Return a mapping from real user names to anonymous names"""
    user_map = {}
    for name in list_users(user_home):
        user_map[name] = anon_user_id(name)
    return user_map

def get_user_conf(user_id, configuration, include_meta=False):
    """Return user profile and settings"""
    return load_settings(user_id, configuration, include_meta)
