#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# chkenabled - Helper to easily lookup site enable values in configuration
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Helper to lookup a specific site_enable_X value in MiGserver.conf used for
detecting which daemons to handle and ignore in init scripts.
"""

import getopt
import os
import sys

from shared.conf import get_configuration_object


def usage(name='chkenabled.py'):
    """Usage help"""

    print """Lookup site_enable_FEATURE value in MiGserver.conf.
Usage:
%(name)s [OPTIONS] FEATURE
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -f                  Force operations to continue past errors
   -h                  Show this help
   -v                  Verbose output
""" % {'name': name}


# ## Main ###

if '__main__' == __name__:
    args = sys.argv
    conf_path = None
    force = False
    verbose = False
    feature = 'UNSET'
    opt_args = 'c:fhv'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
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

    if len(args) == 2:
        feature = args[1]
    else:
        usage()
        sys.exit(1)

    if verbose:
        print 'Lookup configuration value for %s' % feature
    try:
        configuration = get_configuration_object(skip_log=True)
        print getattr(configuration, "site_enable_%s" % feature)
    except Exception, err:
        print err
        sys.exit(1)
