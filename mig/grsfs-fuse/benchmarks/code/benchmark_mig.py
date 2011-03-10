#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# benchmark_mig - [insert a few words of module description on this line]
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


import os, sys, timeit, pprint

# dd if=/dev/urandom of=readfile bs=1048576 count=100

    
def cycle(data):
    #sys.stdout.write('.')
    def nodot(item): return item[0] != '.'
    
    write_fd = open("./file", "wb")
    write_fd.write(data)
    write_fd.close()
    
    os.symlink("./file", "./symlinkedfile")
    os.stat("./symlinkedfile")
    for f in filter(nodot, os.listdir('.')):
        os.lstat(f)
    read_fd = open("./symlinkedfile", "rb")
    read_fd.close()
    
    read_fd = open("./file", "rb")
    read_fd.close()
    
    os.rename("./symlinkedfile", "./symlinkedfile2")
    os.unlink("./symlinkedfile2")
    os.unlink("./file")
    #done
    
def main():
    """docstring for main"""
    setup = "import os; from __main__ import cycle; data_fd = open('/dev/urandom', 'rb'); data = data_fd.read(1130); data_fd.close()"
    
    read_results = []
    read_results.append(min(timeit.repeat("cycle(data)", setup = setup, repeat=3, number=10000)))

    pp = pprint.PrettyPrinter()
    pp.pprint(read_results)
    
if __name__ == '__main__':
    main()