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

from shared.configuration import Configuration


def usage(name='createuser.py'):
    print """Usage:
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
   -u USER_FILE        Read user information from pickle file
   -v                  Be verbose
"""\
         % {'name': name}


# ## Main ###

args = sys.argv[1:]
app_dir = os.path.dirname(sys.argv[0])
if not app_dir:
    app_dir = '.'
conf_path = os.path.join(app_dir, 'MiGserver.conf')
db_path = os.path.join(app_dir, 'MiG-users.db')
verbose = False
renew = False
force = False
user_file = None
user_db = {}
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
        user_file = val
    elif opt == '-v':
        verbose = True
    else:
        print 'Error: %s not supported!' % opt

if not os.path.isfile(conf_path):
    print 'Failed to read configuration file: %s' % conf_path
    sys.exit(1)

if verbose:
    print 'using configuration in %s' % conf_path

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
    print 'Please enter the details for the new user:'
    user_dict['full_name'] = raw_input('Full Name: ').title()
    user_dict['organization'] = raw_input('Organization: ')
    user_dict['state'] = raw_input('State: ')
    user_dict['country'] = raw_input('2-letter Country Code: ')
    user_dict['email'] = raw_input('Email: ')
    user_dict['comment'] = raw_input('Comment: ')
    user_dict['password'] = base64.b64encode(getpass('Password: '))

# Default to one year of certificate validity (only used by CA scripts)
if not user_dict.has_key('expire'):
    user_dict['expire'] = int(time.time() + (((2 * 365.25) * 24) * 60) * 60)

# Now all user fields are set and we can begin adding the user

print 'using user dict: %s' % user_dict
user_id = '%(full_name)s:%(organization)s:' % user_dict
user_id += '%(state)s:%(country)s:%(email)s' % user_dict
full_name = user_dict['full_name']
full_name_without_spaces = full_name.replace(' ', '_')

if not full_name:
    print 'Missing Full Name!'
    sys.exit(1)

configuration = Configuration(conf_path)
print 'User name without spaces: %s\n' % full_name_without_spaces

# Update user data base

if os.path.exists(db_path):
    try:
        db_fd = open(db_path, 'rb')
        user_db = pickle.load(db_fd)
        db_fd.close()
        print 'Loaded existing user DB from: %s' % db_path
    except Exception, err:
        print 'Failed to load user DB!'
        if not force:
            sys.exit(1)

    if user_db.has_key(user_id):
        renew_answer = raw_input('User DB entry already exists - renew? [Y/n] ')
        renew = (not renew_answer.lower().startswith('n'))
        if renew:
            print 'Renewing existing user'
        elif not force:
            print 'Nothing more to do for existing user'
            sys.exit(1)

try:
    user_db[user_id] = user_dict
    db_fd = open(db_path, 'wb')
    pickle.dump(user_db, db_fd)
    db_fd.close()
    print 'User %s was successfully added/updated in user DB!' % full_name
except Exception, err:
    print 'Error: Failed to add %s to user DB: %s' % (full_name, err)
    if not force:
        sys.exit(1)

home_dir = os.path.join(configuration.user_home, full_name_without_spaces)
mrsl_dir = os.path.join(configuration.mrsl_files_dir, full_name_without_spaces)
pending_dir = os.path.join(configuration.resource_pending, full_name_without_spaces)
htaccess_path = os.path.join(home_dir, '.htaccess')
if not renew:
    print 'Creating dirs and files for new user: %s' % full_name

    try:
        os.mkdir(home_dir)
    except:
        print 'Error: could not create home dir: %s' % home_dir
        if not force:
            sys.exit(1)

    try:
        os.mkdir(mrsl_dir)
    except:
        print 'Error: could not create mrsl dir: %s' % mrsl_dir
        if not force:
            sys.exit(1)

    try:
        os.mkdir(pending_dir)
    except:
        print 'Error: could not create resource dir: %s' % pending_dir
        if not force:
            sys.exit(1)
else:
    # Allow temporary write access
    os.chmod(htaccess_path, 0644)

# Always write htaccess to catch any updates

try:
    filehandle = open(htaccess_path, 'w')

    # Match all known fields

    access = 'SSLRequire ('
    access += '%%{SSL_CLIENT_S_DN_CN} eq "%(full_name)s"'
    access += ' && %%{SSL_CLIENT_S_DN_O} eq "%(organization)s"'
    access += ' && %%{SSL_CLIENT_S_DN_ST} eq "%(state)s"'
    access += ' && %%{SSL_CLIENT_S_DN_C} eq "%(country)s"'
    access += ' && %%{SSL_CLIENT_S_DN_Email} eq "%(email)s"'
    access += ')\n'

    # Hack to match cert fall back to 'NA' if state is empty

    real_state = user_dict['state']
    if not user_dict['state']:
        user_dict['state'] = 'NA'
    filehandle.write(access % user_dict)
    user_dict['state'] = real_state
    filehandle.close()

    # try to prevent further user modification

    os.chmod(htaccess_path, 0444)
except:
    print 'Error: could not create htaccess file: %s' % htaccess_path
    if not force:
        sys.exit(1)

print 'DB entry and dirs for %s were created or updated' % user_id
if user_file:
    print 'Cleaning up tmp file: %s' % user_file
    os.remove(user_file)
