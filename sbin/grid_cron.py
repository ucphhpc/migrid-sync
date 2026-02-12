#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_cron - daemon to monitor user crontabs and trigger actions
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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

"""Daemon to monitor user crontabs and trigger any associated actions when
configured.

Requires watchdog module (https://pypi.python.org/pypi/watchdog).
"""

from __future__ import print_function
from __future__ import absolute_import

import multiprocessing
import os
import signal
import sys
import time

from mig.lib.cron import cron_monitor
from mig.lib.daemon import check_stop, register_stop_handler, stop_running
from mig.shared.conf import get_configuration_object
from mig.shared.logger import daemon_logger, register_hangup_handler

# Global state helpers used in a number of functions and methods

(configuration, logger) = (None, None)


if __name__ == '__main__':
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning',
                                        'error']:
        log_level = sys.argv[1]

    # Use separate logger

    logger = daemon_logger('cron', configuration.user_cron_log,
                           log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # Allow clean shutdown on SIGINT only to main process
    register_stop_handler(configuration)

    if not configuration.site_enable_crontab:
        err_msg = "Cron support is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)

    print('''This is the MiG cron handler daemon which monitors user crontab
files and reacts to any configured actions when time is up.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
''')

    main_pid = os.getpid()
    print('Starting Cron handler daemon - Ctrl-C to quit')
    logger.info('(%s) Starting Cron handler daemon' % main_pid)

    # Start a single global monitor for all crontabs

    crontab_monitor = multiprocessing.Process(target=cron_monitor,
                                              args=(configuration, ))
    crontab_monitor.start()

    logger.debug('(%s) Starting main loop' % main_pid)
    print("%s: Start main loop" % os.getpid())
    while not stop_running.is_set():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            stop_running.set()
            # NOTE: we can't be sure if SIGINT was sent to only main process
            #       so we make sure to propagate to monitor child
            print("Interrupt requested - close monitor and shutdown")
            logger.info('(%s) Shut down monitor and wait' % os.getpid())
            mon_pid = crontab_monitor.pid
            if mon_pid is not None:
                logger.debug('send exit signal to monitor %s' % mon_pid)
                os.kill(mon_pid, signal.SIGINT)
            break
        except Exception as exc:
            logger.error('(%s) Caught unexpected exception: %s' % (os.getpid(),
                                                                   exc))

    mon_pid = crontab_monitor.pid
    logger.info('Wait for crontab monitors to clean up')
    crontab_monitor.join(5)
    if crontab_monitor.is_alive():
        logger.warning("force kill %s: %s" % (mon_pid,
                                              crontab_monitor.is_alive()))
        crontab_monitor.terminate()
    else:
        logger.debug('crontab monitor %s: done' % mon_pid)

    print('Cron handler daemon shutting down')
    logger.info('(%s) Cron handler daemon shutting down' % main_pid)

    sys.exit(0)
