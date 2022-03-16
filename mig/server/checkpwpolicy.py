#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# checkpwpolicy - Check user database for password compliance with site policy
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

"""Check passwords in user database for compliance with site password policy"""
from __future__ import print_function
from __future__ import absolute_import

import getopt
import pickle
import sys

from mig.shared.conf import get_configuration_object
from mig.shared.defaults import keyword_auto
from mig.shared.useradm import init_user_adm, search_users, default_search, \
    user_password_check, req_password_check


def usage(name='checkpwpolicy.py'):
    """Usage help"""

    print("""Check password policy compliance in user database.
Usage:
%(name)s [CHECK_OPTIONS]
Where CHECK_OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_PATH          Use DB_PATH as user data base file path
   -h                  Show this help
   -I CERT_DN          Check only for user with ID (distinguished name)
   -L                  Run check against any defined password legacy policy
   -p POLICY           Check against POLICY instead of configured value
   -u USER_FILE        Read user information from pickle file
   -v                  Verbose output
""" % {'name': name})


# ## Main ###

if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    policy = None
    verbose = False
    user_file = None
    legacy = False
    search_filter = default_search()
    opt_args = 'c:d:hI:Lp:u:v'
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
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-I':
            search_filter['distinguished_name'] = val
        elif opt == '-L':
            legacy = True
        elif opt == '-p':
            policy = val
        elif opt == '-u':
            user_file = val
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

    if policy and legacy:
        print('Error: specific policy cannot be used together with legacy')
        usage()
        sys.exit(1)

    uid = 'unknown'
    errors = []
    if user_file:
        (configuration, errors) = req_password_check(user_file, conf_path,
                                                     db_path, verbose, policy,
                                                     legacy)
    else:
        (configuration, hits) = search_users(search_filter, conf_path, db_path,
                                             verbose)
        if not hits:
            print("No matching users in user DB")
        else:
            # Load conf only once and reuse hits as a sparse user DB for speed
            conf_path, db_path = configuration, dict(hits)
            print("Password policy errors:")
            for (uid, user_dict) in hits:
                if verbose:
                    print("Checking %s" % uid)
                (_, err) = user_password_check(uid, conf_path,
                                               db_path, verbose,
                                               policy, legacy)
                errors += err
    if errors:
        print('\n'.join(errors))
    elif verbose:
        print("%s: OK" % uid)
