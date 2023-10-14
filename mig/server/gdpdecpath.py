#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# gdpdecpath - Helper to easily unscramble the protected path values in gdp logs
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

"""Helper to unscramble protected path values gdp logs using the configured
password salt.
"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import os
import sys

from mig.shared.conf import get_configuration_object
from mig.shared.pwcrypto import make_decrypt


def usage(name='gdpdecpath.py'):
    """Usage help"""

    print("""Decode a gdp scrambled path to an actual path using salt in MiGserver.conf.
Usage:
%(name)s [OPTIONS] ENCPATH
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -f                  Force operations to continue past errors
   -h                  Show this help
   -v                  Verbose output
""" % {'name': name})


if '__main__' == __name__:
    args = sys.argv[1:]
    conf_path = None
    force = False
    verbose = False
    algo = None
    scrambled_list = []
    opt_args = 'a:c:fhv'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-a':
            algo = val
        elif opt == '-c':
            conf_path = val
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
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

    if args:
        scrambled_list = args
    else:
        usage()
        sys.exit(1)

    configuration = get_configuration_object(skip_log=True)
    if not algo:
        algo = configuration.gdp_path_scramble
    for scrambled in scrambled_list:
        if verbose:
            print('scrambled path %s' % scrambled)
        try:
            plain = make_decrypt(configuration, scrambled,
                                 algo=algo)
            if verbose:
                print('unscrambled path:')
            print(plain)
        except Exception as err:
            print(err)
            sys.exit(1)

    sys.exit(0)
