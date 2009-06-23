#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# deleteuser - Remove a MiG user
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Remove MiG user from user database and file system"""

import os
import sys
import getopt

from shared.useradm import init_user_adm, delete_user, fill_distinguished_name, \
     fill_user

def usage(name='deleteuser.py'):
    """Usage help"""
    print """Usage:
%(name)s [OPTIONS] FULL_NAME [ORGANIZATION] [STATE] [COUNTRY] \
    [EMAIL]
or
%(name)s -u USER_ID
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force: continue on errors
   -h                  Show this help
   -u USER_ID          USER_ID is a colon separated list of ID fields matching a key in DB
   -v                  Be verbose
"""\
         % {'name': name}



# ## Main ###
if "__main__" == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    verbose = False
    force = False
    user_id = None
    user_dict = {}
    opt_args = 'c:d:fhu:v'
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
        elif opt == '-u':
            user_id = val
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

    if user_id and args:
        print 'Only one kind of user specification allowed at a time'
        usage()
        sys.exit(1)

    if args:
        user_dict['full_name'] = args[0]
        try:
            user_dict['organization'] = args[1]
            user_dict['state'] = args[2]
            user_dict['country'] = args[3]
            user_dict['email'] = args[4]
        except IndexError:

            # Ignore missing optional arguments

            pass
    elif user_id:
        parts = user_id.split(':')
        if len(parts) != 5:
            print 'Error in user id extraction: %s' % user_id
            usage()
            sys.exit(1)
        user_dict['full_name'] = parts[0]
        user_dict['organization'] = parts[1]
        user_dict['state'] = parts[2]
        user_dict['country'] = parts[3]
        user_dict['email'] = parts[4]
    else:
        print 'Please enter the details for the user to be removed:'
        user_dict['full_name'] = raw_input('Full Name: ').title()
        user_dict['organization'] = raw_input('Organization: ')
        user_dict['state'] = raw_input('State: ')
        user_dict['country'] = raw_input('2-letter Country Code: ')
        user_dict['email'] = raw_input('Email: ')

    if not user_dict.has_key('distinguished_name'):
        fill_distinguished_name(user_dict)

    fill_user(user_dict)

    # Now all user fields are set and we can begin adding the user

    print 'Removing DB entry and dirs for user: %s' % user_dict

    # Update user data base

    delete_user(user_dict, conf_path, db_path, force)
    
    print 'DB entry and dirs for %s were removed' % \
          user_dict['distinguished_name']
