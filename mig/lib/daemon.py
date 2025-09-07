#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# daemons - helpers to support various service daemons e.g. in signal handling
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

"""Helpers used by service daemons e.g. to react to signals"""

import multiprocessing
import signal

_stop_event = multiprocessing.Event()


def stop_running():
    """A simple helper to set stop marker after some signal was received"""
    return _stop_event.set()


def check_stop():
    """A simple test to see if stop marker was set after some signal was received"""
    return _stop_event.is_set()


def stop_handler(sig, frame):
    """A simple signal handler to help quit on interrupt signal in main"""
    # Print blank line to avoid mix with Ctrl-C line
    print("")
    stop_running()


def register_stop_handler(configuration, stop_signal=signal.SIGINT):
    """Set up stop handler to react on provided stop_signal"""
    signal.signal(stop_signal, stop_handler)
