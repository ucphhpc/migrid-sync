1;4601;0c#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# edituser - Edit a MiG user
# Copyright (C) 2003-2013  The MiG Project lead by Brian Vinter
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

"""Edit MiG user in user database and file system"""

import getopt
import os
import sys

from shared.useradm import init_user_adm, edit_user


def usage(name='edituser.py'):
    """Usage help"""

    print """Edit existing user in MiG user database and file system.
Usage:
%(name)s [OPTIONS] -i USER_ID [FULL_NAME] [ORGANIZATION] [STATE] [COUNTRY] \
    [EMAIL] [COMMENT] [PASSWORD]
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force operations to continue past errors
   -h                  Show this help
   -i CERT_DN          CERT_DN of user to edit
   -o SHORT_ID         Change OpenID alias of user to SHORT_ID
   -R ROLES            Change user affiliation to ROLES
   -v                  Verbose output
"""\
         % {'name': name}


# ## Main ###

if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    force = False
    verbose = False
    user_id = None
    short_id = None
    role = None
    user_dict = {}
    opt_args = 'c:d:fhi:o:R:v'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError, err:
        print 'Error: ', err.msg
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
        elif opt == '-i':
            user_id = val
        elif opt == '-o':
            short_id = val
         elif opt == '-R':
             role = val
        elif opt == '-v':
            verbose = True
        else:
            print 'Error: %s not supported!' % opt

    if conf_path and not os.path.isfile(conf_path):
        print 'Failed to read configuration file: %s' % conf_path
        sys.exit(1)

    if verbose:
        if conf_path:
            print 'using configuration in %s' % conf_path
        else:
            print 'using configuration from MIG_CONF (or default)'

    if not user_id:
        print 'Error: Existing user ID is required'
        usage()
        sys.exit(1)

    if args:
        try:
            user_dict['full_name'] = args[0]
            user_dict['organization'] = args[1]
            user_dict['state'] = args[2]
            user_dict['country'] = args[3]
            user_dict['email'] = args[4]
        except IndexError:

            # Ignore missing optional arguments

            pass
    else:
        print 'Please enter the new details for %s:' % user_id
        print '[enter to skip field]'
        user_dict['full_name'] = raw_input('Full Name: ').title()
        user_dict['organization'] = raw_input('Organization: ')
        user_dict['state'] = raw_input('State: ')
        user_dict['country'] = raw_input('2-letter Country Code: ')
        user_dict['email'] = raw_input('Email: ')

    # Pass optional short_id as well
    if short_id:
        user_dict['short_id'] = short_id

    # Pass optional role as well
    if role:
        user_dict['role'] = role        

    # Remove empty value fields
    
    for (key, val) in user_dict.items():
        if not val:
            del user_dict[key]

    if verbose:
        print 'Update DB entry and dirs for %s: %s' % (user_id, user_dict)
    try:
        user = edit_user(user_id, user_dict, conf_path, db_path, force,
                         verbose)
    except Exception, err:
        print err
        sys.exit(1)
    print '%s\nchanged to\n%s\nin user database and file system' % \
          (user_id, user['distinguished_name'])
    print
    print 'Please revoke/reissue any related certificates!'
