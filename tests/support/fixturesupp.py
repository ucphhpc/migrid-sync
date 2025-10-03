#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# configsupp - configuration helpers for unit tests
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

"""Fixture related details within the test support library."""

from configparser import ConfigParser
import json
import os
import pickle
import shutil
from types import SimpleNamespace

from tests.support.suppconst import TEST_FIXTURE_DIR


def _fixturefile_loadrelative(relative_path, fixture_format=None):
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

    data = None

    if fixture_format == 'binary' or fixture_format == 'pickle':
        with open(tmp_path, 'rb') as binfile:
            data = binfile.read()
    elif fixture_format == 'json':
        data = _fixturefile_json(tmp_path)
    else:
        raise AssertionError(
            "unsupported fixture format: %s" % (fixture_format,))

    if fixture_format == 'pickle':
        data = pickle.loads(data)

    return data, tmp_path


def _fixturefile_normname(relative_path, prefix=''):
    """Grab normname from relative_path and optionally add a path prefix"""
    normname, _ = relative_path.split('--')
    if prefix:
        return os.path.join(prefix, normname)
    return normname


_FIXTUREFILE_HINTAPPLIERS = {
    'array_of_tuples': lambda value: [tuple(x) for x in value]
}


def _fixturefile_json(json_path):
    hints = ConfigParser()

    # let's see if there are loading hints
    try:
        hints_path = "%s.ini" % (json_path,)
        with open(hints_path) as hints_file:
            hints.read_file(hints_file)
    except FileNotFoundError:
        pass

    with open(json_path) as json_file:
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


class _PreparedFixture:
    def __init__(self, testcase,
                 fixture_format,
                 fixture_data,
                 fixture_path):
        self.testcase = testcase
        self.fixture_format = fixture_format
        self.fixture_data = fixture_data
        self.fixture_path = fixture_path

    def assertAgainstFixture(self, value):
        """Compare a value against fixture data ensuring that in the case of
        failure the location of the fixture is prepended to the diff."""

        assert value is not None
        testcase = self.testcase
        originalMaxDiff = testcase.maxDiff
        testcase.maxDiff = None

        raised_exception = None
        try:
            testcase.assertEqual(value, self.fixture_data)
        except AssertionError as diffexc:
            raised_exception = diffexc
        finally:
            testcase.maxDiff = originalMaxDiff
        if raised_exception:
            message = "value differed from fixture stored at %s\n\n%s" % (
                _to_display_path(self.fixture_path), raised_exception)
            raise AssertionError(message)

    def copy_as_temp(self, prefix=None):
        """Copy a fixture to temporary file at the given path prefix."""

        assert prefix is not None
        fixture_basename = os.path.basename(self.fixture_path)
        fixture_name = fixture_basename[0:-len(self.fixture_format) - 1]
        normalised_path = _fixturefile_normname(fixture_name, prefix=prefix)
        copied_fixture_file = self.testcase.temppath(normalised_path)
        shutil.copyfile(self.fixture_path, copied_fixture_file)
        return copied_fixture_file

    @staticmethod
    def from_relpath(testcase, fixture_relpath, fixture_format):
        """
        Instantiate a fixture hint object from a supplied relative path to
        the on-disk fixture file.
        """

        fixture_data, fixture_path = _fixturefile_loadrelative(
            fixture_relpath, fixture_format)
        return _PreparedFixture(testcase, fixture_format, fixture_data, fixture_path)


class FixtureAssertMixin:
    def prepareFixtureAssert(self, fixture_relpath, fixture_format=None):
        """Prepare to assert a value against a fixture."""
        return _PreparedFixture.from_relpath(self, fixture_relpath, fixture_format)
