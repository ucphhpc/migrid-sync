#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# edituser - Edit a MiG user
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# -- END_HEADER ---
#

"""Edit MiG user in user database and file system"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import input
import getopt
import os
import sys

from mig.shared.base import fill_distinguished_name, fill_user, canonical_user, \
    force_native_str_rec, is_gdp_user
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import keyword_auto
from mig.shared.serial import load
from mig.shared.useradm import init_user_adm, edit_user
from mig.shared.userdb import default_db_path


def usage(name='edituser.py'):
    """Usage help"""

    print("""Edit existing user in MiG user database and file system. Allows
user ID changes.
NOTE: It's usually easier to use editmeta.py for non-ID field changes.
Usage:
%(name)s [OPTIONS] -i USER_ID -u USER_FILE
or
%(name)s [OPTIONS] -i USER_ID -n NEW_ID
or
%(name)s [OPTIONS] -i USER_ID [FULL_NAME] [ORGANIZATION] [STATE] [COUNTRY] \
    [EMAIL]
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force operations to continue past errors
   -h                  Show this help
   -i USER_ID          USER_ID of the user to edit
   -n NEW_ID           Edit existing user ID fields to fit NEW_ID
   -o SHORT_ID         Change OpenID alias of user to SHORT_ID
   -r FIELDS           Remove FIELDS for user in user DB
   -R ROLES            Change user affiliation to ROLES
   -u USER_FILE      Update to new user information from pickle file
   -v                  Verbose output
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    force = False
    verbose = False
    user_file = None
    user_id = None
    short_id = None
    role = None
    remove_fields = []
    user_dict = {}
    opt_args = 'c:d:fhi:o:r:R:u:v'
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
        elif opt == '-i':
            user_id = val
        elif opt == '-o':
            short_id = val
        elif opt == '-r':
            remove_fields += val.split()
        elif opt == '-R':
            role = val
        elif opt == '-u':
            user_file = val
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            sys.exit(1)

    if conf_path and not os.path.isfile(conf_path):
        print('Failed to read configuration file: %s' % conf_path)
        sys.exit(1)

    if verbose:
        if conf_path:
            if verbose:
                print('using configuration in %s' % conf_path)
        else:
            if verbose:
                print('using configuration from MIG_CONF (or default)')

    # TODO: do we really want skip_log here?
    configuration = get_configuration_object(
        config_file=conf_path, skip_log=True)
    logger = configuration.logger

    if user_file and args:
        print('Error: Only one kind of user specification allowed at a time')
        usage()
        sys.exit(1)

    if not user_id:
        print('Error: Existing user ID is required')
        usage()
        sys.exit(1)

    if is_gdp_user(configuration, user_id) and not force:
        print("Error: GDP user ID detected")
        print("You probably want to use 'editgdpuser.py'")
        print("If you really mean it then use: 'edituser.py -f'")
        sys.exit(1)

    raw_user = {}
    if args:
        # logger.debug('edituser called with args: %s' % args)
        try:
            raw_user['full_name'] = args[0]
            raw_user['organization'] = args[1]
            raw_user['state'] = args[2]
            raw_user['country'] = args[3]
            raw_user['email'] = args[4]
        except IndexError:
            print('Error: too few arguments given (expected 5 got %d)'
                  % len(args))
            usage()
            sys.exit(1)
        # Force user ID fields to canonical form for consistency
        # Title name, lowercase email, uppercase country and state, etc.
        user_dict = canonical_user(configuration, raw_user, raw_user.keys())
    elif user_file:
        try:
            user_dict = load(user_file)
        except Exception as err:
            print('Error in user name extraction: %s' % err)
            usage()
            sys.exit(1)
    elif not configuration.site_enable_gdp:
        # NOTE: We do not allow interactive user management on GDP systems
        if verbose:
            print('Entering interactive mode')
        print('Please enter the new user details for %s:' % user_id)
        raw_user['full_name'] = input('Full Name: ').title()
        raw_user['organization'] = input('Organization: ')
        raw_user['state'] = input('State: ')
        raw_user['country'] = input('2-letter Country Code: ')
        raw_user['email'] = input('Email: ')
        # Force user ID fields to canonical form for consistency
        # Title name, lowercase email, uppercase country and state, etc.
        user_dict = canonical_user(configuration, raw_user, raw_user.keys())
    else:
        print("Error: Missing one or more of the arguments: "
              + "[FULL_NAME] [ORGANIZATION] [STATE] [COUNTRY] "
              + "[EMAIL]")
        sys.exit(1)

    fill_distinguished_name(user_dict)

    # logger.debug('edituser to new ID: %(distinguished_name)s' % user_dict)
    fill_user(user_dict)

    force_native_str_rec(user_dict)
    # logger.debug('createuser forced to ID: %s' %
    #             [user_dict['distinguished_name']])

    # Pass optional short_id as well
    if short_id:
        user_dict['short_id'] = short_id

    # Pass optional role as well
    if role:
        user_dict['role'] = role

    # Remove empty value fields
    # NOTE: force list copy here as we delete inline below
    for key in list(user_dict):
        if not user_dict[key]:
            del user_dict[key]

    # Now all user fields are set and we can begin editing the user

    if verbose:
        print('Update DB entry and dirs for %s using dict: %s' % (user_id,
                                                                  user_dict))
    try:
        user = edit_user(user_id, user_dict, remove_fields, conf_path,
                         db_path, force, verbose)
    except Exception as exc:
        print("Error editing user: %s" % exc)
        import traceback
        logger.warning("Error creating user: %s" % traceback.format_exc())
        sys.exit(1)
    print('%s\nchanged to\n%s\nin user database and file system' %
          (user_id, user['distinguished_name']))
    print()
    print('Please revoke/reissue any related certificates!')
    if user_file:
        if verbose:
            print('Cleaning up tmp file: %s' % user_file)
        os.remove(user_file)
