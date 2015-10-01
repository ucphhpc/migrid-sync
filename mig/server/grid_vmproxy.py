#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_vmproxy - VM proxy wrapper daemon
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

import os
import sys
import time

from shared.conf import get_configuration_object


if __name__ == '__main__':
    configuration = get_configuration_object()
    logger = configuration.logger

    if not configuration.site_enable_vmachines:
        err_msg = "VMachines and proxy helper is disabled in configuration!"
        logger.error(err_msg)
        print err_msg
        sys.exit(1)

    print """
Running grid VM proxy helper for users to access VMachines on resources.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""

    vm_proxy_base = os.path.join(configuration.mig_code_base, 'vm-proxy')
    daemon_name = 'migproxy.py'
    daemon_path = os.path.join(vm_proxy_base, daemon_name)
    if not os.path.exists(daemon_path):
        err_msg = "VMachines proxy helper not found!"
        logger.error(err_msg)
        print err_msg
        sys.exit(1)

    keep_running = True

    print 'Starting VM proxy helper daemon - Ctrl-C to quit'

    daemon_proc = None
    while keep_running:
        try:
            daemon_proc = subprocess.Popen([daemon_path]).wait()

            # Throttle down

            time.sleep(1)
        except KeyboardInterrupt:
            keep_running = False
        except Exception, exc:
            print 'Caught unexpected exception: %s' % exc
            irc = None
            attempt += 1

    print 'VM proxy daemon shutting down'
    sys.exit(0)
