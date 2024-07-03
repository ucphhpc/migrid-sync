#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# genoiddiscovery - Helper to easily generate openid discovery info xml
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

"""Helper to generate the discovery information for the OpenID 2.0 relying
party verification mechanism. Please refer to the generate_openid_discovery_doc
helper function for details.
"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import os
import sys

from mig.shared.conf import get_configuration_object
from mig.shared.httpsclient import generate_openid_discovery_doc


def usage(name='genoiddiscovery.py'):
    """Usage help"""

    print("""Generate OpenID 2.0 discovery information for this site.
Usage:
%(name)s [OPTIONS] NAME
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
    opt_args = 'c:fhv'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
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
        print('Got unexpected non-option arguments!')
        usage()
        sys.exit(1)

    if verbose:
        print("""OpenID discovery information XML which may be pasted into
state/wwwpublic/oiddiscover.xml if site uses OpenId but doesn't enable the
SID vhost:
""")
    retval = 42
    try:
        configuration = get_configuration_object(skip_log=True)
        print(generate_openid_discovery_doc(configuration))
        retval = 0
    except Exception as err:
        print(err, file=sys.stderr)
        sys.exit(1)

    sys.exit(retval)
