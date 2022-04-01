#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# notifymigoid - Send internal openid account create/renew email to user
# Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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

"""Send a short introduction to user upon internal OpenID account creation or
renewal. Used to greet users signing up or renewing with internal OpenID
service where we don't have another hook to send e.g. certificate and where
autocreate is not in place.
By default sends the information on email to the registered notification
address or email from Distinguished Name field of user entry. If user
configured additional messaging protocols they can also be used.
"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import sys

from mig.shared.defaults import keyword_auto
from mig.shared.notification import notify_user
from mig.shared.useradm import init_user_adm, user_account_notify


def usage(name='notifymigoid.py'):
    """Usage help"""

    print("""Send internal OpenID account create/renew intro to user from user
database.
Usage:
%(name)s [NOTIFY_OPTIONS]
Where NOTIFY_OPTIONS may be one or more of:
   -a                  Send intro to email address from database
   -c CONF_FILE        Use CONF_FILE as server configuration
   -C                  Send a copy of notifications to configured site admins
   -d DB_PATH          Use DB_PATH as user data base file path
   -e EMAIL            Send intro to custom email address
   -h                  Show this help
   -I CERT_DN          Send intro for user with ID (distinguished name)
   -s PROTOCOL         Send intro to notification protocol from settings
   -v                  Verbose output

One or more destinations may be set by combining multiple -e, -s and -a
options.
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    verbose = False
    admin_copy = False
    raw_targets = {}
    user_id = None
    opt_args = 'ac:Cd:e:hI:s:v'
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
            sys.exit(0)

    if args:
        print('Error: Non-option arguments are not supported - missing quotes?')
        usage()
        sys.exit(1)

    if not user_id:
        print("No user_id provided!")
        sys.exit(1)

    (configuration, username, full_name, addresses, errors) = \
        user_account_notify(user_id, raw_targets, conf_path, db_path, verbose,
                            admin_copy)

    if errors:
        print("Address lookup errors:")
        print('\n'.join(errors))

    if not addresses:
        print("Error: found no suitable addresses")
        sys.exit(1)
    if not username:
        print("Error: found no username")
        sys.exit(1)
    logger = configuration.logger
    notify_dict = {'JOB_ID': 'NOJOBID', 'USER_CERT': user_id, 'NOTIFY': []}
    for (proto, address_list) in addresses.items():
        for address in address_list:
            notify_dict['NOTIFY'].append('%s: %s' % (proto, address))
    print("Sending internal OpenID account intro for '%s' to:\n%s" %
          (user_id, '\n'.join(notify_dict['NOTIFY'])))
    notify_user(notify_dict, [user_id, username, full_name], 'ACCOUNTINTRO',
                logger, '', configuration)
