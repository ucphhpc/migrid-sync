#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# breakpoint - Python GDB breakpoint
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Python GNU debugger (GDB) breakpoint
https://devguide.python.org/gdb/
https://wiki.python.org/moin/DebuggingWithGdb
https://sourceware.org/gdb/onlinedocs/gdb/Python-API.html

USAGE:
import pygdb.breakpoint
pygdb.breakpoint.enable()
pygdb.breakpoint.set()

This will block the executing thread (at the pygdb.breakpoint.set() call)
until 'pygdb.console.extension.console_connected' is called
from the gdb console.
"""

import os
import time
import threading
import _pygdb

try:
    from shared.conf import get_configuration_object
    from shared.logger import daemon_logger
except:
    print "pygdb.breakpoint: Missing MiG shared.logger, using stdout"

enabled = False
configuration = None
console_connected = None
breakpoint_lock = None


def enable():
    """Enable breakpoint"""
    global enabled
    global configuration
    global console_connected
    global breakpoint_lock

    enabled = True
    console_connected = False
    breakpoint_lock = threading.Lock()

    try:
        configuration = get_configuration_object(skip_log=True)
        logpath = os.path.join(configuration.log_dir, "gdb.log")
        configuration.gdb_logger = daemon_logger(
            "gdb",
            level=configuration.loglevel,
            path=logpath)
    except:
        pass

    gdb_logger("Init gdb main thread")


def gdb_logger_debug(msg):
    """log debug messages"""
    if not enabled:
        return

    gdb_logger(msg, debug=True)


def gdb_logger(msg, debug=False):
    """log info messages"""
    if not enabled:
        return

    pid = os.getpid()
    tid = threading.current_thread().ident
    log_msg = "(PID: %d, TID: 0x%0.x): %s" \
        % (pid, tid, msg)
    if configuration:
        logger = configuration.gdb_logger
        if debug:
            logger.debug(log_msg)
        else:
            logger.info(log_msg)
    else:
        if debug:
            log_msg = "DEBUG: %s" % log_msg
        print log_msg


def set():
    """Used to set breakpoint, busy-wait until gdb console is connected"""
    if not enabled:
        return
    global console_connected

    # Wait for gdb console
    breakpoint_lock.acquire()
    while not console_connected:
        gdb_logger_debug("breakpoint.set: waiting for gdb console")
        breakpoint_lock.release()
        time.sleep(1)
        breakpoint_lock.acquire()
    breakpoint_lock.release()

    # Set breakpoint mark for GDB
    gdb_logger_debug("breakpoint.set: breakpoint_mark")
    _pygdb.breakpoint_mark()


def set_console_connected():
    """NOTE: This function should only be called from the GNU Debugger (GDB)
    while execution is in 'interruption mode'.
    Therefore applying locks is not needed and might cause deadlocks
    in the GNU Debugger helper functions"""
    global console_connected
    console_connected = True
