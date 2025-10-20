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

from mig.lib.daemon import _run_event, _stop_event, check_run, check_stop, \
    do_run, interruptible_sleep, register_run_handler, register_stop_handler, \
    reset_run, reset_stop, run_handler, stop_handler, stop_running, \
    unregister_signal_handlers
from tests.support import FakeConfiguration, FakeLogger, MigTestCase


class MigLibDaemon(MigTestCase):
    """Unit tests for daemon related helper functions"""

    def before_each(self):
        """Set up test configuration and reset state before each test"""

        # Create fake configuration, sig and frame for test isolation
        self.dummy_conf = FakeConfiguration()
        self.dummy_conf.logger = FakeLogger()
        self.sig = None
        self.frame = None

        # Reset event states
        reset_run()
        reset_stop()

        # Unregister any existing signal handlers
        used_signals = [signal.SIGCONT, signal.SIGINT, signal.SIGALRM,
                        signal.SIGABRT, signal.SIGUSR1, signal.SIGUSR2]
        unregister_signal_handlers(self.dummy_conf, used_signals)

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

    def test_interruptible_sleep_immediate_exit(self):
        """Test interruptible_sleep with max_secs < nap_secs"""
        start = time.time()
        interruptible_sleep(self.dummy_conf, 0.1, [], nap_secs=0.2)
        duration = time.time() - start
        self.assertTrue(duration < 0.15)

    def test_interruptible_sleep_positional_args(self):
        """Test interruptible_sleep works without named arguments"""
        start = time.time()
        interruptible_sleep(None, 0.1, [lambda: False])
        duration = time.time() - start
        self.assertAlmostEqual(duration, 0.1, delta=0.15)

    def test_interruptible_sleep_negative_max_secs(self):
        """Test interruptible_sleep with negative max_secs"""
        start = time.time()
        interruptible_sleep(self.dummy_conf, -1.0, [])
        duration = time.time() - start
        self.assertTrue(duration < 0.1)

    def test_interruptible_sleep_zero_max_secs(self):
        """Test interruptible_sleep with zero max_secs"""
        start = time.time()
        interruptible_sleep(self.dummy_conf, 0.0, [])
        duration = time.time() - start
        self.assertTrue(duration < 0.1)

    def test_handler_unregistered_signals(self):
        """Test event handlers don't fire for unregistered signals"""
        # Verify default signal handlers
        original_cont = signal.getsignal(signal.SIGCONT)
        original_int = signal.getsignal(signal.SIGINT)

        os.kill(os.getpid(), signal.SIGCONT)
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(0.1)

        self.assertFalse(check_run())
        self.assertFalse(check_stop())

        # Restore original handlers to avoid test pollution, even if not needed
        signal.signal(signal.SIGCONT, original_cont)
        signal.signal(signal.SIGINT, original_int)

    def test_consecutive_signal_handling(self):
        """Test back-to-back signal handling"""
        register_run_handler(self.dummy_conf, signal.SIGUSR1)
        register_stop_handler(self.dummy_conf, signal.SIGUSR2)

        # First signal pair
        os.kill(os.getpid(), signal.SIGUSR1)
        os.kill(os.getpid(), signal.SIGUSR2)
        time.sleep(0.2)
        self.assertTrue(check_run())
        self.assertTrue(check_stop())
        reset_run()
        reset_stop()

        # Second signal pair
        os.kill(os.getpid(), signal.SIGUSR1)
        os.kill(os.getpid(), signal.SIGUSR2)
        time.sleep(0.2)
        self.assertTrue(check_run())
        self.assertTrue(check_stop())

    def test_interruptible_sleep_edge_cases(self):
        """Test interruptible_sleep with edge case parameters"""
        # Should complete instantly since max_secs < nap_secs
        start = time.time()
        interruptible_sleep(self.dummy_conf, 0.01, [], nap_secs=0.05)
        self.assertTrue(time.time() - start < 0.05)

        # Test zero and negative max_secs returns immediately
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

    def test_unregister_signal_handlers_explicit(self):
        """Test explicit unregistration of signal handlers"""
        # Register handlers first
        register_run_handler(self.dummy_conf, signal.SIGALRM)
        register_stop_handler(self.dummy_conf, signal.SIGABRT)

        # Verify handlers were set
        self.assertEqual(signal.getsignal(
            signal.SIGALRM).__name__, 'run_handler')
        self.assertEqual(signal.getsignal(
            signal.SIGABRT).__name__, 'stop_handler')

        # Unregister specific signals
        unregister_signal_handlers(
            self.dummy_conf, [signal.SIGALRM, signal.SIGABRT])
        self.assertEqual(signal.getsignal(signal.SIGALRM), signal.SIG_IGN)
        self.assertEqual(signal.getsignal(signal.SIGABRT), signal.SIG_IGN)

    def test_interruptible_sleep_condition_after_interval(self):
        """Test interruptible_sleep break condition after one interval"""
        state = {'count': 0}

        def counter_condition():
            state['count'] += 1
            return state['count'] >= 2

        start = time.time()
        interruptible_sleep(self.dummy_conf, 5.0, [
                            counter_condition], nap_secs=0.1)
        duration = time.time() - start
        self.assertAlmostEqual(duration, 0.2, delta=0.15)

    def test_interruptible_sleep_maxsecs_equals_napsecs(self):
        """Test interruptible_sleep with max_secs exactly matching nap_secs"""
        start = time.time()
        interruptible_sleep(self.dummy_conf, 0.1, [lambda: False],
                            nap_secs=0.1)
        duration = time.time() - start
        self.assertAlmostEqual(duration, 0.1, delta=0.05)

    def test_interruptible_sleep_break_func_exception(self):
        """Test interruptible_sleep handles break function exceptions"""

        SLEEP_ERR = "Sleep Test Error"

        def faulty_condition():
            self.dummy_conf.logger.error(SLEEP_ERR)

        start = time.time()
        interruptible_sleep(self.dummy_conf, 0.1, [faulty_condition],
                            nap_secs=0.01)
        duration = time.time() - start
        self.assertAlmostEqual(duration, 0.1, delta=0.05)
        try:
            self.dummy_conf.logger.check_empty_and_reset()
        except RuntimeError as rte:
            self.assertTrue(SLEEP_ERR in str(rte), "failed sleep break exc")

    def test_reset_run(self):
        """Test reset_run helper"""
        do_run()
        self.assertTrue(check_run())
        reset_run()
        self.assertFalse(check_run())

    def test_reset_stop(self):
        """Test reset_stop helper"""
        stop_running()
        self.assertTrue(check_stop())
        reset_stop()
        self.assertFalse(check_stop())

    def test_do_run(self):
        """Test explicit execution of do_run helper"""
        self.assertFalse(check_run())
        do_run()
        self.assertTrue(check_run())

    def test_stop_running(self):
        """Test explicit execution of stop_running helper"""
        self.assertFalse(check_stop())
        stop_running()
        self.assertTrue(check_stop())

    def test_signal_handlers_with_real_signals(self):
        """Test signal handlers with real signal delivery"""
        register_run_handler(self.dummy_conf, signal.SIGUSR1)
        register_stop_handler(self.dummy_conf, signal.SIGUSR2)

        os.kill(os.getpid(), signal.SIGUSR1)
        time.sleep(0.1)
        self.assertTrue(check_run())

        os.kill(os.getpid(), signal.SIGUSR2)
        time.sleep(0.1)
        self.assertTrue(check_stop())

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
