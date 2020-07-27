#!/usr/bin/env python
# encoding: utf-8
"""
output.py

Created by Jan Wiberg on 2010-03-21.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""
from __future__ import print_function

import sys
import os



def output_console(result):
    """Given a list of test runs, displays each"""
    def output_test(test):
        """outputs a single line"""
        name, meta, status = test
        ret, why = status
        print("%-20s: %s" % (name, "OK" if ret else "Failed! (%s)" % why))
    
    print("TEST RESULTS")
    print(80*'-')
    for test in result:
        output_test(test)
        
def output_tex(result):
    """docstring for output_tex"""
    def output_test(file, test):
        """outputs a single line"""
        name, meta, status = test
        ret, _ = status
        file.write("%s & %s \\\\" % (name, status))
    texfile = open("testrun.tex", "w")
    
    for test in result:
        output_test(texfile, test)
    
    texfile.close()