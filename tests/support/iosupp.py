#
# --- BEGIN_HEADER ---
#
# iosupp - test support functions related to io
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

from __future__ import annotations

import os
import typing


if typing.TYPE_CHECKING:
    TreeDict = dict[str, "TreeDict"] | dict[str, str]


def write_file(dir: str, name: str, content: str) -> None:
    """Write text content into a specified file."""
    with open(os.path.join(dir, name), "w") as f:
        f.write(content)


def read_file(dir: str, name: str) -> str:
    """Read text content from a specified file."""
    with open(os.path.join(dir, name), "r") as f:
        return f.read()


def read_tree(root: str) -> TreeDict:
    """
    Read the filetree rooted at the given directory as a nested dictionary
    tree, where leafs represent file contents.
    """
    tree = {}
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if os.path.isdir(path):
            tree[name] = read_tree(path)
        else:
            tree[name] = read_file(root, path)
    return tree


def write_tree(root: str, tree: TreeDict) -> None:
    """
    Write the given given tree to the given root directory.
    """
    for name, branch in tree.items():
        if isinstance(branch, str):  # leaf
            write_file(root, name, branch)
        else:
            branchname = os.path.join(root, name)
            os.mkdir(branchname)
            write_tree(branchname, branch)
