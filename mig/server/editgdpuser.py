#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# editgdpuser - Edit a MiG GDP user
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Edit MiG GDP user in the GDP database and all related GDP project users
in the MiG user database and file system"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import os
import sys

from mig.shared.conf import get_configuration_object
from mig.shared.gdp.all import edit_gdp_user, reset_account_roles, \
    set_account_state
from mig.shared.useradm import init_user_adm


def usage(name='editgdpuser.py'):
    """Usage help"""

    print("""Edit existing GDP user in the GDP database,
and all related GDP project users in the MiG user database and file system.
Allows user ID changes.
Usage:
%(name)s [OPTIONS] -i USER_ID [FULL_NAME] [ORGANIZATION] [STATE] [COUNTRY] [EMAIL]
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d MIG DB_FILE      Use DB_FILE as MiG user database file
   -f                  Force operations to continue past errors
                       WARNING: This disables rollback in case of failure
   -g GDP DB_FILE      Use GDP_DB_FILE as GDP user database file
   -h                  Show this help
   -i CERT_DN          CERT_DN of user to edit
   -r                  Reset project logins
   -S ACCOUNT_STATE    Change GDP user account state to ACCOUNT_STATE
   -v                  Verbose output
"""
          % {'name': name})


# ## Main ###

if '__main__' == __name__:
    flock = None
    (args, app_dir, mig_db_path) = init_user_adm()
    gdp_db_path = None
    conf_path = None
    force = False
    verbose = False
    user_id = None
    short_id = None
    account_state = None
    reset_roles = False
    user_dict = {}
    opt_args = 'c:g:d:fhri:S:v'
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
            mig_db_path = val
        elif opt == '-f':
            force = True
        elif opt == '-g':
            gdp_db_path = val
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-i':
            user_id = val
        elif opt == '-r':
            reset_roles = True
        elif opt == '-S':
            account_state = val
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

    configuration = get_configuration_object(config_file=conf_path)

    if not user_id:
        print('Error: Existing user ID is required')
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

    elif not (account_state or reset_roles):
        print("Error: Missing one or more of the arguments: "
              + "[FULL_NAME] [ORGANIZATION] [STATE] [COUNTRY] "
              + "[EMAIL]")
        sys.exit(1)

    # Remove empty value fields

    for (key, val) in user_dict.items():
        if not val:
            del user_dict[key]

    if account_state:
        (status, msg) = set_account_state(
            configuration,
            user_id,
            account_state,
            gdp_db_path=gdp_db_path)
        print(msg)
    elif reset_roles:
        (status, msg) = reset_account_roles(
            configuration,
            user_id,
            gdp_db_path=gdp_db_path,
            verbose=verbose)
    else:
        if force:
            print("WARNING: -f disables rollback !!!")
        (status, msg) = edit_gdp_user(
            configuration,
            user_id,
            user_dict,
            conf_path,
            mig_db_path,
            gdp_db_path=gdp_db_path,
            force=force,
            verbose=verbose)
    if not verbose:
        # NOTE: If verbose everything is printed from functions in GDP
        if not status:
            print("ERROR: " + msg)
        else:
            print(msg)

    if status:
        if account_state:
            print("OK: Account state set successfully")
        elif reset_roles:
            print("OK: Project logins reset successfully")
        else:
            print("OK: User modified successfully")
    if not status:
        print("ERROR: Failed to edit user: %r" % user_id)

    if not status:
        sys.exit(1)
