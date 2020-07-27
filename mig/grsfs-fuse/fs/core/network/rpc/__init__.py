#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# __init__ - [insert a few words of module description on this line]
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
Copyright (c) 2010 Jan Wiberg. All rights reserved.
"""
from __future__ import print_function
from __future__ import absolute_import

import cPickle as pickle
import socket
import threading
# Select actual RPC implementation here and keep details hidden in the rest 
from .securexmlrpc import SecureXMLRPCServer as SecureRPCServer
from .securexmlrpc import SecureXMLRPCServerProxy as SecureRPCServerProxy
from .securexmlrpc import wrapbinary, unwrapbinary
#from securepyro import SecurePyroServer as SecureRPCServer
#from securepyro import SecurePyroServerProxy as SecureRPCServerProxy
#from securepyro import wrapbinary, unwrapbinary


class GRSServerProxy(SecureRPCServerProxy):
    """GRSfs RPC server proxy wrapping our secure transport"""
    pass


class GRSRPCServer(SecureRPCServer, threading.Thread):
    """GRSfs RPC server wrapping our secure RPC server"""
    def __init__(self, kernel, options, **kwargs):
        """Initializes the RPC server"""
        print("Init rpcServer at port %s" % options.serverport)
        kwargs["key_path"] = options.key
        kwargs["cert_path"] = options.cert
        SecureRPCServer.__init__(self, ('', options.serverport), **kwargs)
        threading.Thread.__init__(self)
        # Disable log to stdout every time somebody connects
        self.logRequests = 0
        self.allow_reuse_address = True
        self.closed = False
        # Create server

        self.register_introspection_functions()

        self.register_instance(kernel)
        self.socket.setblocking(0)
        
    def stop_serving(self):
        """Shutdown"""
        self.closed = True  
        
    def run(self):
        """Launch"""
        self.serve_forever()


t_server = None
def start(kernel, options):
    """GRSRPCServer starter"""
    global t_server
    from core.specialized.logger import Logger
    logger = Logger()
    logger.debug( "network.rpc.start() called")
    socket.setdefaulttimeout(options.network_timeout) # sets it globally. 
    # See http://stackoverflow.com/questions/372365/
    # set-timeout-for-xmlrpclib-serverproxy for alternative
    t_server = GRSRPCServer(kernel, options)
    t_server.start()
    
    logger.debug("network.rpcServer started")
    
def stop():
    """GRSRPCServer stopper"""
    #global t_server
    t_server.stop_serving()
    from core.specialized.logger import Logger
    logger = Logger()
    logger.debug( "network.rpc.stop() called")
    t_server.shutdown()
    t_server.join()    
    
def connect_to_peer(peer, ident):
    """Open connection to GRSfs peer"""
    from core.specialized.logger import Logger
    logger = Logger()
    try:
        val = None
        logger.info ("%s connecting to %s (%s)" % (__name__, peer,
                                                   peer.connection))
        (address, port) = peer.connection
        try:        
            proxy_link = GRSServerProxy((address, port),
                                        allow_none=True)
            logger.debug("%s link established. Node_register(%s)" % \
                          (__name__, ident))
            if peer.recontact:
                val = proxy_link.node_register(ident)
            logger.debug("%s connected - %s returned  '%s'" % (__name__,
                                                                peer, val))
            return (proxy_link, val)
        except Exception as serr:
            import traceback
            logger.error( "%s unable to connect to %s (%s %s)"  % (__name__,
                                                                peer, serr,
                                                                traceback.format_exc()))
            return None        
    finally:
        pass
    
def leave_network(options, state):
    """Leave GRSfs network"""
    for remote in options.connected_peers[:]:
        try:
            remote.node_unregister((socket.gethostname(), options.serverport))
        except Exception as exc:
            raise exc
        finally:
            options.connected_peers.remove(remote) 
