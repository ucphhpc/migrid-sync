#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# benchmark_raw - benchmark raw read and write access
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

"""Benchmark of raw read write access"""
from __future__ import print_function

import os
import sys
import timeit
import pprint
import getopt

# dd if=/dev/urandom of=readfile bs=1048576 count=100
    
def default_configuration():
    """Return dictionary with default configuration values"""
    conf = {'repeat': 3, 'number': 1000, 'data_bytes': 262144}
    return conf

def usage():
    """Usage help"""
    print("Usage: %s" % sys.argv[0])
    print("Run raw benchmark")
    print("Options and default values:")
    for (key, val) in default_configuration().items():
        print("--%s: %s" % (key, val))

def read_mark(size, filehandle):
    """Read size bytes from filehandle"""
    #print "Reading %d from %s" % (size, filehandle)
    #filehandle.seek(0)
    out = filehandle.read(size)
    #assert len(out) == size
    
def write_mark(size, filehandle, data):
    """Write size bytes from data to filehandle"""
    filehandle.write(data[:size])
    filehandle.flush()
    os.fsync(filehandle)

def prepare_files(conf):
    """Set up files used in benchmark"""
    if not os.path.exists("readfile"):
        data = open("/dev/urandom").read(conf['data_bytes'])
        readfile = open("readfile", "wb")
        readfile.write(data)
        readfile.close()

def main(conf):
    """Run timed benchmark"""
    read_sequence = [1, 2, 16, 256, 512, 1024, 2048, 4096, 8192, 16384,
                     32768, 65536, 262144]
    write_sequence = [1, 2, 16, 256, 512, 1024, 2048, 4096, 8192, 16384,
                      32768, 65536, 262144]
    read_results = []
    write_results = []

    prepare_files(conf)

    for i in read_sequence:
        read_results.append((i, min(
            timeit.repeat("read_mark(%s, filehandle)" % i,
                          setup = conf['setup_read'], repeat=conf['repeat'],
                          number=conf['number']))))

    for i in write_sequence:
        write_results.append((i, min(
            timeit.repeat("write_mark(%s, filehandle, data)" % i,
                          setup = conf['setup_write'], repeat=conf['repeat'],
                          number=conf['number']))))
    out = pprint.PrettyPrinter()
    out.pprint(read_results)
    out.pprint(write_results)


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
    conf['setup_read'] = """
import os
from __main__ import read_mark
filehandle = open('readfile', 'r')"""
    conf['setup_write'] = """
import os
from __main__ import write_mark
data_f = open('/dev/urandom', 'r')
filehandle = open('writefile', 'w')
filehandle.truncate(0)
data = data_f.read(%(data_bytes)d)""" % conf
    main(conf)
