#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_janitor - daemon to handle recurring tasks like clean up and updates
# Copyright (C) 2003-2025  The MiG Project lead by Brian Vinter
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

"""Daemon to take care of various recurring tasks like clean up, cache updates
and pruning of pending requests.
"""

from __future__ import absolute_import, print_function

import multiprocessing
import os
import signal
import sys
import time

from mig.shared.conf import get_configuration_object
from mig.shared.logger import daemon_logger, register_hangup_handler

stop_running = multiprocessing.Event()
(configuration, logger) = (None, None)


def stop_handler(sig, frame):
    """A simple signal handler to quit on Ctrl+C (SIGINT) in main"""
    # Print blank line to avoid mix with Ctrl-C line
    print("")
    stop_running.set()


if __name__ == "__main__":
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ["debug", "info", "warning", "error"]:
        log_level = sys.argv[1]

    # Use separate logger

    logger = daemon_logger("janitor", configuration.user_janitor_log, log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # Allow clean shutdown on SIGINT only to main process
    signal.signal(signal.SIGINT, stop_handler)

    if not configuration.site_enable_janitor:
        err_msg = "Janitor support is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)

    print(
        """This is the MiG janitor daemon which cleans up stale state data,
updates internal caches and prunes pending requests.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""
    )

    main_pid = os.getpid()
    print("Starting janitor daemon - Ctrl-C to quit")
    logger.info("(%s) Starting Janitor daemon" % main_pid)

    logger.debug("(%s) Starting main loop" % main_pid)
    print("%s: Start main loop" % os.getpid())
    while not stop_running.is_set():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            stop_running.set()
            # NOTE: we can't be sure if SIGINT was sent to only main process
            #       so we make sure to propagate to monitor child
            print("Interrupt requested - shutdown")
        except Exception as exc:
            logger.error(
                "(%s) Caught unexpected exception: %s" % (os.getpid(), exc)
            )

    print("Janitor daemon shutting down")
    logger.info("(%s) Janitor daemon shutting down" % main_pid)

    sys.exit(0)
