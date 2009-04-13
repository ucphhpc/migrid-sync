#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# server - Failover server wrapper script
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Full MiG server:
This wrapper script handles a full MiG server in the failover model.
If this server is the current group leader, the server runs the necessary
MiG components, including the main script, monitor and notification.
"""

import os
import sys
import signal
import time

import shared.distfile as distfile
from shared.distbase import get_leader, get_address


def start_component(app, args=[''], env={}):
    """Start app in a separate process"""

    pid = os.fork()
    if pid == 0:
        if not args[0]:
            args = [app]

        # child - take over this process to catch all signals

        os.setsid()
        print os.getpid(), os.getpgid(0)
        os.execve(app, args, env)
    return pid


def stop_component(pid):
    """Stop app running in process with specified pid by sending SIGINT
    (possibly followed by SIGKILL) to process group.
    """

    pgid = os.getpgid(pid)
    print 'Sending INT to pgid %d' % pgid
    os.killpg(pgid, signal.SIGINT)
    for i in range(15):
        (id, status) = os.waitpid(pid, os.WNOHANG)
        if (id, status) != (0, 0):
            break
        time.sleep(2)
    if (id, status) == (0, 0):

        # Still alive

        print 'Sending KILL to pgid %d' % pgid
        os.killpg(pgid, signal.SIGKILL)
        (id, status) = os.waitpid(pid, 0)
        print 'Process(es) killed forcefully'
    else:
        print 'Process(es) exited cleanly'
    return None


def start_server(components):
    """Start all server components"""

    for i in range(len(components)):
        (app, _) = components[i]
        print 'starting %s' % app
        components[i] = (app, start_component(app))


def stop_server(components):
    """Stop all server components"""

    for i in range(len(components)):
        (app, pid) = components[i]
        if not pid:
            print "skipping %s which isn't running" % app
            continue
        print 'stopping %s with pid %s' % (app, pid)
        components[i] = (app, stop_component(pid))


def graceful_shutdown(signum, frame):
    print '%s: graceful_shutdown called' % sys.argv[0]
    try:
        global components
        stop_server(components)
    except:
        pass
    sys.exit(0)


def true():
    """dummy function for testing: always returns True"""

    return True


# ## Main ###
# register ctrl+c signal handler to shutdown system gracefully

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

pid_name = sys.argv[0].replace('.py', '.pid')
pid_file = open(pid_name, 'w')
pid_file.write('%s' % os.getpid())
pid_file.close()

base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

# dictionary of server apps and their associated PIDs

components = []
components.append(('grid_script.py', None))
components.append(('MiGMonitor.py', None))

# TODO: add next line when notify is ready
# components(("im_notify.py"], None))

# Use first argument (if given) as path to config file

print 'Starting Full MiG server'

own_address = get_address()
is_leader = False
while True:
    was_leader = is_leader
    current_leader = get_leader()
    if current_leader == own_address:
        is_leader = True
    else:
        is_leader = False

    if is_leader:
        if not was_leader:
            print 'New local leader: starting MiG components'
            start_server(components)
        else:
            print 'Still local leader: keep running MiG components'
    else:

        if not was_leader:
            print 'Still not the leader - sleeping'
        else:
            print 'No longer local leader: stopping MiG components'
            stop_server(components)

    time.sleep(10)

