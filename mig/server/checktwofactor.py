#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# checktwofactor - Check user enablement of twofactor auth
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

"""Check twofactor activation status for users"""
from __future__ import print_function
from __future__ import absolute_import

import getopt
import pickle
import sys

from mig.shared.defaults import keyword_auto
from mig.shared.useradm import init_user_adm, search_users, default_search, \
    user_twofactor_status


def usage(name='checktwofactor.py'):
    """Usage help"""

    print("""Check twofactor auth status for users.
Usage:
%(name)s [CHECK_OPTIONS]
Where CHECK_OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_PATH          Use DB_PATH as user data base file path
   -g                  Include GDP project users (usually same as owner)
   -h                  Show this help
   -I CERT_DN          Check only for user with ID (distinguished name)
   -v                  Verbose output
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    fields = keyword_auto
    include_project_users = False
    verbose = False
    user_file = None
    search_filter = default_search()
    opt_args = 'c:d:ghf:I:v'
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
            fields = val.split()
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-I':
            search_filter['distinguished_name'] = val
        elif opt == '-g':
            include_project_users = True
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

    uid = 'unknown'
    errors = []
    (configuration, hits) = search_users(search_filter, conf_path, db_path,
                                         verbose)
    if not hits:
        print("No matching users in user DB")
    else:
        # Reuse conf and hits as a sparse user DB for speed
        conf_path, db_path = configuration, dict(hits)
        print("2FA status:")
        for (uid, user_dict) in hits:
            if not include_project_users and \
                    uid.split('/')[-1].startswith('GDP='):
                continue
            if verbose:
                print("Checking %s" % uid)
            (_, err) = user_twofactor_status(uid, conf_path, db_path, fields,
                                             verbose)
            errors += err
    if errors:
        print('\n'.join(errors))
    elif verbose:
        print("%s: OK" % uid)
