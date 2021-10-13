#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# testio - test server io module
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""This module tests the server IO functions from Xfile and Xos."""
from __future__ import print_function

import os
import sys

# NOTE: dummy init before inline compile in code to make pylint happy
LOCK_EX = LOCK_SH = None


def run_test(class_name):
    file_class = eval(class_name)

    # Creating a dir for test to avoid clashing with local FS

    dirname = 'no-such-dir'
    path = '%s/input.txt' % dirname

    print('-creating directory %s' % dirname)

    # ignore missing clean up from previous runs

    try:
        mkdir(dirname)
    except IOError:
        pass
    print('-opening file %s' % path)
    fd = file_class(path, 'w')
    print('-locking for write')
    fd.lock(LOCK_EX)
    print('-file object: %s\n-closed attribute: %s' % (fd, fd.closed))
    print('-seek to 15')
    fd.seek(15)
    print('-truncating')
    fd.truncate()

    print('-writing two single lines and a list of two lines')
    lines = ['This is a test!', 'This is another test!\n',
             'This is a third test!\n', '..and a fourth!\n']
    status = fd.write(lines[0])
    print(status)
    fd.write(lines[1])
    fd.writelines(lines[2:])
    print('-get current file position:')
    position = fd.tell()
    print(position)
    print('-flushing')
    fd.flush()
    print('-unlocking')
    fd.unlock()
    print('-closing file %s' % path)
    fd.close()
    print('-file object: %s\n-closed attribute: %s' % (fd, fd.closed))

    print('-opening file %s' % path)
    fd = file_class(path)
    print('-locking for read')
    fd.lock(LOCK_SH)
    print('-read all lines:')
    lines = fd.readlines()
    print(lines)
    print('-seek to 30')
    fd.seek(30)
    print('-get current file position:')
    position = fd.tell()
    print(position)
    print('-read the rest:')
    rest = fd.read()
    print(rest)
    print('-get current file position:')
    position = fd.tell()
    print(position)
    print('-unlocking')
    fd.unlock()
    print('-closing file %s' % path)
    fd.close()

    print('-calling stat file %s' % path)
    contents = stat(path)
    print(contents)

    print('-listing dir %s' % dirname)
    contents = listdir(dirname)
    print(contents)

    print('-walking dir %s' % dirname)
    generator = walk(dirname)
    print(generator)
    for entry in generator:
        print(entry)

    print('-clean up: remove %s' % path)
    remove(path)
    print('-clean up: rmdir %s' % dirname)
    rmdir(dirname)


type_prefix = 'local'
if len(sys.argv) > 1:
    type_prefix = sys.argv[1]

os_module = '%s%s' % (type_prefix, 'os')
file_class = '%s%s' % (type_prefix.capitalize(), 'File')
file_module = file_class.lower()

# import selected modules

eval(compile('from %s import %s, LOCK_SH, LOCK_EX' % (file_module,
                                                      file_class), '', 'single'))
eval(compile('from %s import mkdir, rmdir, stat, listdir, walk, remove'
             % os_module, '', 'single'))

# now test it

run_test(file_class)
