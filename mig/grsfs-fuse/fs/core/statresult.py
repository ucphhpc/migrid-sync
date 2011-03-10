#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# statresult - [insert a few words of module description on this line]
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

import fuse

class GRSStat(fuse.Stat):
    """FIXME: put here because if its in entities then we get a circular import!"""
    def __init__(self, posix):
        super(GRSStat, self).__init__()
        # HACK/TODO: try to clean up these data structures so we can serialize them in FUSE understandable format
        self.st_mode = posix['mode']
        self.st_ino = posix['ino']
        self.st_dev = posix['dev']
        self.st_nlink = posix['nlink']
        self.st_uid = posix['uid']
        self.st_gid = posix['gid']
        self.st_size = posix['size']
        self.st_atime = posix['atime']
        self.st_mtime = posix['mtime']
        self.st_ctime = posix['ctime']
