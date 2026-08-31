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

import inspect
import json
import os
import pickle
import shutil
from configparser import ConfigParser
from datetime import date, timedelta
from time import mktime
from types import SimpleNamespace

from tests.support.suppconst import MIG_BASE, TEST_FIXTURE_DIR


def _fixturefile_loadrelative(fixture_name, fixture_format=None):
    """Support function for loading fixtures from their serialised format.

    Doing so is a little more involved than it may seem because serialisation
    formats may not capture various nuances of the python data they represent.
    For this reason each supported format defers to a format specific function
    which can then, for example, load hints about deserialization.
    """

    assert fixture_format is not None, "fixture format must be specified"
    relative_path_with_ext = "%s.%s" % (fixture_name, fixture_format)
    tmp_path = os.path.join(TEST_FIXTURE_DIR, relative_path_with_ext)
    assert os.path.isfile(
        tmp_path
    ), 'fixture named "%s" with format %s is not present: %s' % (
        fixture_name,
        fixture_format,
        relative_path_with_ext,
    )

    data = None

    if fixture_format == "binary":
        with open(tmp_path, "rb") as binfile:
            data = binfile.read()
    elif fixture_format == "json":
        with open(tmp_path) as jsonfile:
            data = json.load(jsonfile, object_hook=_FixtureHint.object_hook)
            _hints_apply_from_instances_if_present(data)
            _hints_apply_from_fixture_ini_if_present(fixture_name, data)
    else:
        raise AssertionError(
            "unsupported fixture format: %s" % (fixture_format,)
        )

    return data, tmp_path


def _fixturefile_normname(relative_path, prefix=""):
    """Grab normname from relative_path and optionally add a path prefix"""
    normname, _ = relative_path.split("--")
    if prefix:
        return os.path.join(prefix, normname)
    return normname


# The following chunk of code is all related to "hints": small transformations
# that can be requested to data as it read (and in some cases written) in the
# course of a test run.
#
# The observation here is that the on-disk format of various structures may not
# always be suitable for either as an actual or expected value in a comparison
# or as a human-centric fixture format. But, we explicitly wish to consume the
# value as written by the production code.
#
# Thus, we provide a series of small named transformations which can be
# explicitly requested at a few strategic points (e.g. loading an on-disk file)
# that allows assertions in tests to succinctly make assertions as opposed to
# the intent of the check becoming drowned in the details of conversions etc.
#
# <hints>


def _hints_apply_array_of_tuples(value, modifier):
    """
    Convert list of lists such that its values are instead tuples.
    """
    assert modifier is None
    return [tuple(x) for x in value]


def _hints_apply_today_relative(value, modifier):
    """
    Geneate a time value by applying a declared delta to today's date.
    """

    kind, delta = modifier.split("|")
    if kind == "days":
        time_delta = timedelta(days=int(delta))
        adjusted_datetime = date.today() + time_delta
        return int(mktime(adjusted_datetime.timetuple()))
    else:
        raise NotImplementedError("unspported today_relative modifier")


def _hints_apply_today_relative_date(value, modifer):
    """
    Geneate a date value by applying a declared delta to today's date.
    """
    kind, delta = modifer.split('|')
    if kind == "days":
        time_delta = timedelta(days=int(delta))
        adjusted_datetime = date.today() + time_delta
        return adjusted_datetime.isoformat()
    else:
        raise NotImplementedError("unspported today_relative_date modifier")



def _hints_apply_dict_bytes_to_strings_kv(input_dict, modifier):
    """
    Convert a dictionary whose keys/values are bytes to one whose
    keys/values are strings.
    """

    assert modifier is None

    output_dict = {}

    for k, v in input_dict.items():
        key_to_use = k
        if isinstance(k, bytes):
            key_to_use = str(k, "utf8")

        if isinstance(v, dict):
            output_dict[key_to_use] = _hints_apply_dict_bytes_to_strings_kv(
                v, modifier
            )
            continue

        val_to_use = v
        if isinstance(v, bytes):
            val_to_use = str(v, "utf8")

        output_dict[key_to_use] = val_to_use

    return output_dict


def _hints_apply_dict_strings_to_bytes_kv(input_dict, modifier):
    """
    Convert a dictionary whose keys/values are strings to one whose
    keys/values are bytes.
    """

    assert modifier is None

    output_dict = {}

    for k, v in input_dict.items():
        key_to_use = k
        if isinstance(k, str):
            key_to_use = bytes(k, "utf8")

        if isinstance(v, dict):
            output_dict[key_to_use] = _hints_apply_dict_strings_to_bytes_kv(
                v, modifier
            )
            continue

        val_to_use = v
        if isinstance(v, str):
            val_to_use = bytes(v, "utf8")

        output_dict[key_to_use] = val_to_use

    return output_dict


