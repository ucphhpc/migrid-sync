#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# benchmark_ro - [insert a few words of module description on this line]
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
    #assert len(l) == size
    


def main():
    """docstring for main"""
    setup_read = "import os; from __main__ import read_mark; f = open('readfile', 'r')"
    
    read_sequence = [1, 2, 16, 256, 512, 1024, 2048, 4096, 8192, 16384]
    read_results = []

    for s in read_sequence:
        read_results.append((s, max(timeit.repeat("read_mark(%s, f)" % s, setup = setup_read, repeat=3, number=1000))))

    pp = pprint.PrettyPrinter()
    pp.pprint(read_results)
    
if __name__ == '__main__':
    main()