#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# localfile - implementation of serverfile with local IO
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

"""This module contains various wrapper functions for server IO. In that way
the underlying distribution of server files can be separated from the normal
server operation.
"""

from __future__ import absolute_import

import fcntl
from errno import EACCES, EAGAIN

from .serverfile import ServerFile, LOCK_UN, LOCK_SH, LOCK_EX, \
    LockingException

# File operations


class LocalFile(ServerFile):

    """File object wrapper to provide the usual file interface with
    local files underneath. We simply indirectly inherit all file
    operations from builtin file class here and override as needed.
    """

    def __init__(self, path, mode='r', bufsize=-1):
        """Create local file and set default object attributes"""
        ServerFile.__init__(self, path, mode, bufsize)
        self._file = open(path, mode, bufsize)
        self.mode = self._file.mode
        self.closed = self._file.closed
        self.__locking = LOCK_UN

    def close(self):
        """Close any open local or remote file handle"""
        self._file.close()

    def fileno(self):
        """Get low level file descriptor for any open local or remote file handle"""
        return self._file.fileno()

    def flush(self):
        """Flush any open local or remote file handle"""
        self._file.flush()

    def read(self, size=-1):
        """Read size bytes from local or remote file handle"""
        return self._file.read(size)

    def readlines(self, size=-1):
        """Read size bytes from local or remote file handle"""
        return self._file.readlines(size)

    def seek(self, offset, whence=0):
        """Seek to offset in local or remote file handle"""
        self._file.seek(offset, whence)

    def tell(self):
        """Tell offset in local or remote file handle"""
        return self._file.tell()

    def truncate(self, size=0):
        """Truncate local or remote file handle"""
        self._file.truncate(size)

    def write(self, data):
        """Write data to local or remote file handle"""
        self._file.write(data)

    def writelines(self, lines):
        """Write lines to local or remote file handle"""
        self._file.writelines(lines)

    def lock(self, mode):
        """Additional method to integrate file locking with file
        object. Allowed modes are the constants listed at the
        beginning of this file.
        """

        if mode not in [LOCK_UN, LOCK_SH, LOCK_EX]:
            raise LockingException('Locking error: unknown mode: %s')
        if self.__locking != LOCK_UN and mode != LOCK_UN:
            raise LockingException('Locking rejected: already locked')
        try:
            fcntl.flock(self.fileno(), mode | fcntl.LOCK_NB)
        except IOError as ioe:
            if ioe.errno in [EACCES, EAGAIN]:
                raise LockingException('Locking failed: locking timed out!'
                                       )
        except Exception as exc:
            raise(exc)
        self.__locking = mode

    def unlock(self):
        """Simply pass to lock(), which also handles unlocking."""

        self.lock(LOCK_UN)

    def get_lock_mode(self):
        return self.__locking

    def __str__(self):
        return '%s %s' % (self.__locking, ServerFile.__str__(self))