def _hints_apply_strings_to_bytes_rec(input_value, modifier):
    """
    Recursively convert strings to bytes, including any items
    contained within iterables, stopping at the values of keys.
    """

    if hasattr(input_value, 'items'):
        return _hints_apply_dict_strings_to_bytes_kv(input_value, modifier)
    elif isinstance(input_value, (list, tuple)):
        input_type = type(input_value)
        return input_type((_hints_apply_strings_to_bytes_rec(item, modifier) for item in input_value))
    elif isinstance(input_value, str):
        return bytes(input_value, 'utf8')
    else:
        raise NotImplementedError("unsupported recusrive conversion attempt")


def _hints_apply_dict_to_pairs(input_value, modifier):
    """
    Convert an array of pairs to a dictionary.
    """

    assert modifier is None

    return list(input_value.items())


def _hints_apply_pairs_to_dict(input_value, modifier):
    """
    Convert an array of pairs to a dictionary.
    """

    assert modifier is None

    return dict(input_value)


# hints that can be aplied without an additional modifier argument
_HINTS_APPLIERS_ARGLESS = {
    'array_of_tuples': _hints_apply_array_of_tuples,
    'dict_to_pairs': _hints_apply_dict_to_pairs,
    'today_relative': _hints_apply_today_relative,
    'convert_dict_bytes_to_strings_kv': _hints_apply_dict_bytes_to_strings_kv,
    'convert_dict_strings_to_bytes_kv': _hints_apply_dict_strings_to_bytes_kv,
    'strings_to_bytes_rec': _hints_apply_strings_to_bytes_rec,
    'pairs_to_dict': _hints_apply_pairs_to_dict,
}

# hints applicable to the conversion of attributes during fixture loading
_FIXTUREFILE_APPLIERS_ATTRIBUTES = {
    'array_of_tuples': _hints_apply_array_of_tuples,
    'today_relative': _hints_apply_today_relative,
    'today_relative_date': _hints_apply_today_relative_date
}

# hints applied when writing the contents of a fixture as a temporary file
_FIXTUREFILE_APPLIERS_ONWRITE = {
    "convert_dict_strings_to_bytes_kv": _hints_apply_dict_strings_to_bytes_kv,
}


def apply_named_hints(input_value, *hint_names):
    if not hint_names:
        return input_value

    # hints apply _inplace_, thus we dup the input value here to avoid
    # inadvertently making changes to it that may leak out to our callers
    output_value = input_value.copy()
    for hint_name in hint_names:
        hint_fn = _HINTS_APPLIERS_ARGLESS.get(hint_name)
        output_value = hint_fn(output_value, None)
    return output_value


def _hints_apply_from_instances_if_present(json_object):
    """Recursively apply hints to any hint instances in the supplied data."""

    if isinstance(json_object, list):
        return json_object

    for k, v in json_object.items():
        if isinstance(v, dict):
            _hints_apply_from_instances_if_present(v)
            continue

        if isinstance(v, _FixtureHint):
            json_object[k] = _FixtureHint.decode_hint(v)
            pass


def _choose_names_from_hints_ini(hints, section):
    return [hint_name for hint_name in hints[section]
            if hints.getboolean(section, hint_name)]


def _load_hints_ini_for_fixture_if_present(fixture_name):
    """Load any hints that may be specified for a given fixture."""

    hints = ConfigParser()

    # let's see if there are loading hints
    try:
        hints_file = "%s.hints" % (fixture_name,)
        hints_path = os.path.join(TEST_FIXTURE_DIR, hints_file)
        with open(hints_path) as hints_file:
            hints.read_file(hints_file)
    except FileNotFoundError:
        pass

    # ensure empty required fixture to avoid extra conditionals later
    for required_section in ['ATTRIBUTES', 'ONREAD', 'ONWRITE']:
        if not hints.has_section(required_section):
            hints.add_section(required_section)

    return hints


def _hints_apply_from_fixture_ini_if_present(fixture_name, json_object):
    """
    Amend the supplied object loaded from a fixture in place as specified
    by an optional ini file corresponding to the fixture itself.
    """

    hints = _load_hints_ini_for_fixture_if_present(fixture_name)

    # apply any attriutes hints ahead of specified conversions such that any
    # key can be specified matching what is visible within the loaded fixture
    for item_name, item_hint_unparsed in hints["ATTRIBUTES"].items():
        loaded_value = json_object[item_name]

        item_hint_and_maybe_modifier = item_hint_unparsed.split("--")
        item_hint = item_hint_and_maybe_modifier[0]
        if len(item_hint_and_maybe_modifier) == 2:
            modifier = item_hint_and_maybe_modifier[1]
        elif len(item_hint_and_maybe_modifier) == 1:
            modifier = None
        else:
            raise NotImplementedError("failed to parse hint and modifier")
        value_from_loaded_value = _FIXTUREFILE_APPLIERS_ATTRIBUTES[item_hint]

        json_object[item_name] = value_from_loaded_value(loaded_value, modifier)


