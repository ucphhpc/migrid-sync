#!/usr/bin/env python
# encoding: utf-8
"""
testrunner.py

Created by Jan Wiberg on 2010-03-19.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""
from __future__ import print_function

import sys
from optparse import OptionParser, OptionGroup
import subprocess
import os
from threading import Thread
import time
import constants 
from output import *


help_message = '''
The help message goes here.
'''
        
def run_tests(options):
    """docstring for run_tests"""
    
    results = []
    
    print("Run with options %s" % options)
    lst = os.listdir(constants.TEST_UNIT_DIR)
    lst.sort()
    res = {}
    for name in [os.path.splitext(f) for f in lst if f.endswith(".py") and not f.startswith("__init__")]:
        name = constants.TEST_UNIT_DIR + "."+name[0];
        mod = __import__(name,fromlist=['*'])
        real_name = ''.join(name.split('.')[1:])
        res[real_name] = mod            

    for r in res:
        status = res[r].main(options)
        results.append((r, res[r].meta, status))
        
        
    output_console(results)

class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg


        def main():
            usage = 'usage: %prog [options]'
            parser = OptionParser(usage=usage, version="GRSfs %prog version 0.01 (dev)")
            parser.add_option('-v', '--verbosity', dest='verbosity', type='int', default=1, help='How much information should be logged and printed to the screen. Should be an integer between 1 and 3, defaults to 1.')
            parser.add_option('--filter', dest='filter',  help='Limit the testrun to just tests that match the pattern.')

            options, args = parser.parse_args()
            if args is None or len(args) == 0: 
                parser.error("You need to specify the target filesystem as a positional argument.")

            options.target = args[0]
            if len(args) > 1:
                options.replica1 = args[1]
            if len(args) > 2:
                options.replica2 = args[2]

            run_tests( options )

        if __name__ == "__main__":
            sys.exit(main())
