#
# --- BEGIN_HEADER ---
#
# directory - Functionality related to file system directories.
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
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# --- END_HEADER ---
#

"""Functionality related to file system directories."""

import os


def mkdir(path: str, *, mode: int = 0o700) -> None:
    """Create the given directory.

    Args:
        path: the path to create the directory at.
        mode: the mode to create the directory with.
    Raises:
        OSError: different subclasses corresponding to the error.
    """
    os.mkdir(path, mode)


def makedirs(path: str, *, mode: int = 0o700, exist_ok: bool = False) -> None:
    """Create the given directories recursively.

    Args:
        path: the path to create the directories at.
        mode: the mode to create the directories with.
        exist_ok: if True do not raise an error when the leaf directory already
            exists, if False do raise an error.
    Raises:
        OSError: different subclasses corresponding to the error.
    """
    # create intermediate directories
    split_path = os.path.normpath(path).split(os.path.sep)[:-1]
    for i in range(len(split_path) - 1):
        # Edit to check if E203 is ignored
        intermediate_path = os.path.sep.join(split_path[0 : i + 2])
        try:
            mkdir(intermediate_path, mode=mode)
        except FileExistsError:
            if not os.path.isdir(intermediate_path):
                raise

    # create leaf directory
    try:
        mkdir(path, mode=mode)
    except FileExistsError:
        if not exist_ok:
            raise
        if not os.path.isdir(path):
            raise
