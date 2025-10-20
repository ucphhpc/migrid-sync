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

import os
import signal
import time

from tests.support import FakeConfiguration, MigTestCase

from mig.lib.daemon import _run_event, _stop_event, check_run, check_stop, \
    do_run, reset_run, reset_stop, stop_running, interruptible_sleep, \
    register_run_handler, register_stop_handler, run_handler, stop_handler


class MigLibDaemon(MigTestCase):
    """Unit tests for daemon related helper functions"""

    def before_each(self):
        """Set up test configuration and reset state before each test"""

        # Create fake configuration, sig and frame for test isolation
        self.dummy_conf = FakeConfiguration()
        self.sig = None
        self.frame = None

        # Reset event states
        reset_run()
        reset_stop()

    def test_register_run_handler_manual(self):
        """Register a run handler and verify it can be manually overriden to
        mark early run.
        """
        # It's easier to test with alarm than the usual interrupt signal
        register_run_handler(self.dummy_conf, run_signal=signal.SIGALRM)
        self.assertFalse(check_run())
        signal.alarm(3)
        time.sleep(1)
        do_run()
        self.assertTrue(check_run())

    def test_register_run_handler_signal(self):
        """Register a run handler and verify it can be used to trigger run"""
        # It's easier to test with alarm than the usual interrupt signal
        register_run_handler(self.dummy_conf, run_signal=signal.SIGALRM)
        self.assertFalse(check_run())
        signal.alarm(1)
        time.sleep(1)
        self.assertTrue(check_run())

    def test_interruptible_sleep(self):
        """Register a run handler and verify it can be used for interruptible
        sleep to let daemon be responsive when needed.
        """
        # It's easier to test with alarm than the usual interrupt signal
        register_run_handler(self.dummy_conf, run_signal=signal.SIGALRM)
        self.assertFalse(check_run())
        max_secs = 4.2
        start = time.time()
        signal.alarm(1)
        interruptible_sleep(self.dummy_conf, max_secs, (check_run, ))
        self.assertTrue(check_run())
        end = time.time()
        self.assertTrue(end < start + max_secs)

    def test_register_stop_handler_manual(self):
        """Register a stop handler and verify it can be manually overriden to
        mark early stop.
        """
        # It's easier to test with alarm than the usual interrupt signal
        register_stop_handler(self.dummy_conf, stop_signal=signal.SIGALRM)
        self.assertFalse(check_stop())
        signal.alarm(3)
        time.sleep(1)
        stop_running()
        self.assertTrue(check_stop())

    def test_register_stop_handler_signal(self):
        """Register a stop handler and verify it can be used to mark stop upon
        receiving the signal registered.
        """
        # It's easier to test with alarm than the usual interrupt signal
        register_stop_handler(self.dummy_conf, stop_signal=signal.SIGALRM)
        self.assertFalse(check_stop())
        signal.alarm(1)
        time.sleep(1)
        self.assertTrue(check_stop())

    def test_low_level_event_helpers(self):
        """Test basic event control helpers"""
        # Initial state
        self.assertFalse(check_run())
        self.assertFalse(check_stop())

        # Test manual run control
        do_run()
        self.assertTrue(check_run())
        reset_run()
        self.assertFalse(check_run())

        # Test manual stop control
        stop_running()
        self.assertTrue(check_stop())
        reset_stop()
        self.assertFalse(check_stop())

    def test_run_handler_direct(self):
        """Test run handler directly without signals"""
        self.assertFalse(check_run())
        run_handler(self.sig, self.frame)
        self.assertTrue(check_run())
        # Verify repeated triggering
        run_handler(self.sig, self.frame)
        self.assertTrue(check_run())

    def test_stop_handler_direct(self):
        """Test stop handler directly without signals"""
        self.assertFalse(check_stop())
        stop_handler(self.sig, self.frame)
        self.assertTrue(check_stop())
        # Verify repeated triggering
        stop_handler(self.sig, self.frame)
        self.assertTrue(check_stop())

    def test_interruptible_sleep_edge_cases(self):
        """Test interruptible_sleep with edge case parameters"""
        # Should complete instantly since max_secs == nap_secs
        start = time.time()
        interruptible_sleep(self.dummy_conf, 0.01, [], nap_secs=0.05)
        self.assertTrue(time.time() - start < 0.05)

        # Test zero max_secs
        interruptible_sleep(self.dummy_conf, 0.0, [])
        interruptible_sleep(self.dummy_conf, -1.0, [])

    def test_interruptible_sleep_multiple_conditions(self):
        """Test interruptible_sleep with multiple break conditions"""
        conditions = [
            lambda: False,
            lambda: False,
            lambda: True,  # This triggers break
        ]
        start = time.time()
        interruptible_sleep(self.dummy_conf, 5.0, conditions)
        self.assertTrue(time.time() - start < 0.2)

    def test_handler_registration_conflict(self):
        """Test registering handlers with conflicting signals"""
        # First register USR1 for both handlers
        register_run_handler(self.dummy_conf, signal.SIGUSR1)
        register_stop_handler(self.dummy_conf, signal.SIGUSR1)

        # Should still work
        signal.alarm(1)
        time.sleep(0.5)
        register_run_handler(self.dummy_conf, signal.SIGUSR2)
        register_stop_handler(self.dummy_conf, signal.SIGUSR2)

    def test_concurrent_event_handling(self):
        """Test concurrent event triggers and state maintenance"""
        # Setup both handlers
        self.assertFalse(check_run())
        self.assertFalse(check_stop())
        register_run_handler(self.dummy_conf, signal.SIGCONT)
        register_stop_handler(self.dummy_conf, signal.SIGINT)
        os.kill(os.getpid(), signal.SIGCONT)
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(0.3)
        self.assertTrue(check_run())
        self.assertTrue(check_stop())

        # Verify safe reset
        reset_run()
        reset_stop()
        self.assertFalse(check_run())
        self.assertFalse(check_stop())

    def test_interruptible_sleep_immediate_break(self):
        """Test interruptible_sleep with immediate break condition"""
        def immediate_true():
            return True

        start = time.time()
        interruptible_sleep(self.dummy_conf, 5.0, [immediate_true])
        duration = time.time() - start
        self.assertTrue(duration < 0.1,
                        "Sleep should exit immediately but took %s" % duration)

    def test_reset_event_helpers(self):
        """Test simple event reset helpers"""
        # Manually set events
        _run_event.set()
        _stop_event.set()
        self.assertTrue(check_run())
        self.assertTrue(check_stop())

        reset_run()
        reset_stop()
        self.assertFalse(check_run())
        self.assertFalse(check_stop())

    def test_invalid_nap_secs(self):
        """Test invalid nap_secs parameter"""
        with self.assertRaises(AssertionError):
            interruptible_sleep(self.dummy_conf, 0.5, [], nap_secs=-1.0)

    def test_event_state_persistence(self):
        """Test event states persist across multiple checks"""
        do_run()
        self.assertTrue(check_run())
        # Repeated checks should maintain state
        self.assertTrue(check_run())

        stop_running()
        self.assertTrue(check_stop())
        self.assertTrue(check_stop())

    def test_signal_handler_dispatch(self):
        """Verify signal handlers dispatch correct signals"""
        test_signals = {
            'run': [signal.SIGUSR1],
            'stop': [signal.SIGUSR2]
        }

        for func, sigs in [(register_run_handler, test_signals['run']),
                           (register_stop_handler, test_signals['stop'])]:
            for sig in sigs:
                func(self.dummy_conf, sig)
                # Verify handler registration
                dispatch = signal.getsignal(sig)
                if func == register_run_handler:
                    self.assertEqual(dispatch.__name__, 'run_handler')
                else:
                    self.assertEqual(dispatch.__name__, 'stop_handler')

    def test_event_set_unset_lifecycle(self):
        """Verify full event lifecycle"""
        for func in (do_run, stop_running):
            func()
            if func == do_run:
                self.assertTrue(check_run())
                reset_run()
                self.assertFalse(check_run())
            else:
                self.assertTrue(check_stop())
                reset_stop()
                self.assertFalse(check_stop())

    def test_multiple_reset_cycles(self):
        """Test running multiple reset/manipulation cycles"""
        for _ in range(5):
            # Run through full event lifecycle
            self.assertFalse(check_run())
            do_run()
            self.assertTrue(check_run())
            reset_run()
            self.assertFalse(check_run())

            self.assertFalse(check_stop())
            stop_running()
            self.assertTrue(check_stop())
            reset_stop()
            self.assertFalse(check_stop())

    def test_interruptible_sleep_nap_accuracy(self):
        """Verify nap timing accuracy in sleep function"""
        start = time.time()
        interruptible_sleep(self.dummy_conf, 0.3, [], nap_secs=0.1)
        duration = time.time() - start
        # Should be ~0.3 secs +/- 0.1 tolerance
        self.assertAlmostEqual(duration, 0.3, delta=0.1)

    def test_interruptible_sleep_no_break_conditions(self):
        """Test sleep with no break conditions"""
        start = time.time()
        interruptible_sleep(self.dummy_conf, 0.2, [])
        duration = time.time() - start
        self.assertAlmostEqual(duration, 0.2, delta=0.05)

    def test_interruptible_sleep_invalid_break_conditions(self):
        """Test sleep with improperly formatted break conditions"""
        with self.assertRaises(TypeError):
            interruptible_sleep(self.dummy_conf, 0.2, [None])
