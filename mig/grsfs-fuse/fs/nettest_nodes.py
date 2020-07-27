#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# nettest_nodes - [insert a few words of module description on this line]
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
Created by Jan Wiberg on 2010-03-29.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""
from __future__ import print_function
from __future__ import absolute_import

import sys, time, os
from .core.entities import *
from .core.configuration import *

from .core import kernel
import yappi


def main():
    # yappi.start()
    if len(sys.argv) < 2:
        print("Must supply node id [0,1,2] as argument")
        sys.exit(1)
        
    no = sys.argv[1]
    do_write = len(sys.argv) >= 3 
    opt = Configuration()
    node_id = 8000 + int(no)
    opt.backingstore = '/tmp/node%s' % node_id
    if node_id > 8000: # anti-idiot
        opt.initial_connect_list = [('ubuntu1', 8000)]
    opt.backingstorestate = '../tests/nettest_node%s.bsc' % no
    opt.serverport = node_id
    opt.logverbosity = 3
    # opt.maxcopies = 0
    # opt.mincopies = 0
    opt.validate()


    
    k = kernel.Kernel(opt)
    k.fsinit()
    print("Instance started")
    #  instance started, now start other instances and see what happens
    
    wait_time = (2 if opt.mincopies == 0 else 15)
    print("Sleeping %d seconds to allow others to get off the ground" % wait_time)
    time.sleep(wait_time / 2)
    print("Attempting actions")
    
    try:        
        
        print("!! Getattr on '/': %s" % k.getattr("/", None))

        print("!! Readdir on '/': %s" % k.readdir("/", 0, None))

        f = GRSFile('/hello', os.O_RDONLY)
    
        assert f.file is not None and f.file >= 1
        print("!! Read: ", f.read(-1, 0))
        print("!! Success on last test")
        
        attrs = f.fgetattr()
        print("!! Fgetattrs %s" % attrs)

        if not do_write or k.state.get_instancetype() > 1:
            print("!!!! No writes requested or not master")
            time.sleep(90)
            return 

        opt.maxcopies = 1
        opt.mincopies = 1

        import random
        filename = '/file%d' % random.randint(1000, 9999)
    
        print("!! Writing to %s" % filename)
        w_f = GRSFile(filename, os.O_CREAT|os.O_WRONLY)
        # print "Errno EROFS %d" % errno.EROFS
        assert w_f.file is not None and w_f.file >= 1
        w_f.write("Some string goes here %s\n" % random.randint(0, 10000000), 0)
        w_f.flush()
        w_f.release(w_f.open_args[1])
    
        r_f = GRSFile(filename, os.O_RDONLY)
        assert r_f.file is not None and r_f.file >= 1
        print("!! Read: ", r_f.read(-1, 0))
        r_f.release(r_f.open_args[1])
        
        k.utime("/hello", (time.time(), time.time()), None)
    
    finally:
        k.fshalt()
    

if __name__ == '__main__':
    main()

