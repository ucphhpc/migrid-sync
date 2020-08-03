#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addheader - add license header to all code modules.
# Copyright (C) 2009-2020  Jonas Bardino
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

"""Search code tree and add the required header to all python modules"""
from __future__ import print_function
from __future__ import absolute_import

import datetime
import fnmatch
import os
import sys

from mig.shared.projcode import code_root, py_code_files, sh_code_files, \
    js_code_files

# Modify these to fit actual project
proj_vars = {}
proj_vars['project_name'] = "MiG"
proj_vars['authors'] = 'The MiG Project lead by Brian Vinter'
proj_vars['copyright_year'] = '2003-%d' % datetime.date.today().year

# Set interpreter path and file encoding if not already set in source files
# Use empty string to leave them alone.
proj_vars['interpreter_path'] = '/usr/bin/python'
proj_vars['module_encoding'] = 'utf-8'

begin_marker, end_marker = "--- BEGIN_HEADER ---", "--- END_HEADER ---"

# Mandatory copyright notice for any license
license_text = """#
# %(module_name)s - [optionally add short module description on this line]
# Copyright (C) %(copyright_year)s  %(authors)s
"""

# This is the actual GPL version 2 header to match
# http://opensource.org/licenses/GPL-2.0
# Replace text if another license is desired.
# Additionally add a file called COPYING in the root of the distributed source
# with a verbatim copy of the license text:
# wget -O COPYING http://www.gnu.org/licenses/gpl2.txt

license_text += """#
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


def check_header(path, var_dict, preamble_size=4096):
    """Check if path already has a credible license header. Only looks inside
    the first preamble_size bytes of the file.
    """
    module_fd = open(path, 'r')
    module_preamble = module_fd.read(4096)
    module_fd.close()
    if begin_marker in module_preamble or \
            proj_vars['authors'] in module_preamble:
        return True
    else:
        return False


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

    module_fd = open(path, 'r')
    module_lines = module_fd.readlines()
    module_fd.close()
    backup_fd = open(path + '.unlicensed', 'w')
    backup_fd.writelines(module_lines)
    backup_fd.close()
    # Do not truncate any existing unix executable hint and encoding
    act = '#!%(interpreter_path)s' % var_dict
    if block_wrap:
        enc = ''
    else:
        enc = '# -*- coding: %(module_encoding)s -*-' % var_dict
    lic = license_text % var_dict
    module_header = []
    if var_dict['interpreter_path']:
        module_header.append(act)
        if module_lines and module_lines[0].startswith("#!"):
            module_lines = module_lines[1:]
    else:
        if module_lines and module_lines[0].startswith("#!"):
            module_header.append(module_lines[0].strip())
            module_lines = module_lines[1:]

    if var_dict['module_encoding']:
        module_header.append(enc)
        if module_lines and module_lines[0].startswith("# -*- coding"):
            module_lines = module_lines[1:]

    if explicit_border:
        lic = """
#
# %s
#
%s
#
# %s
#
""" % (begin_marker, lic, end_marker)
    if block_wrap:
        lic = """
/*
%s
*/
""" % lic

    module_header.append(lic)
    module_text = '\n'.join(module_header) % var_dict + '\n'\
        + ''.join(module_lines)

    module_fd = open(path, 'w')
    module_fd.write(module_text)
    module_fd.close()

if __name__ == '__main__':
    target = os.getcwd()
    if len(sys.argv) > 1:
        target = os.path.abspath(sys.argv[1])
    mig_code_base = target
    if len(sys.argv) > 2:
        mig_code_base = os.path.abspath(sys.argv[2])

    for (root, dirs, files) in os.walk(target):

        # skip all dot dirs - they are from repos etc and _not_ jobs

        if root.find(os.sep + '.') != -1:
            continue
        for name in files:
            src_path = os.path.join(root, name)
            if os.path.islink(src_path):
                continue
            print('Inspecting %s' % src_path)
            for pattern in py_code_files + sh_code_files + js_code_files:
                if pattern in js_code_files:
                    needs_block = True
                else:
                    needs_block = False

                pattern = os.path.join(mig_code_base, code_root, pattern)

                # print "Testing %s against %s" % (src_path, pattern)

                if src_path == pattern or fnmatch.fnmatch(src_path, pattern):
                    print('Matched %s against %s' % (src_path, pattern))
                    proj_vars['module_name'] = name.replace('.py', '')
                    if check_header(src_path, proj_vars):
                        print('Skip %s with existing header' % src_path)
                        continue
                    add_header(src_path, proj_vars, block_wrap=needs_block)
    print()
    print("Added license headers to code in %s" % target)
    print()
    print("Don't forget to include COPYING file in root of source, e.g. run:")
    print("wget -O COPYING http://www.gnu.org/licenses/gpl2.txt")
    print("if using the default GPL v2 license here.")
