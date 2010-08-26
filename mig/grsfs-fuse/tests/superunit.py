#!/usr/bin/env python
# encoding: utf-8
"""
superunit.py

contains common functionality that test units can draw on.

Created by Jan Wiberg on 2010-03-19.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""

import sys, os, inspect, subprocess
import constants

def todo(msg = ""):
    me = inspect.stack()[1]
    daddy = inspect.stack()[2][3]
    print "Fun %s:%s() not complete. Msg '%s'" % (me[1], me[3], msg)

def run_external(cmd):
    """docstring for run_external"""
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    p.wait()
    return (out, err, p.returncode)

def return_status(f):
    """wraps a function for easy return. Use like this: return_status(lambda: fun(args))"""
    try:
        ret = f()
        if ret:
            return (constants.RET_OK, None)
    except Exception,v:
        return (constants.RET_FAIL, v)

class superunit:
    def __init__(self):
        pass

