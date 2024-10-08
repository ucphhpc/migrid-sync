#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# suppconst - constant helpers for unit tests
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

import os

from tests.support._env import MIG_ENV

if MIG_ENV == 'local':
    # Use abspath for __file__ on Py2
    _SUPPORT_DIR = os.path.dirname(os.path.abspath(__file__))
elif MIG_ENV == 'docker':
    _SUPPORT_DIR = '/usr/src/app/tests/support'
else:
    raise NotImplementedError("ABORT: unsupported environment: %s" % (MIG_ENV,))

MIG_BASE = os.path.realpath(os.path.join(_SUPPORT_DIR, "../.."))
TEST_BASE = os.path.join(MIG_BASE, "tests")
TEST_DATA_DIR = os.path.join(TEST_BASE, "data")
TEST_FIXTURE_DIR = os.path.join(TEST_BASE, "fixture")
TEST_OUTPUT_DIR = os.path.join(TEST_BASE, "output")
ENVHELP_DIR = os.path.join(MIG_BASE, "envhelp")
ENVHELP_OUTPUT_DIR = os.path.join(ENVHELP_DIR, "output")


if __name__ == '__main__':
    def print_root_relative(prefix, path):
        print("%s = <root>/%s" % (prefix, os.path.relpath(path, MIG_BASE)))

    print("# base paths")
    print("root=%s" % (MIG_BASE,))
    print("# envhelp paths")
    print_root_relative("output", ENVHELP_OUTPUT_DIR)
    print("# test paths")
    print_root_relative("fixture", TEST_FIXTURE_DIR)
    print_root_relative("output", TEST_OUTPUT_DIR)
