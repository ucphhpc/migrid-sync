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
            raw_path = path = line.strip()
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
            # Extract sid name as first component after root base
            sid_name = path.replace(root, "").lstrip(os.sep)
            sid_name = sid_name.split(os.sep, 1)[0]
            logger.debug("found sid dir: %s" % sid_name)
            # Save full prefix of link path
            full_prefix = os.path.join(root, sid_name)
            # Make sure absolute/normalized but unexpanded path is inside base.
            # Only prevents path itself outside base - not illegal linking
            # outside base, which is checked later.
            path = os.path.abspath(path)
            if not path.startswith(full_prefix):
                logger.error("got path outside sid base: %s" % path)
                print INVALID_MARKER
                continue
            is_file = False
            if is_sharelink:
                # Share links use Alias to map directly into sharelink_home
                # and with first char mapping into access mode sub-dir there.
                (access_dir, _) = extract_mode_id(configuration, sid_name)
                real_root = os.path.join(configuration.sharelink_home,
                                    access_dir) + os.sep
                # Share links always point to a path in user home of owner.
                # We expand with readlink to only follow link there and extract
                # real user home for use as real root.
                link_path = os.path.join(real_root, sid_name)
                try:
                    link_target = os.readlink(link_path).rstrip(os.sep)
                    real_target = os.path.realpath(link_path)
                except Exception, exc:
                    link_target = None
                    real_target = None
                if link_target and os.path.exists(link_target) and \
                       link_target.startswith(configuration.user_home):
                    user_dir = link_target.replace(configuration.user_home, '')
                    user_dir = user_dir.lstrip(os.sep).split(os.sep)[0]
                    base_path = os.path.join(configuration.user_home, user_dir)
                    # NOTE: we cannot completely trust linked path to be safe,
                    # so we use user home and normpath as default to avoid user
                    # escaping sharelink base with e.g. SHAREID/../bla . We
                    # only expand to actual sharelink dir if it is inside user
                    # home.
                    if real_target and real_target.startswith(base_path):
                        is_file = not os.path.isdir(real_target)
                        base_path = real_target
                else:
                    logger.error("got invalid share link path: %s (%s)" % \
                                 (path, link_target))
                    print INVALID_MARKER
                    continue

                # We manually expand sid base.
                logger.debug("found target %s for link %s" % (link_target,
                                                              link_path))
                # Single file sharelinks use direct link to file. If so we
                # manually expand to direct target. Otherwise we only replace
                # that prefix of path to translate it to a sharelink dir path.
                if is_file:
                    logger.debug("found single file sharelink: %s" % path)
                    path = link_target
                else:
                    logger.debug("found directory sharelink: %s" % path)
                    path = path.replace(full_prefix, link_target, 1)
            else:
                # Session links are directly in webserver_home and they map
                # either into mig_system_files for empty jobs or into specific
                # user_home for real job input/output.
                # First re-map X_redirect in path like apache Aliases do.
                real_root = configuration.webserver_home.rstrip(os.sep) + \
                            os.sep
                path = path.replace(root, real_root, 1)

                # Now lookup the helper dir using either sid_name directly if it
                # is a dir link or with extension stripped if it is a file link
                # like e.g. SID.job or SID.sendoutputfiles .
                # We manually expand sid base.
                helper_dir, _ = os.path.splitext(os.path.join(real_root,
                                                              sid_name))
                real_helper = os.path.realpath(helper_dir)
                logger.debug("found real helper path: %s" % real_helper)
                if os.path.dirname(path) == configuration.webserver_home.rstrip(os.sep):
                    base_path = configuration.mig_system_files.rstrip(os.sep)
                elif real_helper.startswith(configuration.user_home):
                    user_dir = real_helper.replace(configuration.user_home, '')
                    user_dir = user_dir.lstrip(os.sep).split(os.sep)[0]
                    base_path = os.path.join(configuration.user_home, user_dir)
                else:
                    logger.error("got session path with invalid root: %s" % path)
                    print INVALID_MARKER
                    continue

            real_path = os.path.realpath(path)
            logger.debug("check path %s in base %s or chroot" % (path,
                                                                base_path))
            # Exact match to sid dir does not make sense as we expect a file
            # IMPORTANT: use path and not real_path here in order to test both
            if not valid_user_path(configuration, path, base_path,
                                   allow_equal=is_file, apache_scripts=True):
                logger.error("real path outside sid chroot: %s" % real_path)
                print INVALID_MARKER
                continue
            logger.info("found valid sid chroot path: %s" % real_path)
            print real_path

            # Throttle down a bit to yield

            time.sleep(0.01)
        except KeyboardInterrupt:
            keep_running = False
        except Exception, exc:
            logger.error("unexpected exception: %s" % exc)
            print INVALID_MARKER
            if verbose:
                print 'Caught unexpected exception: %s' % exc

    if verbose:
        print 'chksidroot helper daemon shutting down'
    sys.exit(0)
