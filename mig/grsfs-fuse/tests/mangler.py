#!/usr/bin/python
"""
    Does quirky things with the kernel module to test some internal stuff
"""


import sys
import os
from core.entities import *
from core.aux import *
from core.configuration import *
from core.state import State

import core.kernel as kernel
import errno


def main():
    opt = Configuration()
    opt.backing_store = '/tmp'
    opt.instance_type = 'master'
    opt.forcedinitialtype = 'master'
    opt.backingstorestate = '../tests/mangler.bsc'
    opt.server_port = 8000
    opt.validate()
    
    # fake, and never instantiated
    opt2 = Configuration()
    opt2.backing_store = '/tmp'
    opt2.instance_type = 'master'
    opt2.forcedinitialtype = 'master'
    opt2.backingstorestate = '../tests/mangler2.bsc'
    opt2.server_port = 6666
    opt2.initial_connect_list = [('blah', 3330)] 
    opt2.validate()    
    
    import pdb
#    pdb.set_trace()
    k = kernel.Kernel(opt)
    k.fsinit()
    
    some_state = State(opt2,("me2", 6666)) # also never instantiated
    # print "Intersection %s" % k.state.member_intersection(some_state)
    # print "Union %s" % k.state.member_union(some_state)
    # print "Complement %s" % k.state.member_complement(some_state)

if __name__ == '__main__':
    main()

