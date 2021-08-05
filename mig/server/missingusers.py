#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# missingusers - Search for missing users in MiG user database
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

"""Find all users in user_home and compare with data base"""
from __future__ import print_function
from __future__ import absolute_import

import fnmatch
import os
import sys
import getopt

from mig.shared.base import client_dir_id, distinguished_name_to_user
from mig.shared.useradm import init_user_adm, search_users, default_search


def usage(name='missingusers.py'):
    """Usage help"""

    print("""Find missing users in MiG user database.
Usage:
%(name)s [SEARCH_OPTIONS]
Where SEARCH_OPTIONS may be one or more of:
   -C COUNTRY          Search for country
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_PATH          Use DB_PATH as user data base file path
   -E EMAIL            Search for email
   -F FULLNAME         Search for full name
   -h                  Show this help
   -I CERT_DN          Search for user ID (distinguished name)
   -n                  Show only name
   -O ORGANIZATION     Search for organization
   -r ROLE             Match on role pattern
   -S STATE            Search for state
   -v                  Verbose output

Each search value can be a string or a pattern with * and ? as wildcards.
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    verbose = False
    user_dict = {}
    opt_args = 'c:C:d:E:F:hI:nO:r:S:v'
    search_filter = default_search()
    name_only = False
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            conf_path = val
        elif opt == '-d':
            db_path = val
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-I':
            search_filter['distinguished_name'] = val
        elif opt == '-n':
            name_only = True
        elif opt == '-C':
            search_filter['country'] = val
        elif opt == '-E':
            search_filter['email'] = val
        elif opt == '-F':
            search_filter['full_name'] = val
        elif opt == '-O':
            search_filter['organization'] = val
        elif opt == '-r':
            search_filter['role'] = val
        elif opt == '-S':
            search_filter['state'] = val
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            usage()
            sys.exit(0)

    fs_users = {}
    fs_hits = []
    from mig.shared.conf import get_configuration_object
    configuration = get_configuration_object()
    for user_dir in os.listdir(configuration.user_home):
        home_path = os.path.join(configuration.user_home, user_dir)
        if not os.path.isdir(home_path) or user_dir.find('+') == -1:
            continue
        user_id = client_dir_id(user_dir)
        user_dict = distinguished_name_to_user(user_id)
        fs_users[user_id] = user_dict
        match = True
        for (key, val) in search_filter.items():
            if not fnmatch.fnmatch("%s" % user_dict.get(key, ''), val):
                match = False
                break
        if not match:
            continue
        fs_hits.append((user_id, user_dict))
    fs_hits_dict = dict(fs_hits)

    (configuration, db_hits) = search_users(search_filter, conf_path, db_path,
                                            verbose)
    db_hits_dict = dict(db_hits)

    print("Missing users:")
    for (user_id, user_dict) in fs_hits:
        if db_hits_dict.get(user_id, None):
            continue
        if name_only:
            print('%s' % user_dict['full_name'])
        else:
            print('%s : %s' % (user_id, user_dict))
