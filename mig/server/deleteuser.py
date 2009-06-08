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

import sys
import time
import os
import getopt
import base64
import pickle

from shared.configuration import Configuration


def usage(name='deleteuser.py'):
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


def delete_dir(path):
    """Recursively remove path:
    first remove all files and subdirs, then remove dir tree.
    """

    for (root, dirs, files) in os.walk(path, topdown=False):
        for name in files:
            print 'removing: ' + root + os.sep + name
            os.remove(root + os.sep + name)
        for name in dirs:
            print 'removing: ' + root + os.sep + name
            os.rmdir(root + os.sep + name)
    os.removedirs(path)


# ## Main ###

args = sys.argv[1:]
app_dir = os.path.dirname(sys.argv[0])
if not app_dir:
    app_dir = '.'
conf = app_dir + os.sep + 'MiGserver.conf'
db_file = app_dir + os.sep + 'MiG-users.db'
verbose = False
force = False
user_id = None
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
        conf = val
    elif opt == '-d':
        db_file = val
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

if not os.path.isfile(conf):
    print 'Failed to read configuration file: %s' % conf
    sys.exit(1)

if verbose:
    print 'using configuration in %s' % conf

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

user_id = '%(full_name)s:%(organization)s:' % user_dict
user_id += '%(state)s:%(country)s:%(email)s' % user_dict
full_name = user_dict['full_name']
full_name_without_spaces = full_name.replace(' ', '_')

if not full_name:
    print 'Missing Full Name!'
    sys.exit(1)

configuration = Configuration(conf)
print 'Removing DB entry and dirs for specified user: %s' % full_name
print 'User name without spaces: %s\n' % full_name_without_spaces

# Update user data base

if os.path.exists(db_file):
    try:
        db_fd = open(db_file, 'rb')
        user_db = pickle.load(db_fd)
        db_fd.close()
        print 'Loaded existing user DB from: %s' % db_file
    except Exception, err:
        print 'Failed to load user DB!'
        if not force:
            sys.exit(1)

    if not user_db.has_key(user_id):
        print "Error: User DB entry '%s' doesn't exist!" % user_id
        if not force:
            sys.exit(1)

try:
    del user_db[user_id]
    db_fd = open(db_file, 'wb')
    pickle.dump(user_db, db_fd)
    db_fd.close()
    print 'User %s was successfully removed from user DB!' % full_name
except Exception, err:
    print 'Error: Failed to remove %s from user DB: %s' % (full_name,
            err)
    if not force:
        sys.exit(1)

if not os.path.exists(configuration.user_home
                       + full_name_without_spaces):
    print "Error: User dir doesn't exist!"
    if not force:
        sys.exit(1)

# Remove user dirs

try:
    delete_dir(configuration.resource_pending
                + full_name_without_spaces)
except:
    print 'Error: could not remove resource dir: %s'\
         % configuration.resource_pending + full_name_without_spaces
    if not force:
        sys.exit(1)

try:
    htaccessfilename = configuration.user_home\
         + full_name_without_spaces + '/.htaccess'
    os.remove(htaccessfilename)
except:
    print 'Error: could not remove htaccess file: %s' % htaccessfilename
    if not force:
        sys.exit(1)

try:
    delete_dir(configuration.mrsl_files_dir + full_name_without_spaces)
except:
    print 'Error: could not remove mrsl dir: %s'\
         % configuration.mrsl_files_dir + full_name_without_spaces
    if not force:
        sys.exit(1)

try:
    delete_dir(configuration.user_home + full_name_without_spaces)
except Exception, err:
    print 'Error: could not remove home dir: %s (%s)'\
         % (configuration.user_home + full_name_without_spaces, err)
    if not force:
        sys.exit(1)

print 'DB entry and dirs for %s were removed' % full_name
