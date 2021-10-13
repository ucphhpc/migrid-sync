#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# TestMaxPrice - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

# Test parsing of a number of price strings

from __future__ import print_function
import time
import sys
import math

import Scheduler


def test(scheduler, s):
    t = 95.7
    replace_map = {'exec_delay': repr(t)}
    price = scheduler.EvalPrice(s, replace_map)
    if price >= 0:
        print("string '", s, "' gave price of", price, \
            'with exec_delay', t)
    else:
        print("string '", s, "' failed to parse with exec_delay", t)


        # unsafe_val = eval(s)
        # print "unsafe eval of string '",s,"' gave result",unsafe_val

# Main

scheduler = Scheduler.Scheduler(86400)

strings = [
    '5',
    '4.5',
    '4+7',
    '4.43*3/2-4.4',
    '25 % 7',
    '102.5-exec_delay',
    '2*(201-exec_delay)**2',
    'math.cos(2)',
    'True and 4',
    '(exec_delay < 100 and 1000) or 10',
    '[1,2,1]',
    'abc',
    ]

for s in strings:
    test(scheduler, s)

sys.exit(0)
