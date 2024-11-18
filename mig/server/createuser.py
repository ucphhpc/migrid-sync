#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createuser - Create or renew a MiG user with all the necessary directories
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

"""Add or renew MiG user in user DB and in file system"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import input
from getpass import getpass
import datetime
import getopt
import os
import sys
import time

from mig.shared.accountstate import default_account_expire
from mig.shared.base import fill_distinguished_name, fill_user, canonical_user
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import valid_auth_types, keyword_auto
from mig.shared.gdp.all import ensure_gdp_user
from mig.shared.minimist import parse_getopt_args, break_apart_legacy_usage
from mig.shared.pwcrypto import unscramble_password, scramble_password, \
    make_hash
from mig.shared.serial import load
from mig.shared.useradm import init_user_adm, create_user, load_user_dict
from mig.shared.userdb import default_db_path

cert_warn = """
Please note that you *must* use either the -i CERT_DN option to createuser
or use importuser instead if you want to use other certificate DN formats
than the one expected by MiG (/C=.*/ST=.*/L=NA/O=.*/CN=.*/emailAddress=.*)
Otherwise those users will NOT be able to access their MiG interfaces!
"""

# NOTE: codes explained in the python library reference e.g. as for python3 on
# https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
expire_formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M", "%x", "%c"]


def usage(name='createuser.py'):
    """Usage help"""

    print("""Create user in the MiG user database and file system.
%(cert_warn)s
Usage:
%(name)s [OPTIONS] [FULL_NAME ORGANIZATION STATE COUNTRY \
    EMAIL COMMENT PASSWORD]
or
%(name)s [OPTIONS] -u USER_FILE
or
%(name)s [OPTIONS] -i CERT_DN
Where OPTIONS may be one or more of:
""")

name_by_argument = break_apart_legacy_usage("""
   -a: AUTH_TYPE
   -c: CONF_FILE
   -d: DB_FILE
   -e: EXPIRE
   -i: CERT_DN
   -o: SHORT_ID
   -p: PEER_PATTERN
   -R: ROLES
   -s: SLACK_DAYS
   -u: USER_FILE
""")

help_by_argument = break_apart_legacy_usage("""
   -a: Prepare account for AUTH_TYPE login (expire, password)
   -c: Use CONF_FILE as server configuration
   -d: Use DB_FILE as user data base file
   -e: Set user account expiration to EXPIRE (epoch)
   -f: Force operations to continue past errors
   -i: Use CERT_DN as user ID despite what other fields suggest
   -o: Add SHORT_ID as OpenID alias for user
   -p: Verify in Peers of existing account matching PEER_PATTERN
   -r: Renew user account with existing values
   -R: Set user affiliation to ROLES
   -s: Allow peers even with account expired within SLACK_DAYS
   -u: Read user information from pickle file
   -v: Verbose output
