#!/usr/bin/env python
# encoding: utf-8
"""
HDF5.py

Pytables/HDF5 storage backend

Created by Jan Wiberg on 2010-03-22.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""

import sys
import os
from hierarchical import HierarchicalClass
from data import data
from metadata import metadata

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
            
    

class optionsmock:
    backingstore = '/tmp/grsfstemp.h5'

if __name__ == '__main__':
    om = optionsmock()
    h5 = HDF5Storage(om)