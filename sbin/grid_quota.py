#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_quota - daemon to manage storage quotas
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Daemon to manage storage quotas"""

from __future__ import absolute_import, print_function

import os
import sys
import time
import traceback
import datetime

from mig.lib.daemon import check_run, check_stop, interruptible_sleep, \
    register_run_handler, register_stop_handler, reset_run, stop_running
from mig.lib.quota import update_quota, supported_quota_backends
from mig.shared.conf import get_configuration_object
from mig.shared.logger import daemon_logger, register_hangup_handler


if __name__ == "__main__":
    print(
        """This is the MiG quota daemon which collects storage quota
        information for users and vgrids.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""
    )
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ["debug", "info", "warning", "error"]:
        log_level = sys.argv[1]

    # Use separate logger

    logger = daemon_logger("quota",
                           configuration.user_quota_log,
                           log_level)
    configuration.logger = logger

    # Check if quota is enabled

    if not configuration.site_enable_quota:
        msg = "Quota support is disabled in configuration!"
        logger.error(msg)
        print("%s ERROR: %s"
              % (datetime.datetime.now(), msg),
              file=sys.stderr)
        sys.exit(1)

    # Check quota backend

    if configuration.quota_backend not in supported_quota_backends:
        msg = "Quota backend: %s not in supported backends: %s" \
            % (configuration.quota_backend,
               ", ".join(supported_quota_backends))
        logger.error(msg)
        print("%s ERROR: %s"
              % (datetime.datetime.now(), msg),
              file=sys.stderr)
        sys.exit(1)

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # Allow trigger next run on SIGCONT to main process
    register_run_handler(configuration)

    # Allow clean shutdown on SIGINT only to main process
    register_stop_handler(configuration)

    throttle_secs = float(configuration.quota_update_interval)
    main_pid = os.getpid()
    msg = "(%s) Starting quota daemon with throttle: %d secs" \
        % (main_pid, throttle_secs)
    logger.info(msg)
    print("%s %s" % (datetime.datetime.now(), msg))

    throttle = False
    while not check_stop():
        try:
            if throttle:
                interruptible_sleep(configuration, throttle_secs,
                                    (check_run, check_stop))
                reset_run()
            if check_stop():
                break
            t1 = time.time()
            status = update_quota(configuration)
            t2 = time.time()
            msg = "(%s) Updated quota in %d secs with status: %s" \
                % (os.getpid(), int(t2-t1), status)
            logger.info(msg)
            print("%s %s" % (datetime.datetime.now(), msg))
            throttle = True
        except KeyboardInterrupt:
            stop_running()
            # NOTE: we can't be sure if SIGINT was sent to only main process
            #       so we make sure to propagate to monitor child
            msg = "(%s) Interrupt requested - shutdown" \
                % os.getpid()
            logger.info(msg)
            print("%s %s" % (datetime.datetime.now(), msg))
        except Exception:
            throttle = True
            msg = "(%s) Caught unexpected exception:\n%s" \
                  % (os.getpid(), traceback.format_exc())
            logger.error(msg)
            print("%s ERROR: %s"
                  % (datetime.datetime.now(), msg),
                  file=sys.stderr)

    msg = "(%s) Quota daemon shutting down" % main_pid
    logger.info(msg)
    print("%s %s" % (datetime.datetime.now(), msg))

    sys.exit(0)
