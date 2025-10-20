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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#

"""Helpers used by service daemons e.g. to react to signals"""

import multiprocessing
import signal
import time

_run_event, _stop_event = multiprocessing.Event(), multiprocessing.Event()


def _reset_event(evt):
    """A simple helper to reset evt marker after it was set"""
    return evt.clear()


def reset_run():
    """A simple helper to reset run marker after it was set"""
    return _reset_event(_run_event)


def do_run():
    """A simple helper to set run marker after some signal was received"""
    return _run_event.set()


def check_run():
    """A simple test to see if run marker was set after some signal was
    received.
    """
    return _run_event.is_set()


def run_handler(sig, frame):
    """A simple signal handler to trigger run on continue signal in main"""
    do_run()


def register_run_handler(configuration, run_signal=signal.SIGCONT):
    """Set up run next handler to react on provided run_signal"""
    reset_run()
    signal.signal(run_signal, run_handler)


def unregister_signal_handlers(configuration, target_signals=None):
    """Remove any handlers registered to react on provided target_signals list.
    Default to SIGCONT, SIGUSR1 and SIGUSR2 if target_signals is left to None.
    """
    if target_signals is None:
        target_signals = [signal.SIGCONT, signal.SIGUSR1, signal.SIGUSR2]
    for target in target_signals:
        original_handler = signal.getsignal(target)
        if original_handler:
            signal.signal(target, signal.SIG_IGN)


def interruptible_sleep(configuration, max_secs, break_checks, nap_secs=0.1):
    """Idle loop for max_secs or until one or more break_checks succeed"""
    assert nap_secs > 0.0, "Invalid non-positive nap_secs value"
    if max_secs < nap_secs:
        return
    for _ in range(int(max_secs / nap_secs)):
        for check in break_checks:
            if check():
                return
        time.sleep(nap_secs)


def reset_stop():
    """A simple helper to reset stop marker after it was set"""
    return _reset_event(_stop_event)


def stop_running():
    """A simple helper to set stop marker after some signal was received"""
    return _stop_event.set()


def check_stop():
    """A simple test to see if stop marker was set after some signal was
    received.
    """
    return _stop_event.is_set()


def stop_handler(sig, frame):
    """A simple signal handler to help quit on interrupt signal in main"""
    # Print blank line to avoid mix with Ctrl-C line
    print("")
    stop_running()


def register_stop_handler(configuration, stop_signal=signal.SIGINT):
    """Set up stop handler to react on provided stop_signal"""
    reset_stop()
    signal.signal(stop_signal, stop_handler)
