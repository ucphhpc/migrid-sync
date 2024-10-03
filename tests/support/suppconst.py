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


# Use abspath for __file__ on Py2
_SUPPORT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_BASE = os.path.normpath(os.path.join(_SUPPORT_DIR, ".."))
TEST_DATA_DIR = os.path.join(TEST_BASE, "data")
TEST_FIXTURE_DIR = os.path.join(TEST_BASE, "fixture")
TEST_OUTPUT_DIR = os.path.join(TEST_BASE, "output")
MIG_BASE = os.path.realpath(os.path.join(TEST_BASE, ".."))
