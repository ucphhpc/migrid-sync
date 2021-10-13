#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# countorg - display count for each unique organizational prefix read on stdin
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

"""Show count for each unique DN organizational prefix given on stdin.

Use e.g. as in
./searchusers.py -f distinguished_name | grep -v 'Matching users' | python countorg.py
"""
from __future__ import print_function

import fileinput

if __name__ == '__main__':
    org_map = {}
    for line in fileinput.input():
        org_prefix = line.split('/OU=', 1)[0]
        if org_prefix not in org_map:
            org_map[org_prefix] = 0
        org_map[org_prefix] += 1
    org_list = list(org_map.items())
    org_list.sort()
    for (org, cnt) in org_list:
        print('%d\t%s' % (cnt, org))
