#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# __init__ - package marker and core package functions
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
from configparser import ConfigParser
import difflib
import errno
import io
import json
import logging
import os
import shutil
import stat
import sys
from unittest import TestCase, main as testmain

from tests.support.configsupp import FakeConfiguration
from tests.support.suppconst import MIG_BASE, TEST_BASE, TEST_FIXTURE_DIR, \
    TEST_OUTPUT_DIR

PY2 = (sys.version_info[0] == 2)

# force defaults to a local environment
os.environ['MIG_ENV'] = 'local'

# expose the configured environment as a constant
MIG_ENV = os.environ['MIG_ENV']

if MIG_ENV == 'local':
    # force testconfig as the conig file path
    is_py2 = PY2
    _conf_dir_suffix = "-py%s" % ('2' if is_py2 else '3',)
    _conf_dir = "testconfs%s" % (_conf_dir_suffix,)
    _local_conf = os.path.join(
        MIG_BASE, 'envhelp/output', _conf_dir, 'MiGserver.conf')
    _config_file = os.getenv('MIG_CONF', None)
    if _config_file is None:
        os.environ['MIG_CONF'] = _local_conf

# All MiG related code will at some point include bits from the mig module
# namespace. Rather than have this knowledge spread through every test file,
# make the sole responsbility of test files to find the support file and
# configure the rest here.

sys.path.append(MIG_BASE)

# provision an output directory up-front
try:
    os.mkdir(TEST_OUTPUT_DIR)
except EnvironmentError as enverr:
    if enverr.errno == errno.EEXIST:  # FileExistsError
        shutil.rmtree(TEST_OUTPUT_DIR)
        os.mkdir(TEST_OUTPUT_DIR)

# Exports to expose at the top level from the support library.

from tests.support.assertover import AssertOver
from tests.support.configsupp import FakeConfiguration
from tests.support.loggersupp import FakeLogger
from tests.support.serversupp import make_wrapped_server


# Basic global logging configuration for testing


class BlackHole:
    """Arrange a stream that ignores all logging messages"""

    def write(self, message):
        """NoOp to fake write"""
        pass


BLACKHOLE_STREAM = BlackHole()
# provide a working logging setup (black hole by default)
logging.basicConfig(stream=BLACKHOLE_STREAM)
# request capturing warnings from within the Python runtime
logging.captureWarnings(True)


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
        self._cleanup_checks = list()
        self._cleanup_paths = set()
        self._configuration = None
        self._logger = None
        self._skip_logging = False

    def setUp(self):
        """Init before tests"""
        if not self._skip_logging:
            self._reset_logging(stream=self.logger)
        self.before_each()

    def tearDown(self):
        """Clean up after tests"""
        self.after_each()

        if not self._skip_logging:
            self._logger.check_empty_and_reset()

        for check_callable in self._cleanup_checks:
            check_callable.__call__()
        self._cleanup_checks = list()

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
    def after_each(self):
        """After each test action hook"""
        pass

    def before_each(self):
        """Before each test action hook"""
        pass

    def _register_check(self, check_callable):
        self._cleanup_checks.append(check_callable)

    def _reset_logging(self, stream):
        root_logger = logging.getLogger()
        root_handler = root_logger.handlers[0]
        root_handler.stream = stream

    # testcase defaults

    @staticmethod
    def _make_configuration_instance(configuration_to_make):
        if configuration_to_make == 'fakeconfig':
            return FakeConfiguration()
        elif configuration_to_make == 'testconfig':
            from mig.shared.conf import get_configuration_object
            return get_configuration_object(skip_log=True, disable_auth_log=True)
        else:
            raise AssertionError(
                "MigTestCase: unknown configuration %r" % (configuration_to_make,))

    def _provide_configuration(self):
        return 'fakeconfig'

    @property
    def configuration(self):
        """Init a fake configuration if not already done"""
        if self._configuration is None:
            configuration_to_make = self._provide_configuration()
            self._configuration = self._make_configuration_instance(
                configuration_to_make)
        return self._configuration

    @property
    def logger(self):
        """Init a fake logger if not already done"""
        if self._logger is None:
            self._logger = FakeLogger()
        return self._logger

    def assert_over(self, values=None, _AssertOver=AssertOver):
        assert_over = _AssertOver(values=values, testcase=self)
        check_callable = assert_over.to_check_callable()
        self._register_check(check_callable)
        return assert_over

    # custom assertions available for common use

    def assertFileContentIdentical(self, file_actual, file_expected):
        """Make sure file_actual and file_expected are identical"""
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

    def assertFileExists(self, relative_path):
        """Make sure relative_path exists and is a file"""
        path_kind = self.assertPathExists(relative_path)
        assert path_kind == "file", "expected a file but found %s" % (
            path_kind, )
        return os.path.join(TEST_OUTPUT_DIR, relative_path)

    def assertPathExists(self, relative_path):
        """Make sure file in relative_path exists"""
        assert not os.path.isabs(
            relative_path), "expected relative path within output folder"
        absolute_path = os.path.join(TEST_OUTPUT_DIR, relative_path)
        return MigTestCase._absolute_path_kind(absolute_path)

    @staticmethod
    def _absolute_path_kind(absolute_path):
        stat_result = os.lstat(absolute_path)
        if stat.S_ISLNK(stat_result.st_mode):
            return "symlink"
        elif stat.S_ISDIR(stat_result.st_mode):
            return "dir"
        else:
            return "file"

    def assertPathWithin(self, path, start=None):
        """Make sure path is within start directory"""
        if not is_path_within(path, start=start):
            raise AssertionError(
                "path %s is not within directory %s" % (path, start))

    @staticmethod
    def pretty_display_path(absolute_path):
        assert os.path.isabs(absolute_path)
        relative_path = os.path.relpath(absolute_path, start=MIG_BASE)
        assert not relative_path.startswith('..')
        return relative_path


