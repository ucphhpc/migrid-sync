#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rejectuser - Reject a MiG user request with an explanation on email
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

"""Reject a MiG user request and send email with reason"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import os
import getopt

from mig.shared.base import fill_distinguished_name, fill_user
from mig.shared.defaults import keyword_auto, valid_auth_types
from mig.shared.notification import notify_user
from mig.shared.serial import load
from mig.shared.useradm import init_user_adm, user_request_reject


def usage(name='rejectuser.py'):
    """Usage help"""

    print("""Reject MiG user account request and inform by email.
Usage:
%(name)s [OPTIONS] -u USER_FILE
Where OPTIONS may be one or more of:
   -a AUTH_TYPE        redirect user to retry on AUTH_TYPE sign up form
   -c CONF_FILE        Use CONF_FILE as server configuration
   -C                  Send a copy of notifications to configured site admins
   -d DB_PATH          Use DB_PATH as user data base file path
   -e EMAIL            Send reject message to custom email address
   -f                  Force operations to continue past errors
   -h                  Show this help
   -i CERT_DN          Use CERT_DN as user ID despite what other fields suggest
   -r REASON           Display REASON for reject in email to help user retry
   -u USER_FILE        Read user information from pickle file
   -v                  Verbose output
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    auth_type = 'oid'
    conf_path = None
    force = False
    reason = "invalid or missing mandatory info"
    verbose = False
    admin_copy = False
    raw_targets = {}
    # Default to mail in request
    raw_targets['email'] = raw_targets.get('email', [])
    raw_targets['email'].append(keyword_auto)
    user_file = None
    user_id = None
    user_dict = {}
    override_fields = {}
    opt_args = 'a:c:Cd:e:fhi:r:u:v'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-a':
            auth_type = val
        elif opt == '-c':
            conf_path = val
        elif opt == '-C':
            admin_copy = True
        elif opt == '-d':
            db_path = val
        elif opt == '-e':
            raw_targets['email'] = raw_targets.get('email', [])
            raw_targets['email'].append(val)
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-i':
            user_id = val
        elif opt == '-r':
            reason = val
        elif opt == '-u':
            user_file = val
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            usage()
            sys.exit(1)

    if args:
        print('Error: Non-option arguments are not supported - missing quotes?')
        usage()
        sys.exit(1)

    if not user_file:
        print("Required user request file not provided!")
        sys.exit(1)

    if auth_type not in valid_auth_types:
        print('Error: invalid account auth type %r requested (allowed: %s)' %
              (auth_type, ', '.join(valid_auth_types)))
        usage()
        sys.exit(1)

    try:
        user_dict = load(user_file)
    except Exception as err:
        print('Error in user name extraction: %s' % err)
        usage()
        sys.exit(1)

    if user_id:
        user_dict['distinguished_name'] = user_id
    elif 'distinguished_name' not in user_dict:
        fill_distinguished_name(user_dict)

    fill_user(user_dict)
    user_id = user_dict['distinguished_name']

    # Now all user fields are set and we can reject and warn the user

    (configuration, addresses, errors) = \
        user_request_reject(user_id, raw_targets, conf_path,
                            db_path, verbose, admin_copy)

    if errors:
        print("Address lookup errors:")
        print('\n'.join(errors))

    if not addresses:
        print("Error: found no suitable addresses")
        sys.exit(1)
    logger = configuration.logger
    notify_dict = {'JOB_ID': 'NOJOBID', 'USER_CERT': user_id, 'NOTIFY': []}
    for (proto, address_list) in addresses.items():
        for address in address_list:
            notify_dict['NOTIFY'].append('%s: %s' % (proto, address))
    print("Sending reject account request for '%s' to:\n%s" %
          (user_id, '\n'.join(notify_dict['NOTIFY'])))
    notify_user(notify_dict, [user_id, user_dict, auth_type, reason],
                'ACCOUNTREQUESTREJECT', logger, '', configuration)

    if verbose:
        print('Cleaning up tmp file: %s' % user_file)
    os.remove(user_file)
