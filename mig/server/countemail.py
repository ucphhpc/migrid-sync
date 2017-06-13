#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# countemail - display count for each unique email domain read on stdin
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Show count for each unique email domain given on stdin.

Use e.g. as in
./searchusers.py -f email | grep -v 'Matching users' | python countemail.py
"""

import fileinput

if __name__ == '__main__':
    domain_map = {}
    for line in fileinput.input():
        domain_suffix = line.split('@', 1)[1].strip()
        if not domain_map.has_key(domain_suffix):
            domain_map[domain_suffix] = 0
        domain_map[domain_suffix] += 1
    domain_list = domain_map.items()
    domain_list.sort()
    for (domain, cnt) in domain_list:
        print '%d\t%s' % (cnt, domain)
