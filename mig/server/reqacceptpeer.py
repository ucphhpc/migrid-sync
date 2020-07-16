#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqacceptpeer - Forward account request from peer to existing user(s)
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

"""Forward an external account request with reference to a local employee to
that employee. Used to request said employee to officially vouch for an
external user e.g. in relation to a course, project or permanent collaboration.
By default sends instructions on email to the registered notification address
or email from Distinguished Name field of employee user entry. If user
configured additional messaging protocols they can also be used.
"""

import getopt
import os
import sys

from shared.accountreq import peers_permit_allowed, manage_pending_peers
from shared.base import fill_distinguished_name, client_id_dir
from shared.conf import get_configuration_object
from shared.defaults import keyword_auto, gdp_distinguished_field, \
    pending_peers_filename
from shared.notification import notify_user
from shared.serial import load, dump
from shared.useradm import init_user_adm, search_users, default_search, \
    user_account_notify


def usage(name='reqacceptpeer.py'):
    """Usage help"""

    print """Request formal acceptance of external account request to user(s)
from user database and send instructions email.
Usage:
%(name)s [NOTIFY_OPTIONS] [FULL_NAME ORGANIZATION STATE COUNTRY EMAIL COMMENT]
Where NOTIFY_OPTIONS may be one or more of:
   -a                  Send instructions to email address of user from database
   -c CONF_FILE        Use CONF_FILE as server configuration
   -C                  Send a copy of notifications to configured site admins
   -d DB_PATH          Use DB_PATH as user data base file path
   -e EMAIL            Send instructions to custom email address
   -h                  Show this help
   -I CERT_DN          Forward peer request to user(s) with ID (distinguished name)
   -s PROTOCOL         Send instructions to notification protocol from settings
   -u USER_FILE        Read user request information from pickle file
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
    user_file = None
    user_id = None
    search_filter = default_search()
    # Default to all users
    search_filter['distinguished_name'] = '*'
    peer_dict = {}
    exit_code = 0
    opt_args = 'ac:Cd:e:hI:s:u:v'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError, err:
        print 'Error: ', err.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        print "parsing %s : %s" % (opt, val)
        if opt == '-a':
            raw_targets['email'] = raw_targets.get('email', [])
            raw_targets['email'].append(keyword_auto)
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
        elif opt == '-u':
            user_file = val
        elif opt == '-v':
            verbose = True
        else:
            print 'Error: %s not supported!' % opt
            usage()
            sys.exit(0)

    if conf_path and not os.path.isfile(conf_path):
        print 'Failed to read configuration file: %s' % conf_path
        sys.exit(1)

    if verbose:
        if conf_path:
            if verbose:
                print 'using configuration in %s' % conf_path
        else:
            if verbose:
                print 'using configuration from MIG_CONF (or default)'

    configuration = get_configuration_object(config_file=conf_path)
    logger = configuration.logger
    if user_file and args:
        print 'Error: Only one kind of user specification allowed at a time'
        usage()
        sys.exit(1)

    if args:
        try:
            peer_dict['full_name'] = args[0]
            peer_dict['organization'] = args[1]
            peer_dict['state'] = args[2]
            peer_dict['country'] = args[3]
            peer_dict['email'] = args[4]
            peer_dict['comment'] = args[5]
        except IndexError:
            print 'Error: too few arguments given (expected 6 got %d)'\
                % len(args)
            usage()
            sys.exit(1)
    elif user_file:
        try:
            peer_dict = load(user_file)
        except Exception, err:
            print 'Error in user name extraction: %s' % err
            usage()
            sys.exit(1)
    else:
        print 'No peer specified: please pass peer as args or with -u PATH'
        usage()
        sys.exit(1)

    fill_distinguished_name(peer_dict)
    peer_id = peer_dict['distinguished_name']

    if verbose:
        print 'Handling peer %s' % peer_id

    # Lookup users to request formal acceptance from
    (_, hits) = search_users(search_filter, conf_path, db_path, verbose)
    logger = configuration.logger
    gdp_prefix = "%s=" % gdp_distinguished_field
    for (user_id, user_dict) in hits:
        if verbose:
            print 'Check for %s' % user_id

        if configuration.site_enable_gdp and \
                user_id.split('/')[-1].startswith(gdp_prefix):
            if verbose:
                print "Skip GDP project account: %s" % user_id
            continue

        if not peers_permit_allowed(configuration, user_dict):
            if verbose:
                print "Skip account %s without vouching permission" % user_id
            continue

        if not manage_pending_peers(configuration, user_id, "add",
                                    [(peer_id, peer_dict)]):
            print "Failed to forward accept peer %s to %s" % (peer_id, user_id)
            continue

        print "Added peer request from %s to %s" % (peer_id, user_id)

        (_, _, full_name, addresses, errors) = user_account_notify(
            user_id, raw_targets, conf_path, db_path, verbose, admin_copy)
        if errors:
            print "Address lookup errors for %s :" % user_id
            print '\n'.join(errors)
            exit_code += 1
            continue

        notify_dict = {'JOB_ID': 'NOJOBID', 'USER_CERT': user_id, 'NOTIFY': []}
        for (proto, address_list) in addresses.items():
            for address in address_list:
                notify_dict['NOTIFY'].append('%s: %s' % (proto, address))
        # Don't actually send unless requested
        if not raw_targets and not admin_copy:
            print "No email targets for request accept peer %s from %s" % \
                  (peer_id, user_id)
            continue
        print "Send request accept peer message for '%s' to:\n%s" \
              % (peer_id, '\n'.join(notify_dict['NOTIFY']))
        notify_user(notify_dict, [peer_id, configuration.short_title,
                                  'peeraccount', peer_dict['comment'],
                                  peer_dict['email']],
                    'SENDREQUEST', logger, '', configuration)

    sys.exit(exit_code)
