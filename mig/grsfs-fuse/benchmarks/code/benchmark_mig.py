#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# benchmark_mig - benchmark typical MiG file access
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

"""Benchmark emulating typical MiG file access"""
from __future__ import print_function

import os
import sys
import getopt
import timeit
import pprint

# dd if=/dev/urandom of=readfile bs=1048576 count=100

    
def default_configuration():
    """Return dictionary with default configuration values"""
    conf = {'repeat': 3, 'number': 10000, 'data_bytes': 1130}
    return conf

def usage():
    """Usage help"""
    print("Usage: %s" % sys.argv[0])
    print("Run MiG emulating benchmark")
    print("Options and default values:")
    for (key, val) in default_configuration().items():
        print("--%s: %s" % (key, val))
                
def cycle(data):
    """Run create, symlink, stat, read, rename and unlink cycle"""
    write_fd = open("./file", "wb")
    write_fd.write(data)
    write_fd.close()
    
    os.symlink("./file", "./symlinkedfile")
    os.stat("./symlinkedfile")
    for name in [i for i in os.listdir('.') if i[0] != '.']:
        os.lstat(name)
    read_fd = open("./symlinkedfile", "rb")
    read_fd.close()
    
    read_fd = open("./file", "rb")
    read_fd.close()
    
    os.rename("./symlinkedfile", "./symlinkedfile2")
    os.unlink("./symlinkedfile2")
    os.unlink("./file")
    
def main(conf):
    """Run timed benchmark"""
    read_results = []
    read_results.append(min(timeit.repeat("cycle(data)", setup = conf['setup'],
                        repeat=conf['repeat'], number=conf['number'])))

    out = pprint.PrettyPrinter()
    out.pprint(read_results)


if __name__ == '__main__':
    conf = default_configuration()

    # Parse command line

    try:
        (opts, args) = getopt.getopt(sys.argv[1:],
                                     'd:hn:r:', [
            'data-bytes=',
            'help',
            'number=',
            'repeat=',
            ])
    except getopt.GetoptError as err:
        print('Error in option parsing: ' + err.msg)
        usage()
        sys.exit(1)
        
    for (opt, val) in opts:
        if opt in ('-d', '--data-bytes'):
            try:
                conf["data_bytes"] = int(val)
            except ValueError as err:
                print('Error in parsing %s value: %s' % (opt, err))
                sys.exit(1)
        elif opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('-n', '--number'):
            try:
                conf["number"] = int(val)
            except ValueError as err:
                print('Error in parsing %s value: %s' % (opt, err))
                sys.exit(1)
        elif opt in ('-r', '--repeat'):
            try:
                conf["repeat"] = int(val)
            except ValueError as err:
                print('Error in parsing %s value: %s' % (opt, err))
                sys.exit(1)
        else:
            print("unknown option: %s" % opt)
            usage()
            sys.exit(1)
    conf['setup'] = """
import os
from __main__ import cycle
data_fd = open('/dev/urandom', 'rb')
data = data_fd.read(%(data_bytes)d)
data_fd.close()""" % conf
    main(conf)
