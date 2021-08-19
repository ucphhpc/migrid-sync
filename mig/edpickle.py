#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# edpickle - a simple pickled object editor.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Edit pickled objects on disk"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import input
import os
import sys

from mig.shared.serial import pickle


if len(sys.argv) < 2:
    print('Usage: %s PATH' % sys.argv[0])
    print('Edit pickled object in file PATH')
    sys.exit(1)

dirty = False
path = sys.argv[1]
print("opening pickle in %s" % path)
pickle_fd = open(path, 'rb+')
obj = pickle.load(pickle_fd)
print("pickled object loaded as 'obj'")
while True:
    command = input("Enter command: ")
    command = command.lower().strip()
    if command in ['o', 'open']:
        path = input("Path to open: ")
        pickle_fd = open(path, 'rb+')
        obj = pickle.load(pickle_fd)
    elif command in ['h', 'help']:
        print("Valid commands include:")
        print("(d)isplay to display the opened pickled object")
        print("(e)dit to edit the opened pickled object")
        print("(o)pen to open a new pickle file")
        print("(c)lose to close the opened pickled object")
        print("(q)uit to quit pickle editor")
    elif command in ['d', 'display']:
        print(obj)
    elif command in ['e', 'edit']:
        edit = input("Edit command: ")
        # eval(edit)
        eval(compile(edit, 'command-line', 'single'))
        dirty = True
    elif command in ['c', 'close', 'q', 'quit']:
        if dirty:
            flush = input("Modified object not saved - save now?: ")
            if flush.lower() in ('y', 'yes'):
                pickle_fd.seek(0)
                pickle.dump(obj, pickle_fd)
        pickle_fd.close()
        obj = None
        if command in ('q', 'quit'):
            print("Closing")
            break
    else:
        print("unknown command '%s'" % command)
