#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
#
# fixusersharelinks - update sharelinks for legacy edituser victims
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Fix any leftover sharelinks not previously handled by edituser by relinking
them to the current user home and updating the pickled owner info.
"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import sys

from mig.shared.useradm import init_user_adm, fix_user_sharelinks


def usage(name='fixusersharelinks.py'):
    """Usage help"""

    print("""Update user sharelinks to fix any links not previously handled by
edituser.

Usage:
%(name)s [OPTIONS] OLD_ID NEW_ID
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force operations to continue past errors
   -h                  Show this help
   -v                  Verbose output
"""
          % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    force = False
    verbose = False
    opt_args = 'c:d:fhv'
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
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            sys.exit(1)

    if len(args) != 2:
        usage()
        sys.exit(1)

    old_id, new_id = args[0], args[1]
    try:
        fix_user_sharelinks(old_id, new_id, conf_path, db_path, verbose)
    except Exception as err:
        print(err)
        sys.exit(1)
