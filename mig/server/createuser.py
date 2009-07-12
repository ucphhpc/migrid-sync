#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createuser - Create or renew a MiG user with all the necessary directories
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

"""Add or renew MiG user in user DB and in file system"""

import sys
import time
import os
import getopt
import base64
import pickle
from getpass import getpass

from shared.useradm import init_user_adm, create_user, \
    fill_distinguished_name, fill_user

cert_warn = \
    """
Please note that you *must* use either the -i CERT_DN option to createuser
or use importuser instead if you want to use other certificate DN formats
than the one expected by MiG (/C=.*/ST=.*/L=NA/O=.*/CN=.*/emailAddress=.*)
Otherwise those users will not be able to access their MiG interfaces!
"""


def usage(name='createuser.py'):
    """Usage help"""

    print """Create user in the MiG user database and file system.
%(cert_warn)s
Usage:
%(name)s [OPTIONS] FULL_NAME ORGANIZATION STATE COUNTRY \
    EMAIL COMMENT PASSWORD
or
%(name)s -u USER_FILE
or
%(name)s
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force: continue on errors
   -h                  Show this help
   -i CERT_DN          Use CERT_DN as user ID no matter what other fields suggest
   -u USER_FILE        Read user information from pickle file
   -v                  Be verbose
"""\
         % {'name': name, 'cert_warn': cert_warn}


# ## Main ###

if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    verbose = False
    force = False
    user_file = None
    user_id = None
    user_dict = {}
    opt_args = 'c:d:fhi:u:v'
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
        elif opt == '-u':
            user_file = val
        elif opt == '-v':
            verbose = True
        else:
            print 'Error: %s not supported!' % opt
            sys.exit(1)

    if conf_path and not os.path.isfile(conf_path):
        print 'Failed to read configuration file: %s' % conf_path
        sys.exit(1)

    if verbose:
        if conf_path:
            print 'using configuration in %s' % conf_path
        else:
            print 'using configuration from MIG_CONF (or default)'

    if user_file and args:
        print 'Only one kind of user specification allowed at a time'
        usage()
        sys.exit(1)

    if args:
        try:
            user_dict['full_name'] = args[0]
            user_dict['organization'] = args[1]
            user_dict['state'] = args[2]
            user_dict['country'] = args[3]
            user_dict['email'] = args[4]
            user_dict['comment'] = args[5]
            user_dict['password'] = args[6]
        except IndexError:
            print 'Error: too few arguments given (expected 7 got %d)'\
                 % len(args)
            usage()
            sys.exit(1)
    elif user_file:
        try:
            user_fd = open(user_file, 'rb')
            user_dict = pickle.load(user_fd)
        except Exception, err:
            print 'Error in user name extraction: %s' % err
            usage()
            sys.exit(1)
    else:
        print '''Entering interactive mode
%s''' % cert_warn
        print 'Please enter the details for the new user:'
        user_dict['full_name'] = raw_input('Full Name: ').title()
        user_dict['organization'] = raw_input('Organization: ')
        user_dict['state'] = raw_input('State: ')
        user_dict['country'] = raw_input('2-letter Country Code: ')
        user_dict['email'] = raw_input('Email: ')
        user_dict['comment'] = raw_input('Comment: ')
        user_dict['password'] = getpass('Password: ')

    # Encode password if not already encoded

    try:
        base64.b64decode(user_dict['password'])
    except TypeError:
        user_dict['password'] = base64.b64encode(user_dict['password'])

    # Default to one year of certificate validity (only used by CA scripts)

    if not user_dict.has_key('expire'):
        user_dict['expire'] = int(time.time() + (((2 * 365.25) * 24)
                                   * 60) * 60)
    if user_id:
        user_dict['distinguished_name'] = user_id
    elif not user_dict.has_key('distinguished_name'):
        fill_distinguished_name(user_dict)

    fill_user(user_dict)

    # Now all user fields are set and we can begin adding the user

    print 'using user dict: %s' % user_dict

    # Update user data base

    create_user(user_dict, conf_path, db_path, force)

    print 'DB entry and dirs for %s were created or updated'\
         % user_dict['distinguished_name']
    if user_file:
        print 'Cleaning up tmp file: %s' % user_file
        os.remove(user_file)
