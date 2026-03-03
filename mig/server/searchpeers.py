#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# searchpeers - Search in MiG user peers
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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

"""Find all peers of a user matching given account field(s)"""

from __future__ import print_function
from __future__ import absolute_import

from past.builtins import basestring
import getopt
import sys

from mig.shared.useradm import init_user_adm, search_peers, default_search


def usage(name='searchpeers.py'):
    """Usage help"""

    print("""Search in MiG user peers.
Usage:
%(name)s [SEARCH_OPTIONS] PEER_CONTACT_ID
Where SEARCH_OPTIONS may be one or more of:
   -C COUNTRY          Search for country
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_PATH          Use DB_PATH as user data base file path
   -E EMAIL            Search for email
   -F FULLNAME         Search for full name
   -f FIELD            Show only FIELD value for matching users
   -h                  Show this help
   -I CERT_DN          Search for user ID (distinguished name)
   -n                  Show only name (equals -f full_name)
   -O ORGANIZATION     Search for organization
   -S STATE            Search for state
   -v                  Verbose output

Each search value can be a string or a pattern with * and ? as wildcards.
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    verbose = False
    user_dict = {}
    opt_args = 'a:b:c:C:d:E:f:F:hI:nO:S:v'
    search_filter = default_search()
    only_fields = []
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
        elif opt == '-S':
            search_filter['state'] = val
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            usage()
            sys.exit(0)

    if not args:
        print('Error: peer contact ID is required!')
        usage()
        sys.exit(1)

    peers_contact_id = sys.argv[-1]

    regex_patterns = []
    for (key, val) in search_filter.items():
        if isinstance(val, basestring) and val.find('|') != -1:
            regex_patterns.append(key)

    (configuration, hits) = search_peers(peers_contact_id, search_filter,
                                         conf_path, db_path, verbose,
                                         regex_match=regex_patterns)
    print("Matching peers:")
    for (uid, user_dict) in hits:
        if only_fields:
            field_list = ["%s" % user_dict.get(i, '') for i in only_fields]
            print('%s' % ' : '.join(field_list))
        else:
            print('%s : %s' % (uid, user_dict))
