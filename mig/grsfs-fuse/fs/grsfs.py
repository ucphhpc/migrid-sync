#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grsfs - [insert a few words of module description on this line]
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

#   Grid Replicated Storage
#   Copyright (C) 2010  Jan Wiberg <jaws a t diku.dk>
#
#
# TODOs:
#   See gmailfs.py for some ideas
#   Rip out connection code and put into network module
#   Rip out storage code and put into storage module
#   Figure out threads
#

"""
migfuse is a fuse frontend to the MiG Distributed Storage System
"""

import pprint
import fuse

import Queue
from fuse import Fuse
import os
from threading import Thread
import threading
import thread
import stat, errno
from os.path import abspath, expanduser, isfile

fuse.fuse_python_api = (0, 2)
fuse.feature_assert('stateful_files', 'has_init')

import thread
import quopri

import sys, traceback, re, time, tempfile, array, syslog

# Import our own stuff - put it elsewhere to reduce clutter
from core.entities import *
from core.specialized.aux import *
from core.configuration import *

from core import kernel


class grsfs(Fuse):
    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)
        
    def getattr(self, path):
        self.logger.debug("grsfs.__getattr__ %s" % threading.current_thread())        
        return GRSStat(self.kernel.getattr(path, None))

    def readlink(self, path):
        self.logger.debug("readlink %s" % path)
        return self.kernel.readlink(path, None)

    def unlink(self, path):
        self.logger.debug("unlink %s" % path)
        return self.kernel.unlink(path, None)

    def rmdir(self, path):
        self.logger.debug("rmdir %s" % path)
        return self.kernel.rmdir(path, None)

    def symlink(self, path, path1):
        self.logger.debug("symlink %s" % path)
        return self.kernel.symlink(path, path1, None)

    def rename(self, path, path1):
        self.logger.debug("rename %s" % path)
        return self.kernel.rename(path, path1, None)

    def link(self, path, path1):
        self.logger.debug("link %s" % path)
        return self.kernel.link(path, path1, None)

    def chmod(self, path, mode):
        self.logger.debug("chmod %s" % path)
        return self.kernel.chmod(path, mode, None)

    def chown(self, path, user, group):
        self.logger.debug("chown %s" % path)
        return self.kernel.chown(path, user, group, None)

    def truncate(self, path, length):
        self.logger.debug("truncate %s (len %s)" % (path, length))
        return self.kernel.truncate(path, length, None)

    def mknod(self, path, mode, dev):
        self.logger.debug("mknod %s" % path)
        return self.kernel.mknod(path, mode, dev, None)

    def utime(self, path, times):
        self.logger.debug("utime %s" % path)
        return self.kernel.utime(path, times, None)

    def access(self, path, mode):
        self.logger.debug("access %s" % path)
        return self.kernel.access(path, mode, None)
     
    def readdir(self, path, offset):
        self.logger.debug("GRSDir.readdir %s, %s" % (path, offset))
        val = self.kernel.readdir(path, offset, None)
        for v in val:
            yield fuse.Direntry(v)

    def mkdir(self, path, mode):
        self.logger.debug("GRSDir.mkdir")
        self.kernel.mkdir(path, mode, None)
        
    def init(self, arg):
        print "Init called?!"
        
    def fsinit(self):
        # print "fsinit %s" % threading.current_thread()
        # Do some dirty hacking to get things running

        self.kernel = kernel.Kernel(self.options)     # start threads in here       
        self.kernel.fsinit() 
        self.logger = self.kernel.logger

        # print "Leaving fsinit %s"  % threading.current_thread
    #END_DEF fsinit
    
    def halt(self):
        self.kernel.fshalt()

    def main(self, *a, **kw):        
        self.file_class = GRSFile
        # this crashes and is not needed: self.dir_class = GRSDirectory
        return Fuse.main(self, *a, **kw)
        
def break_into_debugger(option, opt, value, parser):
    """docstring for break_into_debugger"""
    import pdb
    pdb.set_trace()
    
    
def main():
    usage = """
    Userspace nullfs-alike: mirror the filesystem tree from some point on.

    """ + Fuse.fusage
    server = grsfs(version="%prog " + fuse.__version__,
                 usage=usage,
                 dash_s_do='setsingle')
                 
    cfg = Configuration()

    server.multithreaded = True

    server.parser.add_option(mountopt="network", default="XMLRPC", 
                             help="Which network communication library to use [default: %default]")
    server.parser.add_option(mountopt="network_timeout", default="5", 
                             help="Network communication timeout to use [default: %default]")
    server.parser.add_option(mountopt="backingstore", metavar="PATH", default=cfg.backingstore,
                             help="location of local datastore [default: %default]")
    server.parser.add_option(mountopt="backingstorestate", metavar="PATH", default=cfg.backingstorestate,
                          help="State information file [default: %default]")
    server.parser.add_option(mountopt="backingtype", default=cfg.backingtype, 
                          help="Which backing store implementation to use [default: %default]")
    server.parser.add_option(mountopt="spare", action="store", default='negotiate',
                          help="instance type [default: %default]")
    server.parser.add_option(mountopt="serverport", default=cfg.serverport, type="int",
                        help="instance type [default: %default]")
    server.parser.add_option(mountopt="contact", action="store", type="string",
                        help="list of remote hosts to group with.")
    server.parser.add_option(mountopt="mincopies", action="store", default=cfg.mincopies, type="int",
                        help="# of replicas. [Default %default]")
    server.parser.add_option(mountopt="maxcopies", action="store", default=cfg.maxcopies, type="int",
                        help="# of replicas. [Default %default]")
                        
    # advanced
    server.parser.add_option(mountopt="logverbosity", action="store", default=cfg.logverbosity,
                        help="verbosity level of the logger [default: %default]")
    server.parser.add_option(mountopt="logquiet", action="store_false", default=cfg.logquiet,
                        help="whether to be quiet [default: %default]")
    server.parser.add_option(mountopt="logdir", action="store", type="string", default=cfg.logdir,
                        help="Where to put log files. If not specified, no logging [default %default]")
    server.parser.add_option(mountopt="pdb", action="callback", callback=break_into_debugger,
                        help="whether to break into debugger upon start")
    server.parser.add_option(mountopt="key", default="key.pem", 
                             help="Which SSL key for secure network communication library to use [default: %default]")
    server.parser.add_option(mountopt="cert", default="cert.pem", 
                             help="Which SSL certificate for secure network communication library to use [default: %default]")
    server.parse(values=cfg, errex=1)
    
    if server.fuse_args.mount_expected(): 
        cfg.validate()
                    
        server.options = cfg        
    else:
        #print "Something went wrong?"
        return
        
    server.main()
    server.halt()
#END_DEF main

# for debug: global exception handler
# def my_excepthook(type, value, traceback):
#     print 'Unhandled error:', type, value

#sys.excepthook = my_excepthook

if __name__ == '__main__':
    main()

