#!/usr/bin/env python
# encoding: utf-8
"""
testnet.py

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

