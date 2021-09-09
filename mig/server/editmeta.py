#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# editmeta - Edit a MiG user metadata in user database
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

"""Edit MiG user metadata in user database - only non-ID fields"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import os
import sys

from mig.shared.useradm import init_user_adm, edit_user


def usage(name='editmeta.py'):
    """Usage help"""

    print("""Edit existing user (non-ID) metadata in MiG user database.
NOTE: it is necessary to use edituser.py to change any ID fields.
Usage:
%(name)s [OPTIONS] USER_ID FIELD VALUE
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force operations to continue past errors
   -r                  Remove provided FIELD(S) from USER_ID
   -h                  Show this help
   -v                  Verbose output
""" % {'name': name})


# ## Main ###

if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    force = False
    remove = False
    remove_fields = []
    verbose = False
    user_id = None
    user_dict = {}
    opt_args = 'c:d:frhv'
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
            force = True
        elif opt == '-r':
            remove = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)

    if conf_path and not os.path.isfile(conf_path):
        print('Failed to read configuration file: %s' % conf_path)
        sys.exit(1)

    if verbose:
        if conf_path:
            print('using configuration in %s' % conf_path)
        else:
            print('using configuration from MIG_CONF (or default)')

    if remove and len(args) > 1:
        user_id = user_dict['distinguished_name'] = args[0]
        remove_fields += args[1:]
    elif len(args) == 3:
        user_id = user_dict['distinguished_name'] = args[0]
        user_dict[args[1]] = args[2]
    else:
        usage()
        sys.exit(1)

    if verbose:
        print('Update DB entry for %s: %s' % (user_id, user_dict))
    try:
        user = edit_user(user_id, user_dict, remove_fields, conf_path, db_path,
                         force, verbose, True)
    except Exception as err:
        print(err)
        sys.exit(1)
    print('%s\nchanged to\n%s\nin user database' % (user_id, user))
