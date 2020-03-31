#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# notifyexpire - Send account expire warning email to user(s)
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""Lookup account expire for one or more users and send a warning email with
instructions for renewing if expire is imminent. Used to remind users signed up
with internal OpenID access where we don't have another logical hook to send
based on e.g. certificate expiration.
By default sends the information on email to the registered notification
address or email from Distinguished Name field of user entry. If user
configured additional messaging protocols they can also be used.
"""

import datetime
import getopt
import sys
import time

from shared.defaults import keyword_auto, gdp_distinguished_field
from shared.notification import notify_user
from shared.useradm import init_user_adm, search_users, default_search, \
    user_migoid_notify


def usage(name='notifyexpire.py'):
    """Usage help"""

    print """Check internal OpenID account expire for user(s) from user
database and send warning email if imminent.
Usage:
%(name)s [NOTIFY_OPTIONS]
Where NOTIFY_OPTIONS may be one or more of:
   -a                  Send warning to email address of user from database
   -A EXPIRE_AFTER     Limit to users expiring after EXPIRE_AFTER (epoch)
   -B EXPIRE_BEFORE    Limit to users expiring before EXPIRE_BEFORE (epoch)
   -c CONF_FILE        Use CONF_FILE as server configuration
   -C                  Send a copy of notifications to configured site admins
   -d DB_PATH          Use DB_PATH as user data base file path
   -e EMAIL            Send warning to custom email address
   -h                  Show this help
   -I CERT_DN          Send warning for user(s) with ID (distinguished name)
   -s PROTOCOL         Send warning to notification protocol from settings
   -v                  Verbose output

One or more destinations may be set by combining multiple -e, -s and -a
options.
""" % {'name': name}


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    verbose = False
    admin_copy = False
    raw_targets = {}
    user_id = None
    search_filter = default_search()
    # Default to all users with expire range between now and in 30 days
    search_filter['distinguished_name'] = '*'
    search_filter['expire_after'] = int(time.time())
    search_filter['expire_before'] = int(time.time() + 30 * 24 * 3600)
    now = int(time.time())
    exit_code = 0
    opt_args = 'aA:B:c:Cd:e:hI:s:v'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError, err:
        print 'Error: ', err.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-a':
            raw_targets['email'] = raw_targets.get('email', [])
            raw_targets['email'].append(keyword_auto)
        elif opt == '-A':
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
        elif opt == '-C':
            admin_copy = True
        elif opt == '-d':
            db_path = val
        elif opt == '-e':
            raw_targets['email'] = raw_targets.get('email', [])
            raw_targets['email'].append(val)
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-I':
            search_filter['distinguished_name'] = val
        elif opt == '-s':
            val = val.lower()
            raw_targets[val] = raw_targets.get(val, [])
            raw_targets[val].append('SETTINGS')
        elif opt == '-v':
            verbose = True
        else:
            print 'Error: %s not supported!' % opt
            usage()
            sys.exit(0)

    if args:
        print 'Error: Non-option arguments are not supported - missing quotes?'
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
            print "Check %d expire(s) between %s and %s for user ID '%s'" % \
                  (len(hits), after, before, search_dn)
        else:
            print "No expires between %s and %s for user ID '%s'" % \
                  (after, before, search_dn)
    for (user_id, user_dict) in hits:
        if verbose:
            print 'Check for %s' % user_id

        if configuration.site_enable_gdp and \
                user_id.split('/')[-1].startswith(gdp_prefix):
            if verbose:
                print "Skip GDP project account: %s" % user_id
            continue

        if not user_dict.get('password', '') and \
                not user_dict.get('password_hash', ''):
            if verbose:
                print "Skip account %s without local password" % user_id
            continue

        (_, username, full_name, addresses, errors) = user_migoid_notify(
            user_id, raw_targets, conf_path, db_path, verbose, admin_copy)
        if errors:
            print "Address lookup errors for %s :" % user_id
            print '\n'.join(errors)
            exit_code += 1
            continue
        if not username:
            print "Error: found no username for %s" % user_id
            exit_code += 1
            continue
        expire = datetime.datetime.fromtimestamp(user_dict['expire'])
        print "Account %s expires on %s" % (user_id, expire)
        notify_dict = {'JOB_ID': 'NOJOBID', 'USER_CERT': user_id, 'NOTIFY': []}
        for (proto, address_list) in addresses.items():
            for address in address_list:
                notify_dict['NOTIFY'].append('%s: %s' % (proto, address))
        # Don't actually send unless requested
        if not raw_targets and not admin_copy:
            continue
        print "Send internal OpenID account expire warning for '%s' to:\n%s" \
              % (user_id, '\n'.join(notify_dict['NOTIFY']))
        notify_user(notify_dict, [user_id, username, full_name, user_dict],
                    'ACCOUNTEXPIRE', logger, '', configuration)

    sys.exit(exit_code)
