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
import io
import json
import os
import shutil

from tests.support.suppconst import MIG_BASE, TEST_FIXTURE_DIR


_FIXTUREFILE_HINTAPPLIERS = {
    'array_of_tuples': lambda value: [tuple(x) for x in value]
}


def _to_display_path(value):
    display_path = os.path.relpath(value, MIG_BASE)
    if not display_path.startswith('.'):
        return "./" + display_path
    return display_path


def _fixturefile(relative_path, fixture_format=None):
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

    data = None

    if fixture_format == 'binary':
        with open(tmp_path, 'rb') as binfile:
            data = binfile.read()
    elif fixture_format == 'json':
        data = _fixturefile_json(tmp_path)
    else:
        raise AssertionError(
            "unsupported fixture format: %s" % (fixture_format,))

    return data, tmp_path


def _fixturefile_json(json_path):
    hints = ConfigParser()

    # let's see if there are loading hints
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


def _fixturefile_normname(relative_path, prefix=''):
    """Grab normname from relative_path and optionally add a path prefix"""
    normname, _ = relative_path.split('--')
    if prefix:
        return os.path.join(prefix, normname)
    return normname


class _AssertAgainstFixture:
    def __init__(self, testcase, fixture_format, fixture_data, fixture_path):
        self._testcase = testcase
        self._fixture_format = fixture_format
        self._fixture_data = fixture_data
        self._fixture_path = fixture_path

    def assertAgainstFixture(self, value=None):
        assert value is not None
        originalMaxDiff = self._testcase.maxDiff
        self._testcase.maxDiff = None
        try:
            self._testcase.assertEqual(value, self._fixture_data)
        except AssertionError as diffexc:
            message = "value differed from fixture stored at %s\n\n%s" % (
                _to_display_path(self._fixture_path), diffexc)
            raise AssertionError(message)
        finally:
            self._testcase.maxDiff = originalMaxDiff

    def copy_as_temp(self, prefix=None):
        assert prefix is not None
        fixture_basename = os.path.basename(self._fixture_path)
        fixture_name = fixture_basename[0:-len(self._fixture_format) - 1]
        normalised_path = _fixturefile_normname(fixture_name, prefix=prefix)
        copied_fixture_file = self._testcase.temppath(normalised_path)
        shutil.copyfile(self._fixture_path, copied_fixture_file)
        return copied_fixture_file


class FixtureAssertMixin:
    def prepareFixtureAssert(self, fixture_relpath, fixture_format=None):
        fixture_data, fixture_path = _fixturefile(
            fixture_relpath, fixture_format)
        return _AssertAgainstFixture(self, fixture_format, fixture_data, fixture_path)


def fixturepath(relative_path):
    """Get absolute fixture path for relative_path"""
    tmp_path = os.path.join(TEST_FIXTURE_DIR, relative_path)
    return tmp_path
