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
import getopt

from shared.useradm import init_user_adm, search_users, default_search, \
     migrate_user

def usage(name='fix_user_db.py'):
    """Usage help"""

    print """Update MiG user database and user dirs from old format with CN
as user idetifier to new format with DN as user identifier.

Usage:
%(name)s [OPTIONS]
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force operations to continue past errors
   -h                  Show this help
   -v                  Verbose output
"""\
         % {'name': name}

if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    force = False
    verbose = False
    opt_args = 'c:d:fhv'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError, err:
        print 'Error: ', err.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            conf_path = val
        elif opt == '-d':
            db_path = val
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-v':
            verbose = True
        else:
            print 'Error: %s not supported!' % opt
            sys.exit(1)

    search_filter = default_search()
    all_users = search_users(search_filter, conf_path, db_path, verbose)

    for (user_id, user_dict) in all_users:
        migrate_user(user_id, conf_path, db_path, force, verbose)
