#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# TestSafeEval - [insert a few words of module description on this line]
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


# Test correct sfae handling of a number of expressions

import sys
import math

import SafeEval

def test(expr):
    #indent = "\t\t\t\t\t"
    indent = "\t"
    try:
        print "testing expr:", expr
        val = SafeEval.math_expr_eval(expr)
        print indent,"[ OK ]:",indent,val
    except ValueError, v:
        print indent,"[ ERROR ]:",indent,"ValueError:", v
    except Exception, e:
        print indent,"[ ERROR ]:",indent,"Exception:", e
# end test


# Main

#strings = ['5', '4.5', '1+4.43*3/2-4.4', '25 % 7', '4**2', 'math.cos(2)', 'math.exp(2)+math.sin(0.3)', 'True and 4', '[1,2,1]', 'math.exp(abs(-2))', 'sys.exit(255)', 'abc', 'math.exp(2)+sys.exit(254)', 'math.exp(2,2)']
strings = ['5', '4.5', '1+4.43*3/2-4.4', '25 % 7', '4**2', 'cos(2)', 'exp(2)+sin(0.3)', 'True and 4', '[1,2,1]', 'exp(abs(-2))', 'sys.exit(255)', 'abc', 'exp(2)+sys.exit(254)', 'exp(2,2)']

for s in strings:
    test(s)

sys.exit(0)
