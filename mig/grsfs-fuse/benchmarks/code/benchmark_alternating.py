#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# benchmark_alternating - benchmark alternating read/write
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

"""Benchmark alternating file reads and writes"""

import os
import sys
import threading
import time
import getopt

clock_fun = time.time
    
def default_configuration():
    """Return dictionary with default configuration values"""
    conf = {'number': 100000, 'data_bytes': 512}
    return conf

def usage():
    """Usage help"""
    print("Usage: %s" % sys.argv[0])
    print("Run alternating benchmark")
    print("Options and default values:")
    for (key, val) in default_configuration().items():
        print("--%s: %s" % (key, val))
                

class Writer(threading.Thread):
    """Writer thread"""
    def __init__(self, start_time, writefile, data, conf):
        threading.Thread.__init__(self)
        self.writefile = writefile
        self.data = data
        self.start_time = start_time
        self.endtime = -1
        self.conf = conf
        
    def run(self):
        """Runner"""
        for _ in xrange(self.conf['number']):
            self.writefile.write(self.data)
            self.writefile.flush()
            #time.sleep(0.001)
        self.endtime = (clock_fun() - self.start_time)
        print "Write finished at %0.3f" % (self.endtime * 1000)
            

class Reader(threading.Thread):
    """Reader thread"""
    def __init__(self, start_time, readfile, conf):
        threading.Thread.__init__(self)
        self.readfile = readfile
        self.start_time = start_time
        self.endtime = -1
        self.conf = conf

    def run(self):
        """Runner"""
        for _ in xrange(self.conf['number']):
            nbytes = len(self.readfile.read(self.conf['data_bytes']))
            if nbytes < self.conf['data_bytes']:
                self.readfile.seek(0)
            #time.sleep(0.001)
        self.endtime = (clock_fun() - self.start_time)
        print "Read finished at %0.3f" % (self.endtime * 1000)

def prepare_files(conf):
    """Set up files used in benchmark"""
    if not os.path.exists("readfile"):
        data = open("/dev/urandom").read(conf['data_bytes'])
        readfile = open("readfile", "wb")
        readfile.write(data)
        readfile.close()
          
def main(conf):
    """Run timed benchmark"""

    # WRITES ONLY

    threads = []

    prepare_files(conf)
    readfile = open("readfile", "rb")
    writefile = open("writefile", "wb")
    data = open("/dev/urandom").read(conf['data_bytes']/8)

    start_time =  clock_fun()

    for _ in xrange(1):
        worker = Writer(start_time, writefile, data, conf)
        threads.append(worker)

    for worker in threads:
        worker.start()

    for worker in threads:
        worker.join()

    end = time.time()
    print "Time for pure writes %d" % (end - start_time)    

    # MIXED MODE 
    threads = []
    readfile = open("readfile", "rb")
    writefile = open("writefile", "wb")
    data = open("/dev/urandom").read(conf['data_bytes']/8)

    start_time =  clock_fun()
    worker = Writer(start_time, writefile, data, conf)
    threads.append(worker)
    for _ in xrange(4):
        worker = Reader(start_time, readfile, conf)
        threads.append(worker)

    for worker in threads:
        worker.start()
        
    for worker in threads:
        worker.join()

    end = time.time()
    
    # READ/ONLY MODE
    print "Time for mixed reads/writes %d" % (end - start_time)    
    threads = []
    readfile = open("readfile", "rb")

    start_time =  clock_fun()

    for _ in xrange(5):
        worker = Reader(start_time, readfile, conf)
        threads.append(worker)

    for worker in threads:
        worker.start()

    for worker in threads:
        worker.join()

    end = time.time()

    print "Time for just reads %d" % (end - start_time)


if __name__ == '__main__':
    conf = default_configuration()

    # Parse command line

    try:
        (opts, args) = getopt.getopt(sys.argv[1:],
                                     'd:hn:', [
            'data-bytes=',
            'help',
            'number=',
            ])
    except getopt.GetoptError, err:
        print('Error in option parsing: ' + err.msg)
        usage()
        sys.exit(1)
        
    for (opt, val) in opts:
        if opt in ('-d', '--data-bytes'):
            try:
                conf["data_bytes"] = int(val)
            except ValueError, err:
                print('Error in parsing %s value: %s' % (opt, err))
                sys.exit(1)
        elif opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('-n', '--number'):
            try:
                conf["number"] = int(val)
            except ValueError, err:
                print('Error in parsing %s value: %s' % (opt, err))
                sys.exit(1)
        else:
            print("unknown option: %s" % opt)
            usage()
            sys.exit(1)
    main(conf)
