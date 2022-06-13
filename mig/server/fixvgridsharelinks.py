#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
#
# fixvgridsharelinks - fix missing vgrid sharelinks on adminvgrid pages
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

"""Fix any missing sharelinks on adminvgrid pages by going through all
sharelinks and making sure that all those pointing inside a vgrid share on
modern format are actually included in the vgrid sharelink pickle used to
render the list of sharelinks on the vgrid admin page.
In short some of these sharelinks may not have been caught as vgrid sharelinks
due to the bug fixed in rev4168+4169. Namely the detection of vgrid shares was
not correctly updated after the switch from the legacy vgrid_files_home to
the new vgrid_files_writable and vgrid_files_readonly so the vgrid sharelink
pickle didn't get updated for recent vgrids. 
"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import sys

from mig.shared.useradm import init_user_adm, fix_vgrid_sharelinks


def usage(name='fixvgridsharelinks.py'):
    """Usage help"""

    print("""Update vgrid sharelinks to fix any links not previously handled by
sharelink creation inside new-style vgrids.

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

    if len(args) > 0:
        usage()
        sys.exit(1)

    try:
        fix_vgrid_sharelinks(conf_path, db_path, verbose, force)
    except Exception as err:
        print(err)
        sys.exit(1)
