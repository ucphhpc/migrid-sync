#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# im_notify_stdout - Dummy IM daemon
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

"""Dummy IM daemon writing requests to stdout instead of sending them"""

import os
import sys
import time

from shared.conf import get_configuration_object


# ## MAIN ###
print '''This is a dummy MiG IM notification daemon which just prints requests.

The real notification daemon, im_notify.py, hard codes accounts and thus
does not support multiple instances. So please only run this dummy daemon and
*not* the real daemon anywhere but on the main official MiG server.
'''

configuration = get_configuration_object()
stdin_path = configuration.im_notify_stdin

try:
    if not os.path.exists(stdin_path):
        print 'IM stdin %s does not exist, creating it with mkfifo!'
        try:
            os.mkfifo(stdin_path, mode=0600)
        except Exception, err:
            print 'Could not create missing IM stdin fifo: %s exception: %s '\
                 % (stdin_path, err)
except:
    print 'error opening IM stdin! %s' % sys.exc_info()[0]
    sys.exit(1)

keep_running = True

print 'Starting Dummy IM daemon - Ctrl-C to quit'

print 'Reading commands from %s' % stdin_path
try:
    im_notify_stdin = open(stdin_path, 'r')
except KeyboardInterrupt:
    keep_running = False
except Exception, exc:
    print 'could not open IM stdin %s: %s'\
         % (stdin_path, exc)

while keep_running:
    try:
        line = im_notify_stdin.readline()
        if line.upper().startswith('SENDMESSAGE '):
            print line
        elif line:
            print 'unknown message received: %s' % line
            
        # Throttle down
        time.sleep(1)

    except KeyboardInterrupt:
        keep_running = False
    except Exception, exc:
        print 'Caught unexpected exception: %s' % exc

print 'Dummy IM daemon shutting down'
sys.exit(0)
