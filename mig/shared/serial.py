#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# serial - object serialization operations using pickle or json
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Pickle based serializing"""

from __future__ import print_function

# NOTE: wrap in try/except to avoid autopep8 interference in import order
try:
    from future import standard_library
    standard_library.install_aliases()
except Exception as exc:
    print("ERROR: failed to init compatibility setup")
    exit(1)

import json
import yaml

# Python 2 requires explicit cPickle where as python 3 defaults to it
try:
    import cPickle as pickle
except ImportError:
    import pickle

from mig.shared.base import force_native_str_rec, force_utf8_rec


def dumps(data, protocol=0, serializer='pickle', **kwargs):
    """Dump data to serialized string using given serializer.
    IMPORTANT: we always force data onto UTF-8 bytes for consistency and
    backwards compliance with data from legacy Python versions.
    """
    utf8_data = force_utf8_rec(data)
    if serializer == 'pickle':
        serial_helper = pickle.dumps
        if 'protocol' not in kwargs:
            kwargs['protocol'] = protocol
    if serializer == 'json':
        serial_helper = json.dumps
    if serializer == 'yaml':
        serial_helper = yaml.dump
    return serial_helper(utf8_data, **kwargs)


def dump(data, path, protocol=0, serializer='pickle', mode='wb', **kwargs):
    """Dump data to file given by path.
    IMPORTANT: we always force data onto UTF-8 bytes for consistency and
    backwards compatibility with data from legacy Python versions.
    """
    with open(path, mode) as fh:
        fh.write(dumps(data, protocol, serializer, **kwargs))


def loads(data, serializer='pickle', **kwargs):
    """Load data from serialized string.
    IMPORTANT: we force data into native string format for consistency and
    backwards compatibility with data from legacy Python versions.
    """
    serial_helper = pickle.loads
    if serializer == 'json':
        serial_helper = json.loads
    if serializer == 'yaml':
        # NOTE: yaml load supports both string and file-like obj
        serial_helper = yaml.load
        kwargs['Loader'] = yaml.SafeLoader
    # Python3+ fallback to read as bytes, which Python2 always implicitly did.
    try:
        result = serial_helper(data, **kwargs)
    except UnicodeDecodeError:
        result = serial_helper(data, encoding="bytes", **kwargs)
    return force_native_str_rec(result)


def load(path, serializer='pickle', mode='rb', **kwargs):
    """Load serialized data from file given by path.
    IMPORTANT: we force data into native string format for consistency and
    backwards compatibility with data from legacy Python versions.
    """
    with open(path, mode) as fh:
        return loads(fh.read(), serializer, **kwargs)


if "__main__" == __name__:
    print("Testing serializer")
    tmp_path = "dummyserial.tmp"
    orig = {'abc': 123, 'def': 'def', 'ghi': 42.0, 'accented': 'TéstÆøå'}
    print("testing serializing to string and back")
    data = loads(dumps(orig))
    print("original\n%s\nloaded\n%s\nMatch: %s" % (orig, data, orig == data))
    print("testing serializing to file and back")
    dump(orig, tmp_path)
    data = load(tmp_path)
    print("original\n%s\nloaded\n%s\nMatch: %s" % (orig, data, orig == data))
