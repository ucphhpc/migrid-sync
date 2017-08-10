#!/usr/bin/python -u
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# chkuserroot - Simple Apache httpd user chroot helper daemon
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

# NOTE: we request unbuffered I/O with the she-bang at the top in line with:
#       http://httpd.apache.org/docs/current/rewrite/rewritemap.html#prg

"""Simple user chroot helper daemon to verify that paths are limited to valid
chroot locations. Reads a path from stdin and prints either invalid marker or
actual real path to stdout so that apache can use the daemon from RewriteMap
and rewrite to fail or success depending on output.
"""

import os
import signal
import sys
import time

from shared.conf import get_configuration_object
from shared.logger import daemon_logger, reopen_log
from shared.validstring import valid_user_path

configuration, logger = None, None

# Constant value to mark a failed chroot verification.
# Please keep in sync with rewrite in apache MiG conf.

INVALID_MARKER = "_OUT_OF_BOUNDS_"

def hangup_handler(signal, frame):
    """A simple signal handler to force log reopening on SIGHUP"""
    logger.info("reopening log in reaction to hangup signal")
    reopen_log(configuration)
    logger.info("reopened log after hangup signal")

if __name__ == '__main__':
    configuration = get_configuration_object()
    verbose = False
    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]
        verbose = True

    if verbose:
        print os.environ.get('MIG_CONF', 'DEFAULT'), configuration.server_fqdn

    # Use separate logger
    logger = daemon_logger("chkuserroot", configuration.user_chkuserroot_log,
                           log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    signal.signal(signal.SIGHUP, hangup_handler)

    if verbose:
        print '''This is simple user chroot check helper daemon which just
prints the real path for all allowed path requests and the invalid marker for
illegal ones.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
'''
        print 'Starting chkuserroot helper daemon - Ctrl-C to quit'

    # NOTE: we use sys stdin directly
    
    chkuserroot_stdin = sys.stdin

    keep_running = True
    if verbose:
        print 'Reading commands from sys stdin'
    while keep_running:
        try:
            line = chkuserroot_stdin.readline()
            path = line.strip()
            logger.info("chkuserroot got path: %s" % path)
            if not os.path.isabs(path):
                logger.error("not an absolute path: %s" % path)
                print INVALID_MARKER
                continue
            # NOTE: extract home dir before ANY expansion to avoid escape
            #       with e.g. /PATH/TO/OWNUSER/../OTHERUSER/somefile.txt
            root = configuration.user_home.rstrip(os.sep) + os.sep
            if not path.startswith(root):
                logger.error("got path with invalid root: %s" % path)
                print INVALID_MARKER
                continue
            # Extract name of home as first component after root base
            home_dir = path.replace(root, "").lstrip(os.sep)
            home_dir = home_dir.split(os.sep, 1)[0]
            logger.debug("found home dir: %s" % home_dir)
            # No need to expand home_path here - done in valid_user_path
            home_path = os.path.join(root, home_dir) + os.sep
            abs_path = os.path.abspath(path)
            # Make sure absolute but unexpanded path is inside home_path
            if not abs_path.startswith(root):
                logger.error("got path outside user home: %s" % abs_path)
                print INVALID_MARKER
                continue
            logger.debug("check path %s in home %s or chroot" % (abs_path,
                                                                 home_path))
            # Exact match to user home does not make sense as we expect a file
            if not valid_user_path(configuration, abs_path, home_path,
                                   allow_equal=False, apache_scripts=True):
                logger.error("path outside user chroot: %s" % abs_path)
                print INVALID_MARKER
                continue
            logger.info("found valid user chroot path: %s" % abs_path)
            print abs_path

            # Throttle down a bit to yield

            time.sleep(0.01)
        except KeyboardInterrupt:
            keep_running = False
        except Exception, exc:
            logger.error("unexpected exception: %s" % exc)
            if verbose:
                print 'Caught unexpected exception: %s' % exc

    if verbose:
        print 'chkuserroot helper daemon shutting down'
    sys.exit(0)
