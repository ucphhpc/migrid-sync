#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# searchusers - [insert a few words of module description on this line]
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

"""Find all users with given data base field(s)"""

import os
import sys
import getopt
import pickle
import fnmatch

def usage(name='searchusers.py'):
    print """Usage:
%(name)s [SEARCH_OPTIONS]
Where SEARCH_OPTIONS may be one or more of:
   -c COUNTRY          Search for country
   -d DB_PATH          Use DB_PATH as user data base file path
   -e EMAIL            Search for email
   -f FULLNAME         Search for full name
   -n                  Show only name
   -h                  Show this help
   -o ORGANIZATION     Search for organization
   -s STATE            Search for state

Each search value can be a string or a pattern with * and ? as wildcards.
"""\
         % {'name': name}


# ## Main ###

args = sys.argv[1:]
app_dir = os.path.dirname(sys.argv[0])
db_file = app_dir + os.sep + 'MiG-users.db'
user_db = {}
user_dict = {}
opt_args = 'c:d:e:f:hno:s:'
search_filter = {
    'country': '*',
    'email': '*',
    'full_name': '*',
    'organization': '*',
    'state': '*',
    }
name_only = False
try:
    (opts, args) = getopt.getopt(args, opt_args)
except getopt.GetoptError, err:
    print 'Error: ', err.msg
    usage()
    sys.exit(1)

for (opt, val) in opts:
    if opt == '-c':
        search_filter['country'] = val
    elif opt == '-d':
        db_file = val
    elif opt == '-e':
        search_filter['email'] = val
    elif opt == '-f':
        search_filter['full_name'] = val
    elif opt == '-h':
        usage()
        sys.exit(0)
    elif opt == '-n':
        name_only = True
    elif opt == '-o':
        search_filter['organization'] = val
    elif opt == '-s':
        search_filter['state'] = val
    else:
        print 'Error: %s not supported!' % opt
        usage()
        sys.exit(0)

try:
    db_fd = open(db_file, 'rb')
    user_db = pickle.load(db_fd)
    db_fd.close()
    print 'Loaded existing user DB from: %s' % db_file
except Exception, err:
    print 'Failed to load user DB: %s' % err
    sys.exit(1)

for (uid, user_dict) in user_db.items():
    match = True
    for (key, val) in search_filter.items():
        if not fnmatch.fnmatch(str(user_dict[key]), val):
            match = False
            break
    if not match:
        continue
    if name_only:
        print user_dict['full_name']
    else:
        print '%s : %s' % (uid, user_dict)
