#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# codegrep - a simple helper to locate strings in the project code.
# Copyright (C) 2007  Jonas Bardino
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

"""Grep for a regular expression in all code"""

import os
import sys

if len(sys.argv) < 2:
    print "Usage: %s PATTERN" % (sys.argv)[0]
    print "Grep for PATTERN in all code files"
    sys.exit(1)

pattern = (sys.argv)[1]
code_files = [
    "shared/*.py",
    "shared/*/*.py",
    "server/*.py",
    "cgi-bin/*.py",
    "cgi-sid/*.py",
    "user/*.py",
    "simulation/*.py",
    "migfs-fuse/*.py",
    "resource/frontend_script.sh",
    "resource/master_node_script.sh",
    ]
code_files += ["cgi-sid/%s" % name for name in ["requestnewjob",
               "get_resource_pgid", "put_resource_pgid"]]

code_files += ["cgi-bin/%s" % name for name in ["listdir", "mkdir",
               "put", "remove", "rename", "rmdir", "stat", "walk"]]

if "__main__" == __name__:
    os.system("grep -E '%s' %s" % (pattern, (' ').join(code_files)))
