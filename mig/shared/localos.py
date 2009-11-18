#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# localos - [insert a few words of module description on this line]
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

"""This module contains various wrapper functions for local server
file system operations (think python 'os' module). In that way the
underlying server FS operation can be separated from the normal
server operation.
This module doesn not support *all* operations, only those that are
provided as remote functions! mkfifo(), etc. should still use plain
'os' module as they're not supported for (remote) MiG fs.
"""

import os

# publish path functions as localos.path.X

import os.path as path

# TODO: can functions be replaced by simple chmod = os.chmod, etc ?

# #############################
# Public 'os'-like functions #
# #############################


def chmod(path, mode):
    return os.chmod(path, mode)


def listdir(path):
    return os.listdir(path)


def lstat(path):
    return os.lstat(path)


def mkdir(path, mode=0777):
    return os.mkdir(path, mode)


def makedirs(path_list):
    return os.makedirs(path_list)


def remove(path):
    return os.remove(path)


def rename(src, dst):
    return os.rename(src, dst)


def rmdir(path):
    return os.rmdir(path)


def removedirs(path_list):
    return os.removedirs(path_list)


def stat(path):
    return os.stat(path)


def symlink(src, dst):
    return os.symlink(src, dst)


def walk(top, topdown=True):
    return os.walk(top, topdown)


