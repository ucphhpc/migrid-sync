#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# GRSStorage - storage super class
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

"""
    GRSStorage - storage super class
"""
from core.specialized import ReadWriteLock


class GRSStorage(object):
    def __init__(self):
        """docstring for __init__"""
        self.lock = ReadWriteLock.ReadWriteLock()
    def getlock(self, path):
        """
        Return a suitable lock class for this backend.
        This is a multiple-readers, single-writer lock that prioritizes the writer, 
        and has no provisions for more than one lock (path argument is ignored)."""
        #print "%s returning lock object %s" % (self.__class__.__name__, self.lock)
        return self.lock
