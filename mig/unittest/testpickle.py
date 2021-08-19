#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# testpickle - [insert a few words of module description on this line]
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

"""This module tests the server pickle functions."""

from __future__ import print_function

from builtins import range
import sys


def run_test(module_name):
    """test module"""

    path = 'pickle.txt'
    pickle_data = {'abc': 123, 'hey': 'ged', 'red': 0x00}

    print('-saving %s as the pickle: %s' % (pickle_data, path))
    dump(pickle_data, path)

    print('-truncating data in memory')
    pickle_data = None
    print(pickle_data)

    print('-loading pickled data back from file %s' % path)
    pickle_data = load(path)
    print(pickle_data)


module_prefix = 'local'
if len(sys.argv) > 1:
    module_prefix = sys.argv[1]

module_name = '%s%s' % (module_prefix, 'pickle')

# import selected class

print('importing from %s' % module_name)
eval(compile('from %s import *' % module_name, '', 'single'))

# now test it

for i in range(3):
    run_test(module_name)

