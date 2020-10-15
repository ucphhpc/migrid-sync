#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cleansessions - Helper to clean up stale griddaemon session tracking entries
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
import os
import sys
import time

try:
    import psutil
except ImportError:
    psutil = None

from mig.shared.conf import get_configuration_object
from mig.shared.defaults import keyword_all
from mig.shared.griddaemons.sessions import get_open_sessions, \
    track_close_session


def usage(name='cleansessions.py'):
    """Usage help"""

    print("""Clean stale sessions from griddaemons.
Usage:
%(name)s [OPTIONS] [PROTO] [USERNAME]
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -f                  Force operations to continue past errors
   -h                  Show this help
   -v                  Verbose output
where PROTO is %(all)s or a specific IO protocol and USERNAME is a specific
user but can be left empty to target all users.
""" % {'name': name, 'all': keyword_all})


def parse_connections(configuration, connections):
    """Takes psutil connection list and returns a list of session ID as used
    by griddaemons session tracking.
    """
    sessions = []
    inactive_states = [psutil.CONN_LISTEN, psutil.CONN_NONE]
    for conn in connections:
        if conn.status not in inactive_states:
            session_id = "%s:%s" % conn.raddr
            sessions.append(session_id)
    return sessions


if __name__ == '__main__':
    args = None
    force = False
    verbose = False
    proto = keyword_all
    username = None
    opt_args = 'fhv'
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
        else:
            print('Error: %s not supported!' % opt)

    if args[1:]:
        proto = args[1]
    if args[2:]:
        username = args[2]

    if psutil is None:
        print('Failed to import required psutil module')
        sys.exit(1)

    configuration = get_configuration_object(skip_log=True)

    all_protos = ['davs', 'sftp', 'ftps']
    if proto == keyword_all:
        proto_list = all_protos
    else:
        proto_list = [i for i in all_protos if proto == i]

    if verbose:
        print('Clean up stale sessions for protocol %s and user %s' %
              (proto, username))
    retval = 0
    cleaned = []
    min_stale_secs = 120
    configuration = get_configuration_object(skip_log=True)
    for cur_proto in proto_list:
        sessions = get_open_sessions(configuration, cur_proto, username)
        if not sessions:
            if verbose:
                print('No tracked %s sessions ...' % cur_proto)
            continue
        if verbose:
            print('Found %s sessions:\n%s' % (cur_proto, sessions))
        active_connections = psutil.net_connections()
        active_sessions = parse_connections(configuration, active_connections)
        if verbose:
            print('All active sessions:\n%s' % active_sessions)
        now = time.time()
        for (session_id, info) in sessions.items():
            session_age_secs = now - info['timestamp']
            if session_age_secs < min_stale_secs:
                if verbose:
                    print('Skip session %s only %ds old' %
                          (session_id, session_age_secs))
                continue
            if not session_id in active_sessions:
                if verbose:
                    print('Cleaning stale %s session: %s' %
                          (cur_proto, session_id))

                print('TODO: actually clean stale %s session: %s' %
                      (cur_proto, session_id))

                cleaned.append(session_id)

    if cleaned:
        print("\n### Summary ###")
        print('Cleaned %s stale sessions:\n%s' %
              (len(cleaned), '\n'.join(cleaned)))
        retval = len(cleaned)
    sys.exit(retval)
