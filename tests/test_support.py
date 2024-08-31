from __future__ import print_function
import os
import sys
import unittest

from tests.support import MigTestCase, PY2, testmain, temppath, \
                    AssertOver


class InstrumentedAssertOver(AssertOver):
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
    def _class_attribute(self, name, **kwargs):
        cls = type(self)
        if 'value' in kwargs:
            setattr(cls, name, kwargs['value'])
        else:
            return getattr(cls, name, None)

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

        attempt_wrapper = self.assert_over(values=(1, 2, 3), _AssertOver=InstrumentedAssertOver)

        # record the wrapper on the test case so the subsequent test can assert against it
        self._class_attribute('surviving_attempt_wrapper', value=attempt_wrapper)

        with attempt_wrapper as attempt:
            attempt(assert_is_int)
        attempt_wrapper.assert_success()

        self.assertTrue(attempt_wrapper.has_check_callable())
        # cleanup was recorded
        self.assertIn(attempt_wrapper.get_check_callable(), self._cleanup_checks)

    def test_when_asserting_over_multiple_values_after(self):
        # test name is purposefully after ..._recorded in sort order
        # such that we can check the check function was called correctly

        attempt_wrapper = self._class_attribute('surviving_attempt_wrapper')
        self.assertTrue(attempt_wrapper.was_check_callable_called())


if __name__ == '__main__':
    testmain()
