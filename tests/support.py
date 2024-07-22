#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# support - helper functions for unit testing
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Supporting functions for the unit test framework"""

from collections import defaultdict
import difflib
import errno
import io
import logging
import os
import re
import shutil
import stat
import sys
from unittest import TestCase, main as testmain

TEST_BASE = os.path.dirname(__file__)
TEST_FIXTURE_DIR = os.path.join(TEST_BASE, "fixture")
TEST_OUTPUT_DIR = os.path.join(TEST_BASE, "output")
MIG_BASE = os.path.realpath(os.path.join(TEST_BASE, ".."))
PY2 = sys.version_info[0] == 2

# force defaults to a local environment
os.environ['MIG_ENV'] = 'local'

# All MiG related code will at some point include bits
# from the mig module namespace. Rather than have this
# knowledge spread through every test file, make the
# sole responsbility of test files to find the support
# file and configure the rest here.
sys.path.append(MIG_BASE)

# provision an output directory up-front
try:
    os.mkdir(TEST_OUTPUT_DIR)
except EnvironmentError as enverr:
    if enverr.errno == errno.EEXIST:  # FileExistsError
        shutil.rmtree(TEST_OUTPUT_DIR)
        os.mkdir(TEST_OUTPUT_DIR)

# Basic global logging configuration for testing


class BlackHole:
    """Arrange a stream that ignores all logging messages"""

    def write(self, message):
        pass


BLACKHOLE_STREAM = BlackHole()
# provide a working logging setup (black hole by default)
logging.basicConfig(stream=BLACKHOLE_STREAM)
# request capturing warnings from within the Python runtime
logging.captureWarnings(True)


class FakeLogger:
    """An output capturing logger suitable for being passed to the
    majority of MiG code by presenting an API compatible interface
    with the common logger module.

    An instance of this class is made avaiable to test cases which
    can pass it down into function calls and subsequenently make
    assertions against any output strings hat were recorded during
    execution while also avoiding noise hitting the console.
    """

    RE_UNCLOSEDFILE = re.compile(
        'unclosed file <.*? name=\'(?P<location>.*?)\'( .*?)?>')

    def __init__(self):
        self.channels_dict = defaultdict(list)
        self.unclosed_by_file = defaultdict(list)

    def _append_as(self, channel, line):
        self.channels_dict[channel].append(line)

    def check_empty_and_reset(self):
        unclosed_by_file = self.unclosed_by_file

        # reset the record of any logged messages
        self.channels_dict = defaultdict(list)
        self.unclosed_by_file = defaultdict(list)

        # complain loudly (and in detail) in the case of unclosed files
        if len(unclosed_by_file) > 0:
            messages = '\n'.join({' --> %s: line=%s, file=%s' % (fname, lineno, outname)
                                 for fname, (lineno, outname) in unclosed_by_file.items()})
            raise RuntimeError('unclosed files encountered:\n%s' % (messages,))

    def debug(self, line):
        self._append_as('debug', line)

    def error(self, line):
        self._append_as('error', line)

    def info(self, line):
        self._append_as('info', line)

    def warning(self, line):
        self._append_as('warning', line)

    def write(self, message):
        channel, namespace, specifics = message.split(':', 2)

        # ignore everything except warnings sent by the python runtime
        if not (channel == 'WARNING' and namespace == 'py.warnings'):
            return

        filename_and_datatuple = FakeLogger.identify_unclosed_file(specifics)
        if filename_and_datatuple is not None:
            self.unclosed_by_file.update((filename_and_datatuple,))

    @staticmethod
    def identify_unclosed_file(specifics):
        filename, lineno, exc_name, message = specifics.split(':', 3)

        exc_name = exc_name.lstrip()
        if exc_name != 'ResourceWarning':
            return

        matched = FakeLogger.RE_UNCLOSEDFILE.match(message.lstrip())
        if matched is None:
            return

        relative_testfile = os.path.relpath(filename, start=MIG_BASE)
        relative_outputfile = os.path.relpath(
            matched.groups('location')[0], start=TEST_BASE)
        return (relative_testfile, (lineno, relative_outputfile))


class MigTestCase(TestCase):
    """Embellished base class for MiG test cases. Provides additional commonly
    used assertions as well as some basics for the standardised and idiomatic
    testing of logic within the codebase.

    By containing these details in a single place we can ensure the reliable
    cleanup of state across tests as well as permit enforcement of constraints
    on all code under test.
    """

    def __init__(self, *args):
        super(MigTestCase, self).__init__(*args)
        self._cleanup_paths = set()
        self._logger = None
        self._skip_logging = False

    def setUp(self):
        if not self._skip_logging:
            self._reset_logging(stream=self.logger)
        self.before_each()

    def tearDown(self):
        if not self._skip_logging:
            self._logger.check_empty_and_reset()
        if self._logger is not None:
            self._reset_logging(stream=BLACKHOLE_STREAM)

        for path in self._cleanup_paths:
            if os.path.islink(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)
            else:
                continue

    # hooks
    def before_each(self):
        pass

    def _reset_logging(self, stream):
        root_logger = logging.getLogger()
        root_handler = root_logger.handlers[0]
        root_handler.stream = stream

    @property
    def logger(self):
        if self._logger is None:
            self._logger = FakeLogger()
        return self._logger

    # custom assertions available for common use

    def assertFileContentIdentical(self, file_actual, file_expected):
        with io.open(file_actual) as f_actual, io.open(file_expected) as f_expected:
            lhs = f_actual.readlines()
            rhs = f_expected.readlines()
            different_lines = list(difflib.unified_diff(rhs, lhs))
            try:
                self.assertEqual(len(different_lines), 0)
            except AssertionError:
                raise AssertionError("""differences found between files
