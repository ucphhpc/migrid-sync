#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# serverfile - [insert a few words of module description on this line]
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

# Script version (automagically updated by cvs)

"""This file contains a file wrapper interface for server IO. It should
be used as a template for other IO modules that hide the underlying
physical location of server files.
"""

__version__ = '$Revision: 1564 $'
__revision__ = __version__

# $Id: serverfile.py 1564 2006-10-24 14:43:46Z jones $

import fcntl

# File locking states

LOCK_UN = fcntl.LOCK_UN
LOCK_SH = fcntl.LOCK_SH
LOCK_EX = fcntl.LOCK_EX

# File operations


class ServerFile(file):

    """File object wrapper to provide the usual file interface with
    local or distributed files underneath. We simply inherit file
    operations from builtin file class here. This class should be
    subclassed in order to provide remote server file operation.
    """

    def __init__(
        self,
        path,
        mode='r',
        bufsize=-1,
        ):
        """Create local file and set default object attributes"""

        file.__init__(self, path, mode, bufsize)

    def lock(self, mode):
        """Additional method interface to integrate file locking with
        file objects. 
        """

        raise LockingException('This is an interface class! use a subclass and implement locking there!'
                               )

    def unlock(self):
        """Additional method interface to integrate file locking with
        file objects. 
        """

        raise LockingException('This is an interface class! use a subclass and implement locking there!'
                               )

    def __str__(self):
        return file.__str__(self)


class LockingException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


