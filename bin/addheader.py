#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addheader - add license header to all code modules.
# Copyright (C) 2009-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Search code tree and add the required header to all python modules."""

from __future__ import absolute_import, print_function

import datetime
import fnmatch
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

from mig.shared.fileio import read_file_lines, read_head_lines, write_file_lines
from mig.shared.projcode import CODE_ROOT, JAVASCRIPT, list_code_files

# Modify these to fit actual project
PROJ_CONSTS = {}
PROJ_CONSTS["project_name"] = "MiG"
PROJ_CONSTS["authors"] = "The MiG Project by the Science HPC Center at UCPH"

PROJ_CONSTS["copyright_year"] = "2003-%d" % datetime.date.today().year

# Set interpreter path and file encoding if not already set in source files
# Use empty string to leave them alone.
PROJ_CONSTS["interpreter_path"] = "/usr/bin/env python"
PROJ_CONSTS["module_encoding"] = "utf-8"

BEGIN_MARKER, END_MARKER = "--- BEGIN_HEADER ---", "--- END_HEADER ---"
BACKUP_MARKER = ".unlicensed"

# Mandatory copyright notice for any license
LICENSE_TEXT = """#
# %(module_name)s - [optionally add short module description on this line]
# Copyright (C) %(copyright_year)s  %(authors)s
"""

# This is the actual GPL version 2 header to match
# http://opensource.org/licenses/GPL-2.0
# Replace text if another license is desired.
# Additionally add a file called COPYING in the root of the distributed source
# with a verbatim copy of the license text:
# wget -O COPYING http://www.gnu.org/licenses/gpl2.txt

LICENSE_TEXT += """#
# This file is part of %(project_name)s.
#
# %(project_name)s is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# %(project_name)s is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA."""


def check_header(path, var_dict, preamble_lines=100):
    """Check if path already has a credible license header. Only looks inside
    the first preamble_size bytes of the file.
    """
    module_preamble = "\n".join(read_head_lines(path, preamble_lines, None))
    return (
        BEGIN_MARKER in module_preamble
        or var_dict["authors"] in module_preamble
    )


def add_header(path, var_dict, explicit_border=True, block_wrap=False):
    """Add the required copyright and license header to module in path.

    The optional explicit_border argument can be set to wrap the license
    text in begin and end lines that are easy to find, so that license can
    be updated or replaced later.
    The optional block_wrap argument is used to explicitly put license lines
    into a block comment where needed. This is useful for languages like C and
    JavaScript where the per-line commenting using hash (#) won't work.
    Creates a '.unlicensed' backup copy of each file changed.
    """
    module_lines = read_file_lines(path, None)
    if not write_file_lines(module_lines, path + BACKUP_MARKER, None):
        print("Failed to create backup of %s - skip!" % path)
        return False
    # Do not truncate any existing unix executable hint (shebang) and encoding
    act = "#!%(interpreter_path)s\n" % var_dict
    if block_wrap:
        enc = ""
    else:
        enc = "# -*- coding: %(module_encoding)s -*-" % var_dict
    lic = LICENSE_TEXT % var_dict
    module_header = []
    if module_lines and module_lines[0].startswith("#!"):
        module_header.append(module_lines[0])
        module_lines = module_lines[1:]
    elif var_dict["interpreter_path"]:
        module_header.append(act)

    if module_lines and module_lines[0].startswith("# -*- coding"):
        module_header.append(module_lines[0])
        module_lines = module_lines[1:]
    elif var_dict["module_encoding"]:
        module_header.append(enc)

    if explicit_border:
        lic = """
#
# %s
#
%s
#
# %s
#
""" % (
            BEGIN_MARKER,
            lic,
            END_MARKER,
        )
    if block_wrap:
        lic = (
            """
/*
%s
*/
"""
            % lic
        )

    module_header.append(lic)
    # Make sure there's a blank line between license header and code
    if module_lines and module_lines[0].strip():
        module_header.append("\n")

    updated_lines = [i % var_dict for i in module_header + module_lines]

    if not write_file_lines(updated_lines, path, None):
        print("Failed to write %s with added headers!" % path)
        return False
    # print("DEBUG: wrote %s with added headers!" % path)
    return True


def main(argv):
    """Run header addition for given argv."""
    target = os.getcwd()
    if len(argv) > 1:
        target = os.path.abspath(argv[1])
    mig_code_base = target
    if len(argv) > 2:
        mig_code_base = os.path.abspath(argv[2])

    for root, _, files in os.walk(target):

        # skip all dot dirs - they are from repos etc and _not_ jobs

        if root.find(os.sep + ".") != -1:
            continue
        for name in files:
            src_path = os.path.join(root, name)
            if os.path.islink(src_path):
                continue
            if src_path.endswith(BACKUP_MARKER):
                continue
            print("Inspecting %s" % src_path)
            for pattern in list_code_files():
                needs_block = pattern in list_code_files([JAVASCRIPT])
                pattern = os.path.normpath(
                    os.path.join(mig_code_base, CODE_ROOT, pattern)
                )

                # print("DEBUG: Testing %s against %s" % (src_path, pattern))

                if src_path == pattern or fnmatch.fnmatch(src_path, pattern):
                    print("Matched %s against %s" % (src_path, pattern))
                    PROJ_CONSTS["module_name"] = name.replace(".py", "")
                    if check_header(src_path, PROJ_CONSTS):
                        print("Skip %s with existing header" % src_path)
                        continue
                    add_header(src_path, PROJ_CONSTS, block_wrap=needs_block)
                # else:
                #    print('DEBUG: %s does not match %s' % (src_path, pattern))

    print()
    print("Added license headers to code in %s" % target)
    print()
    print("Don't forget to include COPYING file in root of source, e.g. run:")
    print("wget -O COPYING http://www.gnu.org/licenses/gpl2.txt")
    print("if using the default GPL v2 license here.")


if __name__ == "__main__":
    main(sys.argv)