""")


def main(args, cwd, db_path=keyword_auto):
    conf_path = None
    auth_type = 'custom'
    expire = None
    force = False
    verbose = False
    ask_renew = True
    default_renew = False
    ask_change_pw = True
    user_file = None
    user_id = None
    short_id = None
    role = None
    peer_pattern = None
    slack_secs = 0
    hash_password = True
    user_dict = {}
    override_fields = {}
    opt_args = 'a:c:d:e:fhi:o:p:rR:s:u:v'

    try:
        (opts, args) = parse_getopt_args(args, opt_args,
        help_by_argument=help_by_argument, name_by_argument=name_by_argument)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-a':
            auth_type = val
        elif opt == '-c':
            conf_path = val
        elif opt == '-d':
            db_path = val
        elif opt == '-e':
            parsed = False
            for fmt in ["EPOCH"] + expire_formats:
                try:
                    if fmt == "EPOCH":
                        raw = val
                    else:
                        raw = datetime.datetime.strptime(val, fmt)
                        raw = raw.strftime("%s")
                    expire = int(raw)
                    parsed = True
                    break
                except (TypeError, ValueError):
                    print('Failed to parse expire value: %s' % val)
                    sys.exit(1)
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-i':
            user_id = val
        elif opt == '-o':
            short_id = val
        elif opt == '-p':
            peer_pattern = val
        elif opt == '-r':
            default_renew = True
            ask_renew = False
        elif opt == '-R':
            role = val
        elif opt == '-s':
            # Translate slack days into seconds as
            slack_secs = int(float(val)*24*3600)
        elif opt == '-u':
            user_file = val
            # NOTE: hashing should already be handled explicitly
            hash_password = False
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            sys.exit(1)

    print("HURRAH")
    exit(1)

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

    _main(None, args,
          conf_path=conf_path,
          db_path=db_path,
          expire=expire,
          force=force,
          verbose=verbose,
          ask_renew=ask_renew,
          default_renew=default_renew,
          ask_change_pw=ask_change_pw,
          user_file=user_file,
          user_id=user_id,
          short_id=short_id,
          role=role,
          peer_pattern=peer_pattern,
          slack_secs=slack_secs,
          hash_password=hash_password
          )


def _main(configuration, args,
          conf_path=keyword_auto,
          db_path=keyword_auto,
          auth_type='custom',
          expire=None,
          force=False,
          verbose=False,
          ask_renew=True,
          default_renew=False,
          ask_change_pw=True,
          user_file=None,
          user_id=None,
          short_id=None,
          role=None,
          peer_pattern=None,
          slack_secs=0,
          hash_password=True,
          _generate_salt=None
          ):
    if configuration is None:
        if conf_path == keyword_auto:
            config_file = None
        else:
            config_file = conf_path
        configuration = get_configuration_object(config_file=config_file)

    logger = configuration.logger

    # NOTE: we need explicit db_path lookup here for load_user_dict call
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

    if user_file and args:
        print('Error: Only one kind of user specification allowed at a time')
        usage()
        sys.exit(1)

    if auth_type not in valid_auth_types:
        print('Error: invalid account auth type %r requested (allowed: %s)' %
              (auth_type, ', '.join(valid_auth_types)))
        usage()
        sys.exit(1)

    # NOTE: renew requires original password
    if auth_type == 'cert':
        hash_password = False

    raw_user = {}
    if args:
        try:
            raw_user['full_name'] = args[0]
            raw_user['organization'] = args[1]
            raw_user['state'] = args[2]
            raw_user['country'] = args[3]
            raw_user['email'] = args[4]
            raw_user['comment'] = args[5]
            raw_user['password'] = args[6]
            # Always allow explicit password update on command line
            raw_user['authorized'] = True
        except IndexError:
            print('Error: too few arguments given (expected 7 got %d)'
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
    elif default_renew and user_id:
        saved = load_user_dict(logger, user_id, db_path, verbose)
        if not saved:
            print('Error: no such user in user db: %s' % user_id)
            usage()
            sys.exit(1)
        user_dict.update(saved)
        del user_dict['expire']
    elif not configuration.site_enable_gdp:
        if verbose:
            print('''Entering interactive mode
%s''' % cert_warn)
        print('Please enter the details for the new user:')
        raw_user['full_name'] = input('Full Name: ').title()
        raw_user['organization'] = input('Organization: ')
        raw_user['state'] = input('State: ')
        raw_user['country'] = input('2-letter Country Code: ')
        raw_user['email'] = input('Email: ')
        raw_user['comment'] = input('Comment: ')
        raw_user['password'] = getpass('Password: ')
        # Force user ID fields to canonical form for consistency
        # Title name, lowercase email, uppercase country and state, etc.
        user_dict = canonical_user(configuration, raw_user, raw_user.keys())
    else:
        print("Error: Missing one or more of the arguments: "
              + "[FULL_NAME] [ORGANIZATION] [STATE] [COUNTRY] "
              + "[EMAIL] [COMMENT] [PASSWORD]")
        sys.exit(1)

    # Encode password if set but not already encoded

    if user_dict['password']:
        if hash_password:
            user_dict['password_hash'] = make_hash(user_dict['password'], _generate_salt=_generate_salt)
            user_dict['password'] = ''
        else:
            salt = configuration.site_password_salt
            try:
                unscramble_password(salt, user_dict['password'])
            except TypeError:
                user_dict['password'] = scramble_password(
                    salt, user_dict['password'])

    if user_id:
        user_dict['distinguished_name'] = user_id
    elif 'distinguished_name' not in user_dict:
        fill_distinguished_name(user_dict)

    fill_user(user_dict)

    # assemble the fields to be explicitly overriden
    override_fields = {}
    if peer_pattern:
        override_fields['peer_pattern'] = peer_pattern
        override_fields['status'] = 'temporal'
    if role:
        override_fields['role'] = role
    if short_id:
        override_fields['short_id'] = short_id
    if 'expire' not in user_dict:
        # Make sure account expire is set with local certificate or OpenID login
        if not expire:
            expire = default_account_expire(configuration, auth_type)
        override_fields['expire'] = expire

    # NOTE: let non-ID command line values override loaded values
    for (key, val) in list(override_fields.items()):
        user_dict[key] = val

    # Now all user fields are set and we can begin adding the user

    if verbose:
        print('using user dict: %s' % user_dict)
    try:
        conf_path = configuration.config_file
        create_user(user_dict, conf_path, db_path, configuration, force, verbose, ask_renew,
                    default_renew,
                    verify_peer=peer_pattern,
                    peer_expire_slack=slack_secs, ask_change_pw=ask_change_pw)
        if configuration.site_enable_gdp:
            (success_here, msg) = ensure_gdp_user(configuration,
                                                  "127.0.0.1",
                                                  user_dict['distinguished_name'])
            if not success_here:
                raise Exception("Failed to ensure GDP user: %s" % msg)

    except Exception as exc:
        print("Error creating user: %s" % exc)
        import traceback
        logger.warning("Error creating user: %s" % traceback.format_exc())
        sys.exit(1)
    print('Created or updated %s in user database and in file system' %
          user_dict['distinguished_name'])
    if user_file:
        if verbose:
            print('Cleaning up tmp file: %s' % user_file)
        os.remove(user_file)


if __name__ == '__main__':
    (args, cwd, db_path) = init_user_adm()
    main(args, cwd, db_path=db_path)
