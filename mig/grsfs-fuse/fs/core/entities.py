#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# entities - [insert a few words of module description on this line]
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
Created by Jan Wiberg on 2010-03-21.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""

import sys, os, syslog, stat, errno
import fuse
from core.kernel import Kernel
from core.state import MASTER
from core.statresult import GRSStat

hello_path = '/hello'
hello_str = 'Hello World!\n'


class Writeable(object):
    """Dirty-able FUSE object"""
    # Objects deriving from Writeable are only used for FUSE.
    def __init__(self):
        self.direct_io = False
        self.kernel = Kernel()
        self.keep_cache = False
        self.direct_io = self.kernel.state.instancetype <= MASTER
        self.keep_cache = self.kernel.state.instancetype <= MASTER
    
class GRSFile(Writeable):
    def __init__(self, path, flags, *mode):
        super(GRSFile, self).__init__()
        self.kernel.logger.debug("%s init with args %s, %s, %s" % (self.__class__.__name__, path, flags, mode))
        self.file = self.kernel.open(path, flags, list(mode))
        self.open_args = (path, flags, tuple(mode)) # FIXME: atm open_args and file is the same data?
        
    def _initialize_internal(self):
        """docstring for _initialize_internal"""        
        return {'file_id': self.open_args}
        
    def read(self, size, offset ):
        return self.kernel.read(size, offset, internal = self._initialize_internal())

    def write(self, buf, offset):
        return self.kernel.write(buf, offset, internal = self._initialize_internal())

    def release(self, flags):
        self.kernel.release(flags, internal = self._initialize_internal())

    def flush(self):
        self.kernel.flush(internal = self._initialize_internal())

    def fsync(self, isfsyncfile):
        self.flush()
        self.kernel.fsync(isfsyncfile, internal = self._initialize_internal())

    def fgetattr(self):
        return GRSStat(self.kernel.fgetattr(internal = self._initialize_internal()))

    def ftruncate(self, length):
        self.kernel.ftruncate(length, internal = self._initialize_internal())

    def lock(self, cmd, owner, **kw):
        self.kernel.lock(cmd, owner, kw, internal = self._initialize_internal())
        
        # The code here is much rather just a demonstration of the locking
        # API than something which actually was seen to be useful.

        # Advisory file locking is pretty messy in Unix, and the Python
        # interface to this doesn't make it better.
        # We can't do fcntl(2)/F_GETLK from Python in a platfrom independent
        # way. The following implementation *might* work under Linux. 
        #
        # if cmd == fcntl.F_GETLK:
        #     import struct
        # 
        #     lockdata = struct.pack('hhQQi', kw['l_type'], os.SEEK_SET,
        #                            kw['l_start'], kw['l_len'], kw['l_pid'])
        #     ld2 = fcntl.fcntl(self.fd, fcntl.F_GETLK, lockdata)
        #     flockfields = ('l_type', 'l_whence', 'l_start', 'l_len', 'l_pid')
        #     uld2 = struct.unpack('hhQQi', ld2)
        #     res = {}
        #     for i in xrange(len(uld2)):
        #          res[flockfields[i]] = uld2[i]
        #  
        #     return fuse.Flock(**res)

        # Convert fcntl-ish lock parameters to Python's weird
        # lockf(3)/flock(2) medley locking API...
        # op = { fcntl.F_UNLCK : fcntl.LOCK_UN,
        #        fcntl.F_RDLCK : fcntl.LOCK_SH,
        #        fcntl.F_WRLCK : fcntl.LOCK_EX }[kw['l_type']]
        # if cmd == fcntl.F_GETLK:
        #     return -EOPNOTSUPP
        # elif cmd == fcntl.F_SETLK:
        #     if op != fcntl.LOCK_UN:
        #         op |= fcntl.LOCK_NB
        # elif cmd == fcntl.F_SETLKW:
        #     pass
        # else:
        #     return -EINVAL
        # 
        # fcntl.lockf(self.fd, op, kw['l_start'], kw['l_len'])
    
    
class _GRSDirectory(Writeable): # presently not used
    pass
    # def __init__(self, **kwargs):
    #     log("GRSDir.__init__ %s" % kwargs)
    
    # def __init__(self, path):
    #     """docstring for __init__"""
    #     log("GRSDirectory.__init__ %s" % path)
    #     self.path = path
    #     self.kernel = Kernel()
        
    # def readdir(self, offset):
    #     log("GRSDir.readdir %s, %s" % (self.path, offset))
    #     return self.kernel.readdir(self.path, offset, internal = {})
    # 
    # def mkdir(self, path, mode):
    #     log("GRSDir.mkdir")
    #     return self.kernel.readdir(self.path, offset, internal = {})
    
