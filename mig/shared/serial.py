#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# serial - object serialization operations using pickle
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

# TODO: enable cPickle again if segfaults continue on production server
#import cPickle as pickle
import pickle

def dumps(data, protocol=0):
    """Dump data to serialized string"""

    return pickle.dumps(data)

def dump(data, path, protocol=0):
    """Dump data to file given by path"""

    filehandle = open(path, 'wb')
    pickle.dump(data, filehandle, 0)
    filehandle.close()

def loads(data):
    """Load data from serialized string"""

    return pickle.loads(data)

def load(path):
    """Load serialized data from file given by path"""

    filehandle = open(path, 'rb')
    data = pickle.load(filehandle)
    filehandle.close()
    return data

if "__main__" == __name__:
    print "Testing serializer"
    tmp_path = "dummyserial.tmp"
    orig = {'abc': 123, 'def': 'def', 'ghi':42.0}
    print "testing serializing to string and back"
    data = loads(dumps(orig))
    print "original\n%s\nloaded\n%s\nMatch: %s" % (orig, data, orig == data) 
    print "testing serializing to file and back"
    dump(orig, tmp_path)
    data = load(tmp_path)
    print "original\n%s\nloaded\n%s\nMatch: %s" % (orig, data, orig == data) 
    
