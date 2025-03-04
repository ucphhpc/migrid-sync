# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_support - unit test of the corresponding tests module
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

"""Unit tests for the tests module pointed to in the filename"""

from __future__ import print_function
import os
import sys
import unittest

from tests.support import MigTestCase, PY2, testmain, temppath, \
    AssertOver, FakeConfiguration

from mig.shared.conf import get_configuration_object
from mig.shared.configuration import Configuration


class InstrumentedAssertOver(AssertOver):
    """Helper to keep track of AssertOver runs"""

    def __init__(self, *args, **kwargs):
        AssertOver.__init__(self, *args, **kwargs)
        self._check_callable = None
        self._check_callable_called = False

    def get_check_callable(self):
        return self._check_callable

    def has_check_callable(self):
        return self._check_callable is not None

    def was_check_callable_called(self):
        return self._check_callable_called

    def to_check_callable(self):
        _check_callable = AssertOver.to_check_callable(self)

        def _wrapped_check_callable():
            self._check_callable_called = True
            _check_callable()
        self._check_callable = _wrapped_check_callable
        return _wrapped_check_callable


class SupportTestCase(MigTestCase):
    """Coverage of base Support helpers"""

    def _class_attribute(self, name, **kwargs):
        cls = type(self)
        if 'value' in kwargs:
            setattr(cls, name, kwargs['value'])
        else:
            return getattr(cls, name, None)

    def test_provides_a_fake_configuration(self):
        configuration = self.configuration

        self.assertIsInstance(configuration, FakeConfiguration)

    def test_provides_a_fake_configuration_for_the_duration_of_the_test(self):
        c1 = self.configuration
        c2 = self.configuration

        self.assertIs(c2, c1)

    @unittest.skipIf(PY2, "Python 3 only")
    def test_unclosed_files_are_recorded(self):
        tmp_path = temppath("support-unclosed", self)

        def open_without_close():
            with open(tmp_path, 'w'):
                pass
            open(tmp_path)
            return

        open_without_close()

        with self.assertRaises(RuntimeError):
            self._logger.check_empty_and_reset()

    def test_unclosed_files_are_reset(self):
        # test name is purposefully after ..._recorded in sort order
        # such that we can check the fake logger was cleaned up correctly
        try:
            # will not throw for a clean logger
            self._logger.check_empty_and_reset()
        except:
            self.assertTrue(False, "should not be reachable")

    def test_when_asserting_over_multiple_values(self):
        def assert_is_int(value):
            assert isinstance(value, int)

        attempt_wrapper = self.assert_over(
            values=(1, 2, 3), _AssertOver=InstrumentedAssertOver)

        # record the wrapper on the test case so the subsequent test can assert against it
        self._class_attribute('surviving_attempt_wrapper',
                              value=attempt_wrapper)

        with attempt_wrapper as attempt:
            attempt(assert_is_int)
        attempt_wrapper.assert_success()

        self.assertTrue(attempt_wrapper.has_check_callable())
        # cleanup was recorded
        self.assertIn(attempt_wrapper.get_check_callable(),
                      self._cleanup_checks)

    def test_when_asserting_over_multiple_values_after(self):
        # test name is purposefully after ..._recorded in sort order
        # such that we can check the check function was called correctly

        attempt_wrapper = self._class_attribute('surviving_attempt_wrapper')
        self.assertTrue(attempt_wrapper.was_check_callable_called())


class SupportTestCase_overridden_configuration(MigTestCase):
    """Coverage of base Support helpers extension with configuration override"""

    def _provide_configuration(self):
        return 'testconfig'

    def test_provides_the_test_configuration(self):
        expected_last_dir = 'testconfs-py2' if PY2 else 'testconfs-py3'

        configuration = self.configuration

        # check we have a real config object
        self.assertIsInstance(configuration, Configuration)
        # check for having loaded a config file from a test config dir
        config_file_path_parts = configuration.config_file.split(os.path.sep)
        config_file_path_parts.pop()  # discard file part
        config_file_last_dir = config_file_path_parts.pop()
        self.assertTrue(config_file_last_dir, expected_last_dir)


if __name__ == '__main__':
    testmain()
