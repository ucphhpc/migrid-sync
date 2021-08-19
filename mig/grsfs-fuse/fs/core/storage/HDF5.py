#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# HDF5 - Pytables/HDF5 storage backend
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""
Pytables/HDF5 storage backend

Created by Jan Wiberg on 2010-03-22.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""
from __future__ import absolute_import

from builtins import object
import sys
import os
from .hierarchical import HierarchicalClass
from .data import data
from .metadata import metadata

try:
    import tables
    loaded = True
except:
    loaded = False

class HDF5Storage(HierarchicalClass, data, metadata):
     
    def _initialize(self, filename):
        """Initialize the HDF5 file if needed"""
        h5file = tables.openFile(filename, mode = "w", title = "GRSfs Storage File")
        if not "trunk" in h5file.root:
            group = h5file.createGroup("/", 'trunk', 'Main volume')
        
        self.root = group
        
    def __init__(self, options):
        super(HDF5Storage, self).__init__()
        if not loaded:
            raise Exception("Unable to load PyTables")

        self._initialize(options.backingstore)
            
    

class optionsmock(object):
    backingstore = '/tmp/grsfstemp.h5'

if __name__ == '__main__':
    om = optionsmock()
    h5 = HDF5Storage(om)
