#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# pickle_file_sizes - [insert a few words of module description on this line]
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

import os
import pickle

from os.path import join, getsize

list = []
base = '/home/mig/mig/wwwuser'
for (root, dirs, files) in os.walk(base):
    for name in files:
        path = join(root, name)
        path_no_base = path.replace(base, '')
        list.append((path_no_base, getsize(path)))

        # print path + " " + str(getsize(path))

output = open('filesizes.pkl', 'wb')

# Pickle dictionary using protocol 0.

pickle.dump(list, output)
output.close()

# print list