def is_path_within(path, start=None, _msg=None):
    """Check if path is within start directory"""
    try:
        assert os.path.isabs(path), _msg
        relative = os.path.relpath(path, start=start)
    except:
        return False
    return not relative.startswith('..')


def fixturefile(relative_path, fixture_format=None):
    """Support function for loading fixtures from their serialised format.

    Doing so is a little more involved than it may seem because serialisation
    formats may not capture various nuances of the python data they represent.
    For this reason each supported format defers to a format specific function
    which can then, for example, load hints about deserialization.
    """

    assert fixture_format is not None, "fixture format must be specified"
    assert not os.path.isabs(
        relative_path), "fixture is not relative to fixture folder"
    relative_path_with_ext = "%s.%s" % (relative_path, fixture_format)
    tmp_path = os.path.join(TEST_FIXTURE_DIR, relative_path_with_ext)
    assert os.path.isfile(tmp_path), \
        "fixture file for format is not present: %s" % \
        (relative_path_with_ext,)
    #_, extension = os.path.splitext(os.path.basename(tmp_path))
    #assert fixture_format == extension, "fixture file does not match format"

    if fixture_format == 'json':
        return _fixturefile_json(tmp_path)
    else:
        raise AssertionError(
            "unsupported fixture format: %s" % (fixture_format,))


_FIXTUREFILE_HINTAPPLIERS = {
    'array_of_tuples': lambda value: [tuple(x) for x in value]
}


def _fixturefile_json(json_path):
    hints = ConfigParser()

    # leti's see if there are loading hints
    try:
        hints_path = "%s.ini" % (json_path,)
        with open(hints_path) as hints_file:
            hints.read_file(hints_file)
    except FileNotFoundError:
        pass

    with io.open(json_path) as json_file:
        json_object = json.load(json_file)

        for item_name, item_hint in hints['DEFAULT'].items():
            loaded_value = json_object[item_name]
            value_from_loaded_value = _FIXTUREFILE_HINTAPPLIERS[item_hint]
            json_object[item_name] = value_from_loaded_value(loaded_value)

        return json_object


def fixturepath(relative_path):
    """Get absolute fixture path for relative_path"""
    tmp_path = os.path.join(TEST_FIXTURE_DIR, relative_path)
    return tmp_path


def temppath(relative_path, test_case, ensure_dir=False, skip_clean=False):
    """Get absolute temp path for relative_path"""
    assert isinstance(test_case, MigTestCase)
    tmp_path = os.path.join(TEST_OUTPUT_DIR, relative_path)
    if ensure_dir:
        try:
            os.mkdir(tmp_path)
        except FileExistsError:
            raise AssertionError(
                "ABORT: use of unclean output path: %s" % relative_path)
    if not skip_clean:
        test_case._cleanup_paths.add(tmp_path)
    return tmp_path


# compatibility alias
def cleanpath(relative_path, test_case, **kwargs):
    return temppath(relative_path, test_case, **kwargs)
