#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# passthrough - mirrors an existing underlying filesystem
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
Mirrors an existing underlying filesystem

Parts of this file by the original creator of fuse-python
"""

import os, errno, tarfile
from core.specialized.aux import *

from core.storage.GRSStorage import GRSStorage
from core.statresult import GRSStat

def stat_to_dict(structure):
    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = structure
    d = {}
    d['mode'] = mode
    d['ino'] = ino
    d['dev'] = dev
    d['nlink'] = nlink
    d['uid'] = uid
    d['gid'] = gid
    d['size'] = size
    d['atime'] = atime
    d['mtime'] = mtime
    d['ctime'] = ctime
    return d
            
class Passthrough(GRSStorage):
    # Internal 
    def __init__(self, options):
        super(Passthrough, self).__init__()
        self.os_path = options.backingstore
        self.options = options        
        assert self.os_path is not None
        
    def _recomb(self, path):
        path = os.path.abspath(self.os_path + path)
        #print "Passthrough recombulated path to %s" % path
        return path

    def start(self):
        pass
        
    def stop(self):
        pass
        
    def branch(self, subtree_root, destination, message):
        try:
            # try dry-run first while we are in testing phase
            ret = os.system("rsync -avxn %s %s" % (self._recomb(subtree_root), destination)) 
            if ret != 0:
                return -1
            ret = os.system("rsync -avx %s %s" % (self._recomb(subtree_root), destination)) 
            message_file_path = os.path.join(self._recomb(subtree_root), ".migrated")
            f = open(message_file_path, "w")
            f.write(message+'\n')
            f.close()
            return 0
        except Exception, v:
            raise
            

    def _get_dataset_from_root(self, root):
        tar_archive = tarfile.open(self.options.compressedfilelocation,'w:bz2')
        for root, dirs, files in os.walk(self.options.backingstore):
            for f in files:
                tar_archive.add(f)
            for d in dirs:
                tar_archive.add(d)
                
        tar_archive.close()
        f = open(self.options.compressedfilelocation, "r")
        data = f.read(-1) # careful
        f.close()
        return data
        
        
    # Upgrade operations
    def get_full_dataset(self):
        return self._get_dataset_from_root(self.options.compressedfilelocation)
        
    def set_full_dataset(self, data):
        """
            DELETES ALL FILES IN THE BACKING STORE!!!
        """
        def nuke_contents(path):
            import shutil

            for root, dirs, files in os.walk(path):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))
        
        nuke_contents(self.options.backingstore)
        f = open(self.options.compressedfilelocation, "w")
        f.write(data)
        f.close()
        tar_archive = tarfile.open(self.options.compressedfilelocation,'r:*')
        tar_archive.extractall(self.options.backingstore)
        tar_archive.close()
        
    def remove_temp_file(self):
        """nuke the temp file"""
        try:
            os.unlink(self.options.compressedfilelocation)
        except:
            pass
    # end upgrade operations
    
    # FILESYSTEM METHODS BELOW    
    def getattr(self, internal_data, path):
        return stat_to_dict(os.lstat(self._recomb(path)))

    def readdir(self, internal_data, path, offsetet, prefetch = False):
        return os.listdir(self._recomb(path))
        
    def open(self, internal_data, path, flags, *mode):
        if len(mode) > 0:
            mode = mode[0] # HACK Something weird is happening with python dynamic method invocation here as the list of [] becomes ([],)
        
        f_id = os.open(self._recomb(path), flags, *mode)
        return os.fdopen(f_id, flag2mode(flags))
        #return f_id
                                                            
    def read(self, internal_data, length, offset):
        internal_data.seek(offset)
        return internal_data.read(length) 
        
    def fgetattr(self, internal_data):
        return stat_to_dict(os.fstat(internal_data.fileno()))
        
    # FILE WRITE OPS
    def write(self, internal_data, buf, offset):
        internal_data.seek(offset)
        internal_data.write(buf)
        return len(buf)
        
    def flush(self, internal_data):
        if 'w' in internal_data.mode or 'a' in internal_data.mode:
            internal_data.flush()
        
    def release(self, internal_data, flags):
        internal_data.close()
        # FIXME: release the file in the OFT
    
    def truncate(self, internal_data, path, length):
        f = open(self._recomb(path), "a")
        f.truncate(length)
        f.close()

    def ftruncate(self, internal_data, length):
        return internal_data.truncate(length)
        
    def unlink(self, internal_data, path):
        return os.unlink(self._recomb(path))
        
    def utime(self, internal_data, path, times):
        return os.utime(self._recomb(path), tuple(times))

    def utimens(self, internal_data, path, ts_acc, ts_mod):
        return os.utime(self._recomb(path), (ts_acc.tv_sec, ts_mod.tv_sec))        

    def readlink(self, internal_data, path):
        return os.readlink(self._recomb(path))
                              
    ### META 
    def access(self, internal_data, path, mode):
        if not os.access(self._recomb(path), mode):
            return -errno.EACCES
    
    def link(self, internal_data, path, path1):
        return os.link(self._recomb(path), self._recomb(path1))

    def chmod(self, internal_data, path, mode):
        return os.chmod(self._recomb(path), mode)

    def chown(self, internal_data, path, user, group):
        return os.chown(self._recomb(path), user, group)

    def rmdir(self, internal_data, path):
        os.rmdir(self._recomb(path))

    def symlink(self, internal_data, path, path1):
        os.symlink(path, self._recomb(path1))

    def rename(self, internal_data, path, path1):
        os.rename(self._recomb(path), self._recomb(path1))
            
    def mknod(self, internal_data, path, mode, dev):
        return os.mknod(self._recomb(path), mode, dev)

    def mkdir(self, internal_data, path, mode):
        return os.mkdir(self._recomb(path), mode)
        
    ### BUFFER MANAGEMENT
    def fsync(self, internal_data, flush_all = False):
        if flush_all:
            raise NotImplemented("FIXME descriptor knowledge removed from passthrough, so reengineer at higher level")
        # if flush_all:
        #     for d in self.descriptors:
        #         if hasattr(d, "flush"):
        #             d.flush()
        #             os.fsync(d.fileno)
        #         else:
        #             print "Potential problem in fsync"
                    
        if internal_data is not None:            
            os.fsync(internal_data)
        
    
