#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# localfile - [insert a few words of module description on this line]
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

"""This module contains various wrapper functions for server IO. In that way the underlying distribution of server files can be separated from the normal server operation."""

import fcntl

from serverfile import ServerFile, LOCK_UN, LOCK_SH, LOCK_EX, \
    LockingException

# File operations


class LocalFile(ServerFile):

    """File object wrapper to provide the usual file interface with
    local files underneath. We simply indirectly inherit all file
    operations from builtin file class here and override as needed.
    """

    def __init__(
        self,
        path,
        mode='r',
        bufsize=-1,
        ):

        ServerFile.__init__(self, path, mode, bufsize)
        self.__locking = LOCK_UN

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
        except IOError, ioe:
            if ioe.errno in [EACCESS, EAGAIN]:
                raise LockingException('Locking failed: locking timed out!'
                        )
        except Exception, e:
            raise
        self.__locking = mode

    def unlock(self):
        """Simply pass to lock(), which also handles unlocking."""

        self.lock(LOCK_UN)

    def get_lock_mode(self):
        return self.__locking

    def __str__(self):
        return '%s %s' % (self.__locking, file.__str__(self))