* %s
* %s
included:
%s
                    """ % (
                    os.path.relpath(file_expected, MIG_BASE),
                    os.path.relpath(file_actual, MIG_BASE),
                    ''.join(different_lines)))

    def assertPathExists(self, relative_path):
        assert not os.path.isabs(
            relative_path), "expected relative path within output folder"
        absolute_path = os.path.join(TEST_OUTPUT_DIR, relative_path)
        stat_result = os.lstat(absolute_path)
        if stat.S_ISLNK(stat_result.st_mode):
            return "symlink"
        elif stat.S_ISDIR(stat_result.st_mode):
            return "dir"
        else:
            return "file"

    def assertPathWithin(self, path, start=None):
        if not is_path_within(path, start=start):
            raise AssertionError("path %s is not within directory %s" % (path, start))

    @staticmethod
    def pretty_display_path(absolute_path):
        assert os.path.isabs(absolute_path)
        relative_path = os.path.relpath(absolute_path, start=MIG_BASE)
        assert not relative_path.startswith('..')
        return relative_path


def is_path_within(path, start=None, _msg=None):
    try:
        assert os.path.isabs(path), _msg
        relative = os.path.relpath(path, start=start)
    except:
        return False
    return not relative.startswith('..')


def cleanpath(relative_path, test_case, start=None, skip_clean=False):
    assert isinstance(test_case, MigTestCase)
    if start is None:
        start = TEST_OUTPUT_DIR
    tmp_path = os.path.join(start, relative_path)
    if not skip_clean:
        test_case._cleanup_paths.add(tmp_path)
    return tmp_path


def fixturepath(relative_path):
    tmp_path = os.path.join(TEST_FIXTURE_DIR, relative_path)
    return tmp_path


def temppath(relative_path, test_case, skip_clean=False):
    assert isinstance(test_case, MigTestCase)
    tmp_path = os.path.join(TEST_OUTPUT_DIR, relative_path)
    if not skip_clean:
        test_case._cleanup_paths.add(tmp_path)
    return tmp_path
