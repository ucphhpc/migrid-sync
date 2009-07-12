#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# fix_user_id - a simple helper to migrate old CN to new DN user IDs
# Copyright (C) 2009  Jonas Bardino
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

"""Upgrade all files and dirs to use the new certificate DN based user ID
instead of the old CN based ones"""

import os
import sys

from shared.useradm import search_users, default_search, migrate_user

if '__main__' == __name__:
    if len(sys.argv) < 3:
        print 'Usage: %s CONF_PATH DB_PATH' % sys.argv[0]
        print 'Upgrade all files and dirs to new certificate DN format'
        print 'based on the MiG server configuration in CONF_PATH and the'
        print 'MiG user database in DB_PATH.'
        sys.exit(1)

    conf_path = sys.argv[1]
    db_path = sys.argv[2]
    search_filter = default_search()
    all_users = search_users(search_filter, conf_path, db_path)

    for (user_id, user_dict) in all_users:
        migrate_user(user_id, conf_path, db_path)
