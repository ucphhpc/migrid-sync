# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_daemon - unit test of the corresponding mig lib module
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
# --- END_HEADER ---
#

"""Unit tests for the migrid module pointed to in the filename"""

import signal
import time

from tests.support import MigTestCase

from mig.lib.daemon import check_run, check_stop, do_run, interruptible_sleep, \
    register_run_handler, register_stop_handler, stop_running


class MigLibDaemon(MigTestCase):
    """Unit tests for daemon related helper functions"""

    def test_register_run_handler_manual(self):
        """Register a run handler and verify it can be manually overriden to
        mark early run.
        """

        # We don't actually need a configuration here so just pass None
        configuration = None
        # It's easier to test with alarm than the usual interrupt signal
        register_run_handler(configuration, run_signal=signal.SIGALRM)
        self.assertFalse(check_run())
        signal.alarm(3)
        time.sleep(1)
        do_run()
        self.assertTrue(check_run())

    def test_register_run_handler_signal(self):
        """Register a run handler and verify it can be used to trigger run"""

        # We don't actually need a configuration here so just pass None
        configuration = None
        # It's easier to test with alarm than the usual interrupt signal
        register_run_handler(configuration, run_signal=signal.SIGALRM)
        self.assertFalse(check_run())
        signal.alarm(1)
        time.sleep(1)
        self.assertTrue(check_run())

    def test_interruptible_sleep(self):
        """Register a run handler and verify it can be used for interruptible
        sleep to let daemon be responsive when needed.
        """

        # We don't actually need a configuration here so just pass None
        configuration = None
        # It's easier to test with alarm than the usual interrupt signal
        register_run_handler(configuration, run_signal=signal.SIGALRM)
        self.assertFalse(check_run())
        max_secs = 4.2
        start = time.time()
        signal.alarm(1)
        interruptible_sleep(configuration, max_secs, (check_run, ))
        self.assertTrue(check_run())
        end = time.time()
        self.assertTrue(end < start + max_secs)

    def test_register_stop_handler_manual(self):
        """Register a stop handler and verify it can be manually overriden to
        mark early stop.
        """

        # We don't actually need a configuration here so just pass None
        configuration = None
        # It's easier to test with alarm than the usual interrupt signal
        register_stop_handler(configuration, stop_signal=signal.SIGALRM)
        self.assertFalse(check_stop())
        signal.alarm(3)
        time.sleep(1)
        stop_running()
        self.assertTrue(check_stop())

    def test_register_stop_handler_signal(self):
        """Register a stop handler and verify it can be used to mark stop upon
        receiving the signal registered.
        """

        # We don't actually need a configuration here so just pass None
        configuration = None
        # It's easier to test with alarm than the usual interrupt signal
        register_stop_handler(configuration, stop_signal=signal.SIGALRM)
        self.assertFalse(check_stop())
        signal.alarm(1)
        time.sleep(1)
        self.assertTrue(check_stop())
