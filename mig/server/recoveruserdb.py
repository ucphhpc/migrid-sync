#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# recoveruserdb - Recovermissing users in the user database from a backup file
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Add missing users in the user DB based on a backup file and file system"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import input
from getpass import getpass
import datetime
import getopt
import os
import sys
import time

from mig.shared.base import client_id_dir
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import valid_auth_types, keyword_auto
from mig.shared.useradm import init_user_adm, load_user_dict
from mig.shared.userdb import default_db_path, load_user_db, save_user_db


def usage(name='recoveruserdb.py'):
    """Usage help"""

    print("""Recover missing users in the MiG user database based on backup file
Usage:
%(name)s [OPTIONS] BACKUP_FILE
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force operations to continue past errors
   -h                  Show this help
   -v                  Verbose output
""" % {'name': name})


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

    configuration = get_configuration_object(config_file=conf_path)
    logger = configuration.logger
    # NOTE: we need explicit db_path lookup here for load_user_dict call
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

    if not args:
        print('Error: you must supply a backup file to restore missing users from')
        usage()
        sys.exit(1)

    backup_path_list = args[:]
    # Now we can begin restoring missing users still in the file system

    if verbose:
        print('Restoring missing users based on backup in: %s' %
              ', '.join(backup_path_list))
    current_users = load_user_db(db_path)
    missing_users = {}
    for backup_path in backup_path_list:
        backup_users = load_user_db(backup_path)
        for (bk_id, bk_dict) in backup_users.items():
            if not bk_id in current_users:
                bk_home = os.path.join(
                    configuration.user_home, client_id_dir(bk_id))
                if os.path.isdir(bk_home):
                    missing_users[bk_id] = bk_dict
                else:
                    print('DEBUG: skip missing user %s without home %s' %
                          (bk_id, bk_home))
    print('Found %d missing users in %s but in %s and on file system' %
          (len(missing_users), db_path, ', '.join(backup_path_list)))
    for missing_id in missing_users:
        print(missing_id)

    for (missing_id, missing_dict) in missing_users.items():
        current_users[missing_id] = missing_dict

    print('Saving user DB with %d existing and recovered users in %s' %
          (len(current_users), db_path))
    save_user_db(current_users, db_path)
    sys.exit(0)
