#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_vmproxy - VM proxy wrapper daemon
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

"""Wraps the vm-proxy daemon in a way suitable for use in the init script"""

from __future__ import print_function
from __future__ import absolute_import

import os
import signal
import sys
import time

from mig.shared.conf import get_configuration_object
from mig.shared.logger import daemon_logger, register_hangup_handler
from mig.shared.safeeval import subprocess_popen

configuration, logger = None, None


def handle_stop(signum, stack):
    print("Got signal %s - fake ctrl-c" % signum)
    raise KeyboardInterrupt


if __name__ == '__main__':
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("vmproxy", configuration.user_vmproxy_log,
                           log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # Allow clean exit
    signal.signal(signal.SIGTERM, handle_stop)

    if not configuration.site_enable_vmachines:
        err_msg = "VMachines and proxy helper is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)

    print("""
Running grid VM proxy helper for users to access VMachines on resources.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
""")

    vm_proxy_base = os.path.join(configuration.mig_code_base, 'vm-proxy')
    daemon_name = 'migproxy.py'
    daemon_path = os.path.join(vm_proxy_base, daemon_name)
    if not os.path.exists(daemon_path):
        err_msg = "VMachines proxy helper not found!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)

    keep_running = True

    print('Starting VM proxy helper daemon - Ctrl-C to quit')
    logger.info("Starting VM proxy daemon")

    daemon_proc = None
    while keep_running:
        try:
            # Run vm-proxy helper in the foreground from corresponding dir
            daemon_proc = subprocess_popen([daemon_path, '-n'],
                                           cwd=vm_proxy_base)
            retval = daemon_proc.wait()
            logger.info("daemon returned %s" % retval)
            daemon_proc = None
        except KeyboardInterrupt:
            keep_running = False
            break
        except Exception as exc:
            msg = 'Caught unexpected exception: %s' % exc
            logger.error(msg)
            print(msg)
        # Throttle down
        time.sleep(30)

    if daemon_proc is not None:
        logger.info('Killing spawned proxy daemon')
        daemon_proc.terminate() or daemon_proc.kill()

    print('VM proxy daemon shutting down')
    sys.exit(0)
