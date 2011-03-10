#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# benchmark_raw - [insert a few words of module description on this line]
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


import os, sys, timeit, pprint, threading

# dd if=/dev/urandom of=readfile bs=1048576 count=100


def read_mark(size, f):
    #print "Reading %d from %s" % (size, f)
    #f.seek(0)
    l = f.read(size)
    assert len(l) == size
    
def write_mark(size, f, data):
    f.write(data[:size])
    f.flush()
    os.fsync(f)
    


def main():
    """docstring for main"""
    setup_read = "import os; from __main__ import read_mark; f = open('readfile', 'r')"
    setup_write = "import os; from __main__ import write_mark; data_f = open('/dev/urandom', 'r'); f = open('writefile', 'w'); f.truncate(0); data = data_f.read(262144)"  
    
    read_sequence = [1, 2, 16, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 262144]
    write_sequence = [1, 2, 16, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 262144]
    read_results = []
    write_results = []

    for s in read_sequence:
        read_results.append((s, min(timeit.repeat("read_mark(%s, f)" % s, setup = setup_read, repeat=3, number=1000))))

    for s in write_sequence:
        write_results.append((s, min(timeit.repeat("write_mark(%s, f, data)" % s, setup = setup_write, repeat=3, number=1000))))
    pp = pprint.PrettyPrinter()
    pp.pprint(read_results)
    pp.pprint(write_results)
    
if __name__ == '__main__':
    main()