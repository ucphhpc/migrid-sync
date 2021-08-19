#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# matchpeerusers - Match list of Peers in MiG user database
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

"""Given a CSV of potential Peers find all existing users in the user data base
and output the matches and mismatches.
"""

from __future__ import print_function
from __future__ import absolute_import

from past.builtins import basestring
import getopt
import re
import sys
import time

from mig.shared.accountreq import parse_peers
from mig.shared.base import fill_distinguished_name
from mig.shared.useradm import init_user_adm, search_users, default_search


def usage(name='matchpeerusers.py'):
    """Usage help"""

    print("""Match list of potential Peers in MiG user database.
Usage:
%(name)s [MATCH_OPTIONS] PEERS_PATH
Where MATCH_OPTIONS may be one or more of:
   -a EXPIRE_AFTER     Limit to users set to expire after EXPIRE_AFTER time
   -b EXPIRE_BEFORE    Limit to users set to expire before EXPIRE_BEFORE time
   -C COUNTRY          Search for country
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_PATH          Use DB_PATH as user data base file path
   -E EMAIL            Limit to users matching EMAIL
   -f FIELD            Show only FIELD value for matching users
   -F FULLNAME         Limit to users matching FULLNAME
   -h                  Show this help
   -I CERT_DN          Limit to users matching CERT_DN (distinguished name)
   -L LOCALMAILSUFFIX  Exclude users with LOCALMAILSUFFIX as local non-peers
   -O ORGANIZATION     Limit to users matching ORGANIZATION
   -r ROLE             Limit to users matching ROLE
   -S STATE            Limit to users matching STATE
   -v                  Verbose output

Where PEERS_PATH is the path of a CSV file with lines of peer users suitable
for Import Peers.

Each search value can be a string or a pattern with * and ? as wildcards.
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    verbose = False
    user_dict = {}
    opt_args = 'a:b:c:C:d:E:f:F:hI:L:O:r:S:v'
    search_filter = default_search()
    expire_before, expire_after = None, None
    only_fields = []
    local_mail_suffix = []
    peers_path = None
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
        elif opt == '-C':
            search_filter['country'] = val
        elif opt == '-E':
            search_filter['email'] = val
        elif opt == '-F':
            search_filter['full_name'] = val
        elif opt == '-L':
            local_mail_suffix.append(val)
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

    if args:
        peers_path = args[0]
    else:
        print("No peers path provided")
        usage()
        sys.exit(1)

    peers_content = ''
    try:
        with open(peers_path) as peers_fd:
            peers_content = peers_fd.readlines()
    except Exception as exc:
        print("Failed to load peers from %s: %s" % (peers_path, exc))
        peers_content = None

    regex_patterns = []
    for (key, val) in search_filter.items():
        if isinstance(val, basestring) and val.find('|') != -1:
            regex_patterns.append(key)

    (configuration, hits) = search_users(search_filter, conf_path, db_path,
                                         verbose, regex_match=regex_patterns)

    # Extract peer(s) from request
    (peers, err) = parse_peers(configuration, peers_content, 'csvform')
    if not err and not peers:
        print("No valid peers provided in %s" % peers_path)
        sys.exit(1)
    if err:
        print("Warning: invalid peers found:\n%s\n" % '\n'.join(err))

    #print("DEBUG: found peers: %s" % peers)
    #print("DEBUG: found %d total users" % len(hits))

    hit_ids = [i for (i, j) in hits]
    matches, overlaps, conflicts, misses, excludes = [], [], [], [], []
    # NOTE: we check all peers before any action
    for user in peers:
        fill_distinguished_name(user)
        peer_id = user['distinguished_name']
        peer_email = user['email']
        peer_name = user['full_name']
        peer_org = user['organization']
        if [True for i in local_mail_suffix if peer_email.endswith(i)]:
            excludes.append((peer_id, user))
        elif peer_id in hit_ids:
            matches.append((peer_id, user))
        elif [i for i in hit_ids if i.endswith("emailAddress="+peer_email)]:
            #print("DEBUG: adding %s to conflicts" % peer_id)
            overlap_tuple = [(i, j) for (i, j) in hits if
                             i.endswith("emailAddress="+peer_email)][0]
            overlaps.append(overlap_tuple)
            conflicts.append((peer_id, user))
        # TODO: detect more partial matches here and add to conflicts
        else:
            #print("DEBUG: adding %s to misses" % peer_id)
            misses.append((peer_id, user))

    field_header = ';'.join(only_fields)
    print("Matching peer users:")
    print(field_header)
    for (uid, user_dict) in matches:
        if only_fields:
            field_list = ["%s" % user_dict.get(i, '') for i in only_fields]
            print('%s' % ';'.join(field_list))
        else:
            print('%s : %s' % (uid, user_dict))
    print()
    print("Overlapping peer users:")
    print(field_header)
    for (uid, user_dict) in overlaps:
        if only_fields:
            field_list = ["%s" % user_dict.get(i, '') for i in only_fields]
            print('%s' % ';'.join(field_list))
        else:
            print('%s : %s' % (uid, user_dict))
    print()
    print("Conflicting peer users:")
    print(field_header)
    for (uid, user_dict) in conflicts:
        if only_fields:
            field_list = ["%s" % user_dict.get(i, '') for i in only_fields]
            print('%s' % ';'.join(field_list))
        else:
            print('%s : %s' % (uid, user_dict))
    print()
    print("Missing peer users:")
    print(field_header)
    for (uid, user_dict) in misses:
        if only_fields:
            field_list = ["%s" % user_dict.get(i, '') for i in only_fields]
            print('%s' % ';'.join(field_list))
        else:
            print('%s : %s' % (uid, user_dict))
    print()
    print("Local non-peer users:")
    print(field_header)
    for (uid, user_dict) in excludes:
        if only_fields:
            field_list = ["%s" % user_dict.get(i, '') for i in only_fields]
            print('%s' % ';'.join(field_list))
        else:
            print('%s : %s' % (uid, user_dict))
