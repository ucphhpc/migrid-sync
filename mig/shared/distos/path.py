#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# path - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Provide the file system specific functions of os.path for distos"""
from __future__ import absolute_import

import stat
from . import base

# publish all relevant path functions and override the ones that are
# file location specific

from os.path import basename, commonprefix, dirname, isabs, join, normcase, \
     normpath, sep, split


def isfile(path):
    """Similar to the local version"""

    try:
        stat_tuple = base.stat(path)
        mode = stat_tuple[stat.ST_MODE]
    except OSError as ose:
        return False
    return stat.S_ISREG(mode)


def isdir(path):
    """Similar to the local version"""

    try:
        stat_tuple = base.stat(path)
        mode = stat_tuple[stat.ST_MODE]
    except OSError as ose:
        return False
    return stat.S_ISDIR(mode)


def islink(path):
    """Similar to the local version"""

    try:
        stat_tuple = base.lstat(path)
        mode = stat_tuple[stat.ST_MODE]
    except OSError as ose:
        return False
    return stat.S_ISLNK(mode)


def exists(path):
    """Similar to the local version"""

    try:
        stat_tuple = base.stat(path)
    except OSError as ose:
        return False
    return True


def getsize(path):
    """Similar to the local version"""

    stat_tuple = base.stat(path)
    return stat_tuple[stat.ST_SIZE]


def getatime(path):
    """Similar to the local version"""

    stat_tuple = base.stat(path)
    return stat_tuple[stat.ST_ATIME]


def getctime(path):
    """Similar to the local version"""

    stat_tuple = base.stat(path)
    return stat_tuple[stat.ST_CTIME]


def getmtime(path):
    """Similar to the local version"""

    stat_tuple = base.stat(path)
    return stat_tuple[stat.ST_MTIME]


def abspath(path):
    """Similar to the local version"""

    # CWD does not make sense for dist files so just use sep

    return normpath(join(sep, path))


def realpath(path):
    """Similar to the local version"""

    # CWD does not make sense for dist files so just use sep

    if path.startswith(sep):
        abs_path = path
    else:
        abs_path = sep + path

    # TODO: implement readlink() functionality and use bottom
    # up on abs_path dirs to extract real path

    real_path = abs_path
    return abs_path


def samefile(path1, path2):
    """Similar to the local version"""

    try:
        stat_tuple1 = base.stat(path1)
        inode1 = stat_tuple1[stat.ST_INO]
        stat_tuple2 = base.stat(path2)
        inode2 = stat_tuple2[stat.ST_INO]
    except OSError as ose:
        return False
    return inode1 == inode2


