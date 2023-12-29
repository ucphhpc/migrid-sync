#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cleansessions - Helper to clean up stale griddaemon session tracking entries
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

"""Helper to clean up any stale entries from the griddaemon session tracking.
Relies on psutil to lookup established connections for comparison.
"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import sys

from mig.shared.conf import get_configuration_object
from mig.shared.griddaemons.sessions import expire_dead_sessions


def usage(name='cleansessions.py'):
    """Usage help"""

    print("""Clean stale sessions from griddaemons.
Usage:
%(name)s [OPTIONS] [PROTO ...]
Where OPTIONS may be one or more of:
   -f                  Force operations to continue past errors
   -h                  Show this help
   -v                  Verbose output
   -u USERNAME         Username to specifically target in session clean up
where PROTO is one or more specific IO protocols or all if it is left out.
Sessions of all users are cleaned unless a specific username is requested.
""" % {'name': name})


if __name__ == '__main__':
    args = None
    force = False
    verbose = False
    username = None
    opt_args = 'fhvu:'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-v':
            verbose = True
        elif opt == '-u':
            username = val
        else:
            print('Error: %s not supported!' % opt)

    proto_list = ['davs', 'sftp', 'ftps']
    if args:
        proto_list = [proto for proto in args
                      if proto in proto_list]

    configuration = get_configuration_object()

    if verbose:
        print('Clean up stale sessions for protocol(s) %r and user %s' %
              (" ".join(proto_list), username))
    retval = 0
    cleaned = []
    configuration = get_configuration_object(skip_log=True)
    for cur_proto in proto_list:
        expired = expire_dead_sessions(configuration, cur_proto, username)
        cleaned += list(expired)

    if cleaned:
        if verbose:
            print("\n### Session Clean Summary ###")
        print('Cleaned %s stale %s sessions:\n%s' %
              (len(cleaned), " ".join(proto_list), '\n'.join(cleaned)))
        retval = len(cleaned)
    sys.exit(retval)
