#!/usr/bin/env python
# encoding: utf-8
"""
kernel_test - tests some kernel functions in standalone mode

Created by Jan Wiberg on 2010-03-29.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""

import sys, time, os
from core.entities import *
from core.configuration import *

import core.kernel as kernel


def main():
    opt = Configuration()
    node_id = 8000 
    opt.backingstore = '/tmp/node%s' % node_id
    opt.backingstorestate = '../tests/nettest_node%s.bsc' % node_id
    opt.serverport = node_id
    opt.maxcopies = 0
    opt.mincopies = 0
    opt.logquiet = False
    opt.logverbose = True
    opt.logverbosity = 3
    opt.validate()


    
    k = kernel.Kernel(opt)
    k.fsinit()
    test_filename = 'hello'
    test_path = os.path.join(os.sep, test_filename)
    print "Instance started"
    try:        
        
        print "!! Getattr on '/': %s" % k.getattr("/", None)

        print "!! Readdir on '/': %s" % k.readdir("/", 0, None)

        
        # Root dir may be empty
        if test_filename in k.readdir("/", 0, None):
            f = GRSFile(test_path, os.O_RDONLY)
    
            assert f.file is not None and f.file >= 1
            print "!! Read %s:\n%s" % (test_path, f.read(-1, 0))
            print "!! Success on last test"
        
            attrs = f.fgetattr()
            print "!! Fgetattrs %s" % attrs


        import random
        filename = '/file%d' % random.randint(1000, 9999)
    
        print "!! Writing to %s" % filename
        w_f = GRSFile(filename, os.O_CREAT|os.O_WRONLY)
        # print "Errno EROFS %d" % errno.EROFS
        assert w_f.file is not None and w_f.file >= 1
        w_f.write("Some string goes here %s\n" % random.randint(0, 10000000), 0)
        w_f.flush()
        w_f.release(w_f.open_args[1])
    
        r_f = GRSFile(filename, os.O_RDONLY)
        assert r_f.file is not None and r_f.file >= 1
        print "!! Read: ", r_f.read(-1, 0)
        r_f.release(r_f.open_args[1])

        # append mode
        filename = "/file_a"
        print "!! appending to %s" % filename
        w_f = GRSFile(filename, os.O_CREAT|os.O_WRONLY|os.O_APPEND)
        assert w_f.file is not None and w_f.file >= 1
        w_f.write("mary", 0)
        w_f.flush()
        w_f.release(w_f.open_args[1])
        print "!! -- first part written"
        w_f = GRSFile(filename, os.O_WRONLY|os.O_APPEND)
        assert w_f.file is not None and w_f.file >= 1
        w_f.write("mary", 5)
        w_f.flush()
        w_f.release(w_f.open_args[1])
    
        r_f = GRSFile(filename, os.O_RDONLY)
        assert r_f.file is not None and r_f.file >= 1
        print "!! Read: ", r_f.read(-1, 0)
        r_f.release(r_f.open_args[1])

        # Root dir may be empty
        if test_filename in k.readdir("/", 0, None):
            k.utime(test_path, (time.time(), time.time()), None)
        else:
            print "!! Creating test file %s for future runs" % test_path
            w_f = GRSFile(test_path, os.O_CREAT|os.O_WRONLY)
            assert w_f.file is not None and w_f.file >= 1
            w_f.write("Hello grid file system!\n", 0)
            w_f.flush()
            w_f.release(w_f.open_args[1])
    finally:
        k.fshalt()
    

if __name__ == '__main__':
    main()

