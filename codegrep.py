#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# codegrep - a simple helper to locate strings in the project code.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
# --- END_HEADER ---
#

"""Grep for a regular expression in all code files"""

from __future__ import print_function
from __future__ import absolute_import

import glob
import sys

from mig.shared.projcode import code_files
from mig.shared.safeeval import subprocess_call


if '__main__' == __name__:
    if len(sys.argv) < 2:
        print('Usage: %s PATTERN' % sys.argv[0])
        print('Grep for PATTERN in all code files')
        sys.exit(1)

    pattern = sys.argv[1]
    expanded_paths = []
    for code_path in code_files:
        expanded_paths += glob.glob(code_path)
    command_list = ["grep", "-E", "%s" % pattern] + expanded_paths
    # NOTE: we use command list to avoid shell requirement
    subprocess_call(command_list)
