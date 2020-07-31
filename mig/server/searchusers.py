#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# searchusers - Search in MiG user database
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Find all users with given data base field(s)"""
from __future__ import print_function
from __future__ import absolute_import

import getopt
import sys
import time

from mig.shared.defaults import cert_valid_days, oid_valid_days
from mig.shared.useradm import init_user_adm, search_users, default_search


def usage(name='searchusers.py'):
    """Usage help"""

    print("""Search in MiG user database.
Usage:
%(name)s [SEARCH_OPTIONS]
Where SEARCH_OPTIONS may be one or more of:
   -a EXPIRE_AFTER     Limit to users set to expire after EXPIRE_AFTER time
   -b EXPIRE_BEFORE    Limit to users set to expire before EXPIRE_BEFORE time
   -C COUNTRY          Search for country
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_PATH          Use DB_PATH as user data base file path
   -f FIELD            Show only FIELD value for matching users
   -E EMAIL            Search for email
   -F FULLNAME         Search for full name
   -h                  Show this help
   -I CERT_DN          Search for user ID (distinguished name)
   -n                  Show only name (equals -f full_name)
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
    opt_args = 'a:b:c:C:d:E:f:F:hI:nO:r:S:v'
    search_filter = default_search()
    expire_before, expire_after = None, None
    only_fields = []
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-a':
            search_filter['expire_after'] = int(val)
        elif opt == '-b':
            search_filter['expire_before'] = int(val)
        elif opt == '-c':
            conf_path = val
        elif opt == '-d':
            db_path = val
        elif opt == '-f':
            only_fields.append(val)
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-I':
            search_filter['distinguished_name'] = val
        elif opt == '-n':
            only_fields.append('full_name')
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

    (configuration, hits) = search_users(search_filter, conf_path, db_path,
                                         verbose)
    print("Matching users:")
    for (uid, user_dict) in hits:
        if only_fields:
            field_list = [str(user_dict.get(i, '')) for i in only_fields]
            print('%s' % ' : '.join(field_list))
        else:
            print('%s : %s' % (uid, user_dict))