class _FixtureHint:
    """Named type allowing identification of fixture hints."""

    def __init__(self, hint=None, modifier=None, value=None):
        self.hint = hint
        self.modifier = modifier
        self.value = value

    @staticmethod
    def decode_hint(hint_obj):
        """Produce a value based on the properties of a hint instance."""
        assert isinstance(hint_obj, _FixtureHint)
        value_from_loaded_value = _FIXTUREFILE_APPLIERS_ATTRIBUTES[
            hint_obj.hint
        ]
        return value_from_loaded_value(hint_obj.value, hint_obj.modifier)

    @staticmethod
    def object_hook(decoded_object):
        """
        Function for use as JSON loading hook which will transform
        the serialised representation of a hint into an instance.
        """

        if "_FixtureHint" in decoded_object:
            fixture_hint = _FixtureHint(
                decoded_object["hint"], decoded_object["modifier"]
            )
            return _FixtureHint.decode_hint(fixture_hint)

        return decoded_object


# </hints>


def fixturepath(relative_path):
    """Get absolute fixture path for relative_path"""
    tmp_path = os.path.join(TEST_FIXTURE_DIR, relative_path)
    return tmp_path


def _to_display_path(value):
    """Convert an absolute path to one to be shown as part of test output."""
    display_path = os.path.relpath(value, MIG_BASE)
    if not display_path.startswith("."):
        return "./" + display_path
    return display_path


class _PreparedFixture:
    """
    Object representing a loaded fixture prepared for use within a test case.
    """

    NO_DATA = object()

    def __init__(
        self, testcase, fixture_name, native_fixture_data, fixture_format="", fixture_data=NO_DATA
    ):
        self.testcase = testcase
        self.fixture_name = fixture_name
        self.fixture_format = fixture_format
        self.fixture_data = fixture_data
        self.native_fixture_data = native_fixture_data

    def assertAgainstFixture(self, value, as_native=False):
        """Compare a value against fixture data ensuring that in the case of
        failure the location of the fixture is prepended to the diff."""

        assert value is not None
        testcase = self.testcase
        originalMaxDiff = testcase.maxDiff
        testcase.maxDiff = None

        if as_native:
            expected_data = self.native_fixture_data
        else:
            expected_data = self.fixture_data

        raised_exception = None
        try:
            testcase.assertEqual(value, expected_data)
        except AssertionError as diffexc:
            raised_exception = diffexc
        finally:
            testcase.maxDiff = originalMaxDiff
        if raised_exception:
            if self.fixture_format:
                message_infix = " with format %s" % (self.fixture_format,)
            else:
                message_infix = ""
            message = "value differed from fixture named %s%s\n\n%s" % (
                self.fixture_name,
                message_infix,
                raised_exception,
            )
            raise AssertionError(message)

    def write_to_dir(self, target_dir, output_format=None):
        """
        Write loaded fixture data to temporary file to the specified target
        directory applying any onwrite hints that may be specified.
        """

        assert os.path.isabs(target_dir)

        # convert fixture name (which includes the varaint) to the target file
        fixture_file_target = _fixturefile_normname(
            self.fixture_name, prefix=target_dir
        )

        output_data = self.fixture_data

        # now apply any onwrite conversions
        hints = _load_hints_ini_for_fixture_if_present(self.fixture_name)

        onwrite_hints = _choose_names_from_hints_ini(hints, section='ONWRITE')
        output_data = apply_named_hints(output_data, *onwrite_hints)

        if output_format == "binary":
            with open(fixture_file_target, "wb") as fixture_outputfile:
                fixture_outputfile.write(output_data)
        elif output_format == "json":
            with open(fixture_file_target, "w") as fixture_outputfile:
                json.dump(output_data, fixture_outputfile)
        elif output_format == "pickle":
            with open(fixture_file_target, "wb") as fixture_outputfile:
                pickle.dump(output_data, fixture_outputfile)
        else:
            raise AssertionError(
                "unsupported fixture format: %s" % (output_format,)
            )

    @staticmethod
    def from_relpath(testcase, fixture_name, fixture_format):
        """
        Obtain a prepared fixture given a relative path to the on-disk file
        containing its data.
        """

        raw_fixture_data, fixture_path = _fixturefile_loadrelative(
            fixture_name, fixture_format)

        hints = _load_hints_ini_for_fixture_if_present(fixture_name)

        onread_hints = _choose_names_from_hints_ini(hints, section='ONREAD')
        if onread_hints:
            # hint apply functions operate _inplace_, so given we need to
            # preserve the loaded fixture data we clone the loaded value
            fixture_data = raw_fixture_data.copy()
            native_fixture_data = apply_named_hints(raw_fixture_data, *onread_hints)
        else:
            fixture_data = raw_fixture_data
            native_fixture_data = raw_fixture_data

        return _PreparedFixture(testcase, fixture_name, native_fixture_data, fixture_format, fixture_data)


class FixtureAssertMixin:
    def prepareFixtureAssert(self, fixture_relpath, fixture_format=None):
        """Prepare to assert a value against a fixture."""
        return _PreparedFixture.from_relpath(
            self, fixture_relpath, fixture_format
        )
