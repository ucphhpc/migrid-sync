#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addheader - add license header to all code modules.
# Copyright (C) 2009  Jonas Bardino
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
# --- END_HEADER ---
#

"""Search code tree and add the required header to all python modules"""

import os
import sys
import fnmatch

from codegrep import code_files


action_text = "#!%(interpreter_path)s"
encoding_text = "# -*- coding: %(module_encoding)s -*-"
license_text = """#
# --- BEGIN_HEADER ---
#
# %(module_name)s - [insert a few words of module description on this line]
# Copyright (C) %(copyright_year)s  %(authors)s
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
"""

def add_header(path, var_dict):
    """Add the required copyright and license header to module in path"""
    module_fd = open(path, "r")
    module_lines = module_fd.readlines()
    module_fd.close()
    backup_fd = open(path + ".unlicensed", "w")
    backup_fd.writelines(module_lines)
    backup_fd.close()
    act = action_text % var_dict
    enc = encoding_text % var_dict
    lic = license_text % var_dict
    if module_lines[0].startswith(act):
        module_lines = module_lines[1:]
    if module_lines[0].startswith(enc):
        module_lines = module_lines[1:]
        
    module_header = [act, enc, lic]
    module_text = ('\n'.join(module_header) % var_dict + '\n' + ''.join(module_lines))

    module_fd = open(path, "w")
    module_fd.write(module_text)
    module_fd.close()


target = os.getcwd()
if len(sys.argv) > 1:
    target = os.path.abspath((sys.argv)[1])

var_dict = {}
var_dict["interpreter_path"] = "/usr/bin/python"
var_dict["module_encoding"] = "utf-8"
for (root, dirs, files) in os.walk(target):
    for name in files:
        if root.find(".svn") != -1:
            continue
        path = os.path.join(root, name)
        if os.path.islink(path):
            continue
        print "Inspecting %s" % path
        for pattern in code_files:
            pattern = os.path.join(target, pattern)

            # print "Testing %s against %s" % (path, pattern)
            if path == pattern or fnmatch.fnmatch(path, pattern):
                print "Matched %s against %s" % (path, pattern)
                var_dict["module_name"] = name.replace('.py', '')
                var_dict["authors"] = "The MiG Project lead by Brian Vinter"
                var_dict["copyright_year"] = "2003-2009"
                add_header(path, var_dict)
                
