#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# serverfile - shared wrapper for interfacing local and remote files
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

# Script version (automagically updated by cvs)

"""This file contains a file wrapper interface for server IO. It should
be used as a template for other IO modules that hide the underlying
physical location of server files.
"""

from builtins import object
__version__ = '$Revision: 1564 $'
__revision__ = __version__

# $Id: serverfile.py 1564 2006-10-24 14:43:46Z jones $

import fcntl

# File locking states

LOCK_UN = fcntl.LOCK_UN
LOCK_SH = fcntl.LOCK_SH
LOCK_EX = fcntl.LOCK_EX

# File operations


class ServerFile(object):

    """File object wrapper to provide the usual file interface with
    local or distributed files underneath. We simply inherit file
    operations from builtin file class here. This class should be
    subclassed in order to provide remote server file operation.
    """

    mode = None
    closed = None

    def __init__(self, path, mode='r', bufsize=-1):
        """Any general setup"""
        self.mode = mode
        self.closed = False

    def close(self):
        """Close any open local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def fileno(self):
        """Get low level file descriptor for any open local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def flush(self):
        """Flush any open local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def read(self, size=-1):
        """Read size bytes from local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def readlines(self, size=-1):
        """Read size bytes from local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def seek(self, offset, whence=0):
        """Seek to offset in local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def tell(self):
        """Tell offset in local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def truncate(self, size=0):
        """Truncate local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def write(self, data):
        """Write data to local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def writelines(self, lines):
        """Write lines to local or remote file handle"""
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def lock(self, mode):
        """Additional method interface to integrate file locking with
        file objects.
        """
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def unlock(self):
        """Additional method interface to integrate file locking with
        file objects.
        """
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")

    def __str__(self):
        raise NotImplementedError(
            "This is an interface class: subclass and implement!")


class LockingException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
