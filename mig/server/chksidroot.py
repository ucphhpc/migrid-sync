#!/usr/bin/python -u
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# chksidroot - Simple Apache httpd SID chroot helper daemon
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

"""Simple SID chroot helper daemon to verify that paths are limited to valid
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
from shared.sharelinks import extract_mode_id
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
    logger = daemon_logger("chksidroot", configuration.user_chksidroot_log,
                           log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    signal.signal(signal.SIGHUP, hangup_handler)

    if verbose:
        print '''This is simple SID chroot check helper daemon which just
prints the real path for all allowed path requests and the invalid marker for
illegal ones.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
'''
        print 'Starting chksidroot helper daemon - Ctrl-C to quit'

    # NOTE: we use sys stdin directly
    
    chksidroot_stdin = sys.stdin

    keep_running = True
    if verbose:
        print 'Reading commands from sys stdin'
    while keep_running:
        try:
            line = chksidroot_stdin.readline()
            path = line.strip()
            logger.info("chksidroot got path: %s" % path)
            if not os.path.isabs(path):
                logger.error("not an absolute path: %s" % path)
                print INVALID_MARKER
                continue
            # NOTE: extract sid dir before ANY expansion to avoid escape
            #       with e.g. /PATH/TO/OWNID/../OTHERID/somefile.txt
            # Where sid may be share link or session link id.
            doc_root = configuration.webserver_home
            sharelink_prefix = os.path.join(doc_root, 'share_redirect')
            session_prefix = os.path.join(doc_root, 'sid_redirect')
            is_sharelink = False
            # Make sure absolute but unexpanded path is inside sid dir
            if path.startswith(sharelink_prefix):
                # Build proper root base terminated with a single slash
                root = sharelink_prefix.rstrip(os.sep) + os.sep
                is_sharelink = True
            elif path.startswith(session_prefix):
                # Build proper root base terminated with a single slash
                root = session_prefix.rstrip(os.sep) + os.sep
            else:
                logger.error("got path with invalid root: %s" % path)
                print INVALID_MARKER
                continue
            # Extract sid as first component after root base
            sid_dir = path.replace(root, "").lstrip(os.sep)
            sid_dir = sid_dir.split(os.sep, 1)[0]
            logger.debug("found sid dir: %s" % sid_dir)
            if is_sharelink:
                (access_dir, _) = extract_mode_id(configuration, sid_dir)
                real_root = os.path.join(configuration.sharelink_home,
                                    access_dir) + os.sep
                path = path.replace(root, real_root, 1)
            else:
                real_root = root
            # Expand sid_path to proper base dir here
            sid_path = os.path.join(real_root, sid_dir)
            sid_path = os.path.realpath(sid_path) + os.sep
            abs_path = os.path.realpath(path)
            logger.debug("check path %s in sid %s or chroot" % (abs_path,
                                                                sid_path))
            # Exact match to sid dir does not make sense as we expect a file
            if not valid_user_path(configuration, abs_path, sid_path,
                                   allow_equal=False, apache_scripts=True):
                logger.error("path outside sid chroot: %s" % abs_path)
                print INVALID_MARKER
                continue
            logger.info("found valid sid chroot path: %s" % abs_path)
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
        print 'chksidroot helper daemon shutting down'
    sys.exit(0)
