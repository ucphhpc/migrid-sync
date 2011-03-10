#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# nettest_spare - [insert a few words of module description on this line]
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

import sys, time, os
from core.entities import *
from core.aux import *
from core.configuration import *

import core.kernel as kernel


def main():
    # Server instance started, now start a spare instance and see what happens
    
    opt = Configuration()
    opt.forcedinitialtype = 'spare'
    opt.backingstore = 'backingstoretmp'
    opt.serverport = 8001
    opt.initial_connect_list = [('localhost', 8000)] 
    opt.backingstorestate = '../tests/nettest_client.bsc'
    opt.validate()
    
    k = kernel.Kernel(opt)
    k.fsinit()
    print "Spare instance started"
    
    
    print "Getattr on '/':", 
    ret = k.getattr(None, "/")
    assert ret is not None and ret >= 1 # breaks if not int
    print ret
    print "Success"
    
    #d = GRSDirectory('/')
    print "Readdir on '/':",
    ret = k.readdir(None, "/", 0)
    assert ret is not None and ret >= 1 # breaks if not int
    print ret
    print "Success"
    
    print "Attempting to read /hello file"
    f = GRSFile('/hello', os.O_RDONLY)
    assert f.file is not None and f.file >= 1
    print f.read(-1, 0)

    print "Sleeping ten seconds before trying again"
    time.sleep(10)
    print "Attempting to read /hello file"
    f = GRSFile('/hello', os.O_RDONLY)
    assert f.file is not None and f.file >= 1
    print f.read(-1, 0)


if __name__ == '__main__':
    main()

