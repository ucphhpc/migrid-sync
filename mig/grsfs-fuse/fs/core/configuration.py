#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# configuration - [insert a few words of module description on this line]
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
Created by Jan Wiberg on 2010-03-22.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""
from __future__ import print_function

import os, socket

class ConfigurationException(Exception):
    pass

class Configuration:
    def __init__(self):
        """docstring for __init__"""
        
        # Initial settings
        self.spare = False
        self.heartbeat = 5
        self.backingtype = "passthrough"
        self.network = "xmlrpc"
        self.backingstore = None
        self.backingstorestate = None # directory where to store all scratch data
        self.initial_connect_list = []
        self.contact = None # the string version of the initial connect list
        self.serveraddress = socket.getfqdn() # autodetect the FQDN
        self.serverport = -1
        self.mincopies = 2
        self.maxcopies = 3
        self.benchmark_fast_start = True # randomly finds a score to speed startup.
        self.benchmark_min_gb_free = 50
        self.benchmark_max_gb_free = 200 # above this the score doesn't increase
        self.benchmark_min_free_score = 1.5
        self.freespace_target = "." # Should be same partition as backingstore
        self.iobench_target = "/tmp/random2mbfile" # needs to exist or I/O benchmarking won't work
        self.network_timeout = 5 # set to None for default
        self.logdir = "./logs" #"/var/log/grsfs"
        self.logquiet = False # whether to print to stdout
        self.logverbosity = 0 
        self.neverparticipate = False # turns it into pure ODF
        
          
    def validate(self):
        try:
            assert self.network is not None
            assert self.backingtype is not None
            assert self.backingstore is not None # mandatory non-default option
            assert self.serveraddress is not None
            assert self.serverport is not None and self.serverport > 1024 # mandatory non-default option
            assert self.backingstorestate is not None # mandatory non-default option
        
            assert os.access(self.backingstore, os.R_OK|os.W_OK)
            assert os.path.isdir(self.backingstorestate)
            assert os.access(self.backingstorestate, os.R_OK|os.W_OK)
            self.scratchspace = self.backingstorestate
            self.backingstorestate = os.path.join(self.scratchspace, "%s-%s.grsstate" % (self.serveraddress, self.serverport))
            self.compressedfilelocation = os.path.join(self.scratchspace, "%s-%s.grstemp" % (self.serveraddress, self.serverport))    
            # fails on klynge but not locally??
            # assert os.access(self.backingstorestate, os.R_OK|os.W_OK)
            # assert os.access(self.compressedfilelocation, os.R_OK|os.W_OK)
            
            # mangle the connection string into python-understandable format
            if self.contact and len(self.initial_connect_list) == 0:
                for nodes in self.contact.split(';'):
                    (host, port) = nodes.split(":")
                    port = int(port)
                    assert len(host.strip()) >= 2
                    assert int(port) > 1024
                    self.initial_connect_list.append((host, port))
            # Force timeout to float
            self.network_timeout = float(self.network_timeout)
            
        except Exception:
            print(">>>>>>>> Configuration validation failed, error follows")
            raise
        print("Configuration validated")
