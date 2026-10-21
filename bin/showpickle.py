#!/usr/bin/env python
#
# --- BEGIN_HEADER ---
#
# showpickle - a simple pickled object viewer.
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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

"""Show pickled objects on disk."""

import getopt
import os
import sys
from collections.abc import Iterable

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

from mig.shared.serial import load

SERIALIZER = "pickle"


def usage(name="showpickle.py"):
    """Usage help"""
    print("""Show pickled python data from file.
Usage:
%(name)s [SHOW_OPTIONS] PATH [PATH ..]
Where SHOW_OPTIONS may be one or more of:
   -h                  Show this help
   -s SELECTOR         Show only SELECTOR value for dict or sequence
   -v                  Verbose output

Each PATH will be loaded and shown and SELECTOR can be a key to show if data
is a dict or index if it is a sequence.
""" % {"name": name})


def main(args, select=None, verbose=False):
    """Run load and show pickle optionally limited to select."""
    errors = 0
    out = ""
    # Output path as prefix if more than one path is passed
    path_prefix = False
    if args[1:]:
        path_prefix = True
    for path in args:
        if path_prefix:
            out += "%s: " % path
        if verbose:
            print("loading pickle in %s" % path)
        try:
            obj = load(path, serializer=SERIALIZER)
            if isinstance(obj, dict) and select is not None:
                out += "data[%r]: %s" % (select, obj.get(select, "**UNSET**"))
            elif isinstance(obj, Iterable) and select is not None:
                out += "data[%s]: %s" % (select, obj[int(select)])
            else:
                out += "%s" % obj
        except Exception as exc:
            out += "failed to load: %s" % exc
            errors += 1
        out += "\n"
    print(out.strip())
    if verbose:
        print("completed with %d errors" % errors)
    return errors


if __name__ == "__main__":
    opt_args = "hs:v"
    select = None
    verbose = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], opt_args)
    except getopt.GetoptError as err:
        print("Error: ", err.msg)
        usage()
        sys.exit(1)

    for opt, val in opts:
        if opt == "-h":
            usage()
            sys.exit(0)
        elif opt == "-s":
            select = val
        elif opt == "-v":
            verbose = True
        else:
            print("Error: %s not supported!" % opt)
            usage()
            sys.exit(0)

    if not args:
        usage()
        sys.exit(1)
    err = main(args, select, verbose)
    sys.exit(err)
