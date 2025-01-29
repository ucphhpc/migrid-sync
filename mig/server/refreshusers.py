#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# refreshusers - a simple helper to refresh stale user files to current user ID
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Refresh one or more accounts so that files and dirs fit current user ID, in
particular replace any stale .htaccess files no longer in sync regarding
assigned IDs and therefore causing auth error upon fileman open, etc.
"""

from __future__ import print_function
from __future__ import absolute_import

import datetime
import getopt
import sys
import time

from mig.shared.defaults import gdp_distinguished_field
from mig.shared.useradm import init_user_adm, search_users, default_search, \
    assure_current_htaccess


def usage(name='refreshusers.py'):
    """Usage help"""

    print("""Refresh MiG user user files and dirs based on user ID in MiG user
database.

Usage:
%(name)s [OPTIONS]
Where OPTIONS may be one or more of:
   -A EXPIRE_AFTER     Limit to users expiring after EXPIRE_AFTER (epoch)
   -B EXPIRE_BEFORE    Limit to users expiring before EXPIRE_BEFORE (epoch)
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force operations to continue past errors
   -h                  Show this help
   -I CERT_DN          Filter to user(s) with ID (distinguished name)
   -s SHORT_ID         Filter to user(s) with given short ID field
   -v                  Verbose output
"""
          % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    force = False
    verbose = False
    exit_code = 0
    now = int(time.time())
    search_filter = default_search()
    # Default to all users with expire range between now and in 30 days
    search_filter['distinguished_name'] = '*'
    search_filter['short_id'] = '*'
    search_filter['expire_after'] = now
    search_filter['expire_before'] = int(time.time() + 365 * 24 * 3600)
    # Default to only external openid accounts
    services = ['extoid']
    opt_args = 'A:B:c:d:fhI:s:v'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-A':
            after = now
            if val.startswith('+'):
                after += int(val[1:])
            elif val.startswith('-'):
                after -= int(val[1:])
            else:
                after = int(val)
            search_filter['expire_after'] = after
        elif opt == '-B':
            before = now
            if val.startswith('+'):
                before += int(val[1:])
            elif val.startswith('-'):
                before -= int(val[1:])
            else:
                before = int(val)
            search_filter['expire_before'] = before
        elif opt == '-c':
            conf_path = val
        elif opt == '-d':
            db_path = val
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-I':
            search_filter['distinguished_name'] = val
        elif opt == '-s':
            search_filter['short_id'] = val
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            sys.exit(1)

    if args:
        print('Error: Non-option arguments are not supported - missing quotes?')
        usage()
        sys.exit(1)

    (configuration, hits) = search_users(search_filter, conf_path, db_path,
                                         verbose)
    logger = configuration.logger
    gdp_prefix = "%s=" % gdp_distinguished_field
    # NOTE: we already filtered expired accounts here
    search_dn = search_filter['distinguished_name']
    before = datetime.datetime.fromtimestamp(search_filter['expire_before'])
    after = datetime.datetime.fromtimestamp(search_filter['expire_after'])
    if verbose:
        if hits:
            print("Check %d account(s) expiring between %s and %s for ID %r" %
                  (len(hits), after, before, search_dn))
        else:
            print("No accounts expire between %s and %s for ID %r" %
                  (after, before, search_dn))

    for (user_id, user_dict) in hits:
        affected = []
        if verbose:
            print('Check refresh needed for %r' % user_id)

        # TODO: what to do with gdp accounts here?
        if configuration.site_enable_gdp and \
                user_id.split('/')[-1].startswith(gdp_prefix):
            if verbose:
                print("Skip GDP project account: %s" % user_id)
            continue

        # Don't warn about already disabled or suspended accounts
        account_state = user_dict.get('status', 'active')
        if not account_state in ('active', 'temporal'):
            if verbose:
                print('Skip handling of already %s user %r' % (account_state,
                                                               user_id))
            continue

        known_auth = user_dict.get('auth', [])
        if not known_auth:
            if user_dict.get('main_id', ''):
                known_auth.append("extoidc")
            elif user_dict.get('openid_names', []):
                if user_dict.get('password_hash', ''):
                    known_auth.append("migoid")
                else:
                    known_auth.append("extoid")
            elif user_dict.get('password', ''):
                known_auth.append("migcert")
            else:
                if verbose:
                    print('Skip handling of user %r without auth info' %
                          user_id)
                continue

        if not ('extoid' in known_auth or 'extoidc' in known_auth):
            if verbose:
                print('Skip handling of user %r without extoid(c) auth' %
                      user_id)
            continue

        if verbose:
            print('Assure current htaccess for %r account' % user_id)
        if not assure_current_htaccess(configuration, user_id, user_dict,
                                       force, verbose):
            exit_code += 1

    sys.exit(exit_code)
