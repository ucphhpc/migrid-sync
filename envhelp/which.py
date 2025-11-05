# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# python3 - wrapper to invoke a local python3 virtual environment
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Locate a binary via the active python interpreter."""

import os
import shutil
import sys

ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
VENV_BIN_DIR = os.path.join(ROOT_DIR, 'envhelp/venv/bin')


def main(args):
    if len(args) != 1:
        return 1

    location = shutil.which(args[0])
    if location is not None:
        print(location)
        return 0

    # locally in development we do not require activating the venv and thus
    # it is possible the binary is installed but not path visible - try the
    # local venv as a fallback path to try to catch this
    location = os.path.join(VENV_BIN_DIR, args[0])
    if os.path.exists(location):
        print(location)
        return 0

    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
