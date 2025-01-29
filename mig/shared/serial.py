#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# serial - object serialization operations using pickle, json or yaml
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Pickle/JSON/YAML based serializing"""

from __future__ import print_function

# Python 2 requires explicit cPickle whereas python 3 defaults to it
try:
    import cPickle as pickle
except ImportError:
    import pickle
# IMPORTANT: lazy-load json and yaml mainly in order to work around PAM crashes
#            seen in sshd+sftpsubsys sessions. Apparently there's a bug / C-API
#            incompatibility when using yaml in embedded python interpreters,
#            due to yaml using its own nested C-extensions. In practice it
#            results in a metaclass conflict TypeError or SystemError upon yaml
#            re-init there like described in
#            https://github.com/ros-drivers/rosserial/issues/450
#            On Rocky 9 it's the TypeError and on Rocky 8 the SystemError.
try:
    import json
except ImportError:
    json = None
try:
    import yaml
except ImportError:
    yaml = None
except (TypeError, SystemError):
    # NOTE: this should not really happen but it does with sshd+sftpsubsys in
    #       our PAM module hooking into this code as described above. We don't
    #       actually need yaml in that case so just silently ignore it here and
    #       only raise an assertion error if used below.
    yaml = None


def dumps(data, protocol=0, serializer='pickle', **kwargs):
    """Dump data to serialized string using given serializer using native lib.
    """
    if serializer == 'pickle':
        serial_helper = pickle.dumps
        if 'protocol' not in kwargs:
            kwargs['protocol'] = protocol
    if serializer == 'json':
        assert json is not None, "JSON module must be loaded for actual use"
        serial_helper = json.dumps
    if serializer == 'yaml':
        assert yaml is not None, "YAML module must be loaded for actual use"
        serial_helper = yaml.dump
    return serial_helper(data, **kwargs)


def dump(data, path, protocol=0, serializer='pickle', mode='wb', **kwargs):
    """Dump data to file given by path. Pass most handling through to dumps.
    """
    with open(path, mode) as fh:
        fh.write(dumps(data, protocol, serializer, **kwargs))


def loads(data, serializer='pickle', **kwargs):
    """Load data from serialized string with serializer using native lib.
    """
    serial_helper = pickle.loads
    if serializer == 'json':
        assert json is not None, "JSON module must be loaded for actual use"
        serial_helper = json.loads
    if serializer == 'yaml':
        assert yaml is not None, "YAML module must be loaded for actual use"
        # NOTE: yaml load supports both string and file-like obj
        serial_helper = yaml.load
        kwargs['Loader'] = yaml.SafeLoader
    return serial_helper(data)


def load(path, serializer='pickle', mode='rb', **kwargs):
    """Load data from file given by path. Pass most handling through to loads.
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
