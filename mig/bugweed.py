#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# bugweed - a simple helper to locate simple error in the project code.
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Grep for obvious errors in pylint output for all code"""

import os
import sys

from codegrep import py_code_files

if '__main__' == __name__:
    if len(sys.argv) != 1:
        print 'Usage: %s' % sys.argv[0]
        print 'Grep for obvious errors in all code files'
        sys.exit(1)

    command = "pylint -E %s" % (' '.join(py_code_files))
    print "Bug weeding command: %s" % command
    print "*** Not all lines reported are necessarily errors ***"
    print
    os.system(command)
