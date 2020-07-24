#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# serial - object serialization operations using pickle or json
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

import cPickle as pickle
import json
import yaml


def dumps(data, protocol=0, serializer='pickle', **kwargs):
    """Dump data to serialized string using given serializer."""
    if serializer == 'pickle':
        serial_helper = pickle.dumps
        if 'protocol' not in kwargs:
            kwargs['protocol'] = protocol
    if serializer == 'json':
        serial_helper = json.dumps
    if serializer == 'yaml':
        serial_helper = yaml.dump
    return serial_helper(data, **kwargs)


def dump(data, path, protocol=0, serializer='pickle', mode='wb', **kwargs):
    """Dump data to file given by path"""
    if serializer == 'pickle':
        serial_helper = pickle.dump
        if 'protocol' not in kwargs:
            kwargs['protocol'] = protocol
    if serializer == 'json':
        serial_helper = json.dump
    if serializer == 'yaml':
        serial_helper = yaml.dump
    with open(path, mode) as fh:
        serial_helper(data, fh, **kwargs)


def loads(data, serializer='pickle', **kwargs):
    """Load data from serialized string"""
    serial_helper = pickle.loads
    if serializer == 'json':
        serial_helper = json.loads
    if serializer == 'yaml':
        # NOTE: yaml load supports both string and file-like obj
        serial_helper = yaml.load
        kwargs['Loader'] = yaml.SafeLoader
    return serial_helper(data)


def load(path, serializer='pickle', mode='rb', **kwargs):
    """Load serialized data from file given by path"""
    serial_helper = pickle.load
    if serializer == 'json':
        serial_helper = json.load
    if serializer == 'yaml':
        serial_helper = yaml.load
        kwargs['Loader'] = yaml.SafeLoader
    with open(path, mode) as fh:
        return serial_helper(fh, **kwargs)


if "__main__" == __name__:
    print "Testing serializer"
    tmp_path = "dummyserial.tmp"
    orig = {'abc': 123, 'def': 'def', 'ghi': 42.0}
    print "testing serializing to string and back"
    data = loads(dumps(orig))
    print "original\n%s\nloaded\n%s\nMatch: %s" % (orig, data, orig == data)
    print "testing serializing to file and back"
    dump(orig, tmp_path)
    data = load(tmp_path)
    print "original\n%s\nloaded\n%s\nMatch: %s" % (orig, data, orig == data)
