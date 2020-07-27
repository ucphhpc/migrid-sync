#!/usr/bin/python -u
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# chkuserroot - Simple Apache httpd user chroot helper daemon
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

# NOTE: we request unbuffered I/O with the she-bang at the top in line with:
#       http://httpd.apache.org/docs/current/rewrite/rewritemap.html#prg

"""Simple user chroot helper daemon to verify that paths are limited to valid
chroot locations. Reads a path from stdin and prints either invalid marker or
actual real path to stdout so that apache can use the daemon from RewriteMap
and rewrite to fail or success depending on output.
"""
from __future__ import print_function

import os
import re
import sys
import time

from shared.accountstate import check_account_accessible
from shared.base import client_dir_id
from shared.conf import get_configuration_object
from shared.logger import daemon_logger, register_hangup_handler
from shared.validstring import valid_user_path

configuration, logger = None, None

# Constant value to mark a failed chroot verification.
# Please keep in sync with rewrite in apache MiG conf.

INVALID_MARKER = "_OUT_OF_BOUNDS_"

if __name__ == '__main__':
    configuration = get_configuration_object()
    verbose = False
    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]
        verbose = True

    if verbose:
        print(os.environ.get('MIG_CONF', 'DEFAULT'), configuration.server_fqdn)

    # Use separate logger
    logger = daemon_logger("chkuserroot", configuration.user_chkuserroot_log,
                           log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    if verbose:
        print('''This is simple user chroot check helper daemon which just
prints the real path for all allowed path requests and the invalid marker for
illegal ones.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
''')
        print('Starting chkuserroot helper daemon - Ctrl-C to quit')

    # NOTE: we use sys stdin directly

    chkuserroot_stdin = sys.stdin

    addr_path_pattern = re.compile(
        "^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})::(/.*)$")
    keep_running = True
    if verbose:
        print('Reading commands from sys stdin')
    while keep_running:
        try:
            client_ip = "UNKNOWN"
            line = chkuserroot_stdin.readline()
            raw_line = raw_path = path = line.strip()
            # New line format is ${CLIENT_IP}::${PATH}
            # try to parse and update client_ip and path
            match = addr_path_pattern.match(raw_line)
            if match:
                client_ip = match.group(1)
                raw_path = path = match.group(2)
            logger.info("chkuserroot from %s got path: %s" % (client_ip, path))
            if not os.path.isabs(path):
                logger.error("not an absolute path from %s: %s" %
                             (client_ip, path))
                print(INVALID_MARKER)
                continue
            # NOTE: extract home dir before ANY expansion to avoid escape
            #       with e.g. /PATH/TO/OWNUSER/../OTHERUSER/somefile.txt
            root = configuration.user_home.rstrip(os.sep) + os.sep
            if not path.startswith(root):
                logger.error("got path from %s with invalid root: %s" %
                             (client_ip, path))
                print(INVALID_MARKER)
                continue
            # Extract name of home as first component after root base
            home_dir = path.replace(root, "").lstrip(os.sep)
            home_dir = home_dir.split(os.sep, 1)[0]
            logger.debug("found home dir: %s" % home_dir)
            user_id = client_dir_id(home_dir)
            # No need to expand home_path here - done in valid_user_path
            home_path = os.path.join(root, home_dir) + os.sep
            # Make sure absolute/normalized but unexpanded path is inside home.
            # Only prevents path itself outside home - not illegal linking
            # outside home, which is checked later.
            path = os.path.abspath(path)
            if not path.startswith(home_path):
                logger.error("got path from %s outside user home: %s" %
                             (client_ip, raw_path))
                print(INVALID_MARKER)
                continue

            real_path = os.path.realpath(path)
            logger.debug("check path %s in home %s or chroot" % (path,
                                                                 home_path))
            # Exact match to user home does not make sense as we expect a file
            # IMPORTANT: use path and not real_path here in order to test both
            if not valid_user_path(configuration, path, home_path,
                                   allow_equal=False, apache_scripts=True):
                logger.error("path from %s outside user chroot %s: %s (%s)" %
                             (client_ip, home_path, raw_path, real_path))
                print(INVALID_MARKER)
                continue
            elif not check_account_accessible(configuration, user_id, 'https'):
                logger.error("path from %s in inaccessible %s account: %s (%s)"
                             % (client_ip, user_id, raw_path, real_path))
                print(INVALID_MARKER)
                continue

            logger.info("found valid user chroot path from %s: %s" %
                        (client_ip, real_path))
            print(real_path)

            # Throttle down a bit to yield

            time.sleep(0.01)
        except KeyboardInterrupt:
            keep_running = False
        except Exception as exc:
            logger.error("unexpected exception: %s" % exc)
            print(INVALID_MARKER)
            if verbose:
                print('Caught unexpected exception: %s' % exc)

    if verbose:
        print('chkuserroot helper daemon shutting down')
    sys.exit(0)
