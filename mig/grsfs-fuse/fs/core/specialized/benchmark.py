#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# benchmark - [insert a few words of module description on this line]
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

"""
Computes some suitability score for this node

Created by Jan Wiberg on 2010-03-21.
Copyright (c) 2010 Jan Wiberg. All rights reserved.
"""

from __future__ import division

import random
import time


# adapted from iotest by benjamin schweizer http://benjamin-schweizer.de/files/iotest/
def _iotest(fh, eof, blocksize=512, t=10): 
    """io test"""

    io_num = 0
    start_ts = time.time()
    while time.time() < start_ts+t:
        io_num += 1
        pos = random.randint(0, eof - blocksize)
        fh.seek(pos)
        blockdata = fh.read(blocksize)
    end_ts = time.time()

    total_ts = end_ts - start_ts

    io_s = io_num // total_ts
    by_s = int(blocksize*io_num/total_ts)
    #print " %sB blocks: %6.1f IOs/s, %sB/s" % (greek(blocksize), io_s, greek(by_s))

    return io_num // total_ts

def _iostart(dev, t = 1, maxblock = 4096):# increase t to get a more accurate test.
    blocksize = 512
    try:
        fh = open(dev, 'r')
        fh.seek(0,2)
        eof = fh.tell()

        #print("%s, %sB:" % (dev, greek(eof)))

        iops = 2
        scores = []
        while blocksize < maxblock: #iops > 1:
            iops = _iotest(fh, eof, blocksize, t)
            blocksize *= 2
            scores.append(iops)
            
        return sum(scores) // len(scores)
    except IOError as xxx_todo_changeme:
        (err_no, err_str) = xxx_todo_changeme.args
        raise SystemExit(err_str)
        

def compute_score(options):
    """target: a path on the same disk as """
    if options.benchmark_fast_start:
        import random
        return random.randint(1, 1000)
        
    import os, statvfs, time
    f = os.statvfs(options.freespace_target)
    disk_free_gb = (f[statvfs.F_BAVAIL] * f[statvfs.F_FRSIZE]) // 1073741824
    
    raw_io_average = _iostart(options.iobench_target)
    #print "\tbenched at %d/%d before bias" % (disk_free_gb, raw_io_average)
    score = (max((min(disk_free_gb, options.benchmark_max_gb_free) - options.benchmark_min_gb_free), options.benchmark_min_free_score) // (options.benchmark_max_gb_free - options.benchmark_min_gb_free)) * raw_io_average
    return score
    
