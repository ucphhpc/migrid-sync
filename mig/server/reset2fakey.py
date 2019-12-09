#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# edituser - (Re)set user 2FA key
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""(Re)set user 2FA key"""

import getopt
import os
import sys
import pyotp

from shared.auth import reset_twofactor_key
from shared.defaults import twofactor_interval_name
from shared.conf import get_configuration_object


def usage(name='reset2fakey.py'):
    """Usage help"""

    print """(Re)set user 2FA key.
Usage:
%(name)s [OPTIONS] -i USER_ID [SEED] [INTERVAL]
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -f                  Force operations to continue past errors
   -h                  Show this help
   -i CERT_DN          CERT_DN of user to edit
   -v                  Verbose output
"""\
         % {'name': name}


# ## Main ###

if '__main__' == __name__:
    conf_path = None
    force = False
    verbose = False
    user_id = None
    seed = None
    interval = None
    opt_args = 'c:fhi:v'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opt_args)
    except getopt.GetoptError, err:
        print 'Error: ', err.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            conf_path = val
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-i':
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
            os.environ['MIG_CONF'] = conf_path
            print 'using configuration in %s' % conf_path
        else:
            print 'using configuration from MIG_CONF (or default)'

    if not user_id:
        print 'Error: Existing user ID is required'
        usage()
        sys.exit(1)

    if args:
        try:
            seed = args[0]
            interval = args[1]
        except IndexError:
             # Ignore missing optional arguments

            pass

    if interval:
        try:
            interval = int(interval)
        except:
            print "Skipping non-int interval: %s" % interval
            interval = None

    if verbose:
        if seed:
            print 'using seed: %s' % seed
        else:
            print 'using random seed: %s' % seed
        if interval:
            print 'using interval: %s' % interval

    configuration = get_configuration_object(skip_log=True)
    twofa_key = reset_twofactor_key(user_id, configuration,
                                    seed=seed, interval=interval)
    if verbose:
        print 'New two factor key: %s' % twofa_key

    if twofa_key:
        print 'Two factor key succesfully reset'
        if verbose:
            if interval:
                twofa_code = pyotp.TOTP(twofa_key, interval=interval).now()
            else:
                twofa_code = pyotp.TOTP(twofa_key).now()
            print 'Current two factor accept code: %s' % twofa_code
    else:
        print 'Failed to reset two factor key'
        sys.exit(1)

    sys.exit(0)
