#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# edpickle - a simple pickled object editor.
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Edit pickled objects on disk."""

from __future__ import absolute_import, print_function

# NOTE: keep backwards compatible input reader on python2
try:
    import raw_input as read_input
except ImportError:
    from builtins import input as read_input

import os
import sys

# Try to import mig to assure we have a suitable python module load path
try:
    import mig
except ImportError:
    mig = None  # type: ignore[assignment]

if mig is None:
    # NOTE: include cmd parent path in search path for mig.X imports to work
    MIG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
    print("Using mig installation in %s" % MIG_ROOT)
    sys.path.append(MIG_ROOT)

from mig.shared.serial import dump, load

SERIALIZER = "pickle"


def main(argv):
    """Run interactive session."""
    dirty = False
    path = None
    obj = None
    if argv[1:]:
        path = argv[1]
        print("opening pickle in %s" % path)
        obj = load(path, serializer=SERIALIZER)
        print("pickled object loaded as 'obj'")
    else:
        print("ready to open pickle - type 'help' for instructions")

    while True:
        command = input("Enter command: ")
        command = command.lower().strip()
        if command in ["o", "open"]:
            path = read_input("Path to open: ")
            obj = load(path, serializer=SERIALIZER)
        elif command in ["h", "help"]:
            print("Valid commands include:")
            print("(d)isplay to display the opened pickled object")
            print("(e)dit to edit the opened pickled object")
            print("(o)pen to open a new pickle file")
            print("(c)lose to close the opened pickled object")
            print("(q)uit to quit pickle editor")
        elif command in ["d", "display"]:
            print(obj)
        elif command in ["e", "edit"]:
            edit = read_input("Edit command: ")
            # eval(edit)
            eval(compile(edit, "command-line", "single"))
            dirty = True
        elif command in ["c", "close", "q", "quit"]:
            if dirty:
                flush = read_input("Modified object not saved - save now?: ")
                if flush.lower() in ("y", "yes"):
                    while not path:
                        path = read_input("Object save path: ").strip()
                    dump(obj, path, serializer=SERIALIZER)
                    dirty = False
            obj = None
            if command in ("q", "quit"):
                print("Closing")
                break
        else:
            print("unknown command '%s'" % command)


if __name__ == "__main__":
    if len(sys.argv) not in (1, 2):
        print("Usage: %s [PATH]" % sys.argv[0])
        print("Edit pickled object file - load from PATH if provided")
        sys.exit(1)
    main(sys.argv)
