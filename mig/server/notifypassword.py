#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# notifypassword - Send forgotten password from user database to user
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

"""Send forgotten user password from user database to user. Allows password
reminder to saved notification address or email from Distinguished Name field
of user entry.
"""
from __future__ import print_function
from __future__ import absolute_import

import sys
import getopt

from mig.shared.defaults import keyword_auto
from mig.shared.notification import notify_user
from mig.shared.useradm import init_user_adm, user_password_reminder


def usage(name='notifypassword.py'):
    """Usage help"""

    print("""Send forgotten password to user from user database.
Usage:
%(name)s [NOTIFY_OPTIONS]
Where NOTIFY_OPTIONS may be one or more of:
   -a                  Send reminder to email address from database
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_PATH          Use DB_PATH as user data base file path
   -e EMAIL            Send reminder to custom email address
   -h                  Show this help
   -I CERT_DN          Send reminder for user with ID (distinguished name)
   -s PROTOCOL         Send reminder to notification protocol from settings
   -v                  Verbose output

One or more destinations may be set by combining multiple -e, -s and -a
options.
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    verbose = False
    raw_targets = {}
    user_id = None
    opt_args = 'ac:d:e:hI:s:v'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-a':
            raw_targets['email'] = raw_targets.get('email', [])
            raw_targets['email'].append(keyword_auto)
        elif opt == '-c':
            conf_path = val
        elif opt == '-d':
            db_path = val
        elif opt == '-e':
            raw_targets['email'] = raw_targets.get('email', [])
            raw_targets['email'].append(val)
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-I':
            user_id = val
        elif opt == '-s':
            val = val.lower()
            raw_targets[val] = raw_targets.get(val, [])
            raw_targets[val].append('SETTINGS')
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

    if not user_id:
        print("No user_id provided!")
        sys.exit(1)

    (configuration, password, addresses, errors) = \
        user_password_reminder(user_id, raw_targets, conf_path,
                               db_path, verbose)

    if errors:
        print("Address lookup errors:")
        print('\n'.join(errors))

    if not addresses:
        print("Error: found no suitable addresses")
        sys.exit(1)
    if not password:
        print("Error: found no password for user")
        sys.exit(1)
    logger = configuration.logger
    notify_dict = {'JOB_ID': 'NOJOBID', 'USER_CERT': user_id, 'NOTIFY': []}
    for (proto, address_list) in addresses.items():
        for address in address_list:
            notify_dict['NOTIFY'].append('%s: %s' % (proto, address))
    print("Sending password reminder(s) for '%s' to:\n%s" % \
          (user_id, '\n'.join(notify_dict['NOTIFY'])))
    notify_user(notify_dict, [user_id, password], 'PASSWORDREMINDER', logger,
                '', configuration)
