#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# distpickle - [insert a few words of module description on this line]
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

"""This module contains various wrapper functions for server pickle
operations. In that way the underlying distribution of pickled server
files can be separated from the normal server operation.
Contrary to the native pickle module this version does not separate
file opening from pickle operations.
"""

import pickle

import shared.distfile as distfile
from shared.distfile import LOCK_EX, LOCK_SH


def dump(obj, path, protocol=0):
    """Dump a binary representation of obj to the file, path"""
    contents = pickle.dumps(obj)
    fd = distfile.DistFile(path, "w")
    fd.lock(LOCK_EX)
    fd.write(contents)
    fd.flush()
    fd.unlock()
    fd.close()

def dumps(obj, protocol=0):
    """Simple pass through to same pickle function"""
    return pickle.dumps(obj)
    
def load(path):
    """Load a object from the binary representation of it in the
    file, path"""
    fd = distfile.DistFile(path, "r")
    fd.lock(LOCK_SH)
    contents = fd.read()
    fd.unlock()
    fd.close()
    return pickle.loads(contents)
    
def loads(contents):
    """Simple pass through to same pickle function"""
    return pickle.loads(contents)
