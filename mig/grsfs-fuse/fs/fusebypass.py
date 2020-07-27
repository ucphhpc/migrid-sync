#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fusebypass - Simulates a non-network connected master.
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
Created by Jan Wiberg on 2010-03-26.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""
from __future__ import print_function
from __future__ import absolute_import

import errno
import sys
import os

from .core.entities import *
from .core.specialized.aux import *
from .core.configuration import *
from .core import kernel


def main():
    raise Exception("DEPRECATED")
    
    
    
    
    
    
    
    opt = Configuration()
    opt.backingstore = '/tmp/server'
    opt.instance_type = 'master'
    opt.forcedinitialtype = 'master'
    opt.backingstorestate = '../tests/fusebypass.bsc'
    opt.serverport = 8000
    opt.validate()
    
    import pdb
#    pdb.set_trace()
    k = kernel.Kernel(opt)
    k.fsinit()
    print("!! Getattr on '/': %s" % k.getattr(None, "/"))
    
    # d = GRSDirectory('/')
    print("!! Readdir on '/': %s" % k.readdir(None, "/", 0))

    f = GRSFile('/hello', os.O_RDONLY)
    assert f.file is not None and f.file >= 1
    print("!! Read: ", f.read(-1, 0))
    print("!! Success on last test")
    
    import random
    
    print("!! Testing that we detect too few peers correctly")
    filename = '/file%d' % random.randint(1000, 9999)
    w_f = GRSFile(filename, os.O_CREAT|os.O_WRONLY)
    # print "Errno EROFS %d" % errno.EROFS
    assert w_f.file is not None and w_f.file == -30
    print("!! Success on last test")
    
    print("!! Writing to %s" % filename)
    opt.maxcopies = 0
    opt.mincopies = 0
    w_f = GRSFile(filename, os.O_CREAT|os.O_WRONLY)
    # print "Errno EROFS %d" % errno.EROFS
    assert w_f.file is not None and w_f.file >= 1
    w_f.write("Some string goes here %s\n" % random.randint(0, 10000000), 0)
    w_f.flush()
    w_f.release(w_f.flags)
    
    r_f = GRSFile(filename, os.O_RDONLY)
    assert r_f.file is not None and r_f.file >= 1
    print("!! Read: ", r_f.read(-1, 0))
    r_f.release(r_f.flags)

if __name__ == '__main__':
    main()

