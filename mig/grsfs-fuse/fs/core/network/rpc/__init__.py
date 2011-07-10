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

import socket, threading, select, time, xmlrpclib, re
import SocketServer
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import cPickle as pickle

# Binary wrapping
def wrapbinary(data):
    return xmlrpclib.Binary(data)
    
def unwrapbinary(binary):
    return binary.data

# Exception marshalling partially by http://code.activestate.com/recipes/365244/
__all__ = ['Server']

# List of exceptions that are allowed.  Only exceptions listed here will be reconstructed
# from an xmlrpclib.Fault instance.
allowed_errors = [ValueError, TypeError, IOError, OSError]

# changed to properly reconstruct FUSE understandable exceptions
# Example of a typical FUSE error: <type 'exception.OSError'>: [Errno 2] File not found or something else
error_pat = re.compile(r"<type 'exceptions.(?P<exception>[^:]*)'>:(\[Errno (?P<errno>\d+)\])?(?P<rest>.*$)")


class GRSUnmarshaller (xmlrpclib.Unmarshaller):
    def close(self):
        # return response tuple and target method
        if self._type is None or self._marks:
            raise xmlrpclib.ResponseError()
        if self._type == "fault":
            d = self._stack[0]
            m = error_pat.match(d['faultString'])
            if m:
                exception_name = m.group('exception')
                errno = m.group('errno')
                rest = m.group('rest')
                for exc in allowed_errors:
                    if exc.__name__ == exception_name:
                        if errno is not None:
                            raise exc(int(errno), rest)
                        else:
                            raise exc(rest)

            # Fall through and just raise the fault
            raise xmlrpclib.Fault(**d)
        return tuple(self._stack)


class ExceptionTransport (xmlrpclib.Transport):
    # Override user-agent if desired
    ##user_agent = "xmlrpc-exceptions/0.0.1"

    def getparser (self):
        # We want to use our own custom unmarshaller
        unmarshaller = GRSUnmarshaller()
        parser = xmlrpclib.ExpatParser(unmarshaller)
        return parser, unmarshaller

        
class GRSServerProxy (xmlrpclib.ServerProxy):
    def __init__ (self, *args, **kwargs):
        # Supply our own transport
        kwargs['transport'] = ExceptionTransport()
        xmlrpclib.ServerProxy.__init__(self, *args, **kwargs)



# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    #rpc_paths = ('/RPC2',)
    # Force HTTP v 1.1 and thus automatic keep-alive if available
    protocol_version = 'HTTP/1.1'
    # FIXME Implement request unwrapping here?

    
class AsyncXMLRPCServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer): 
    pass

        
class GRSRPCServer(AsyncXMLRPCServer, threading.Thread):
    def __init__(self, kernel, options):
        """Initializes the RPC server"""
        print "Init rpcServer at port %s" % options.serverport
        SimpleXMLRPCServer.__init__(self, ('', options.serverport), requestHandler = RequestHandler, allow_none = True)
        threading.Thread.__init__(self)
        self.logRequests = 0   # set to 1 to write a string to stdout every time somebody connects
        self.allow_reuse_address = True
        self.closed = False
        # Create server

        self.register_introspection_functions()

        self.register_instance(kernel)
        self.socket.setblocking(0)
        

    def stop_serving(self):
        self.closed = True  
        
    def run(self):
        self.serve_forever()


t_server = None
def start(kernel, options):
    global t_server
    from core.specialized.logger import Logger
    logger = Logger()
    logger.debug( "network.rpc.start() called")
    socket.setdefaulttimeout(options.network_timeout) # sets it globally. 
    # See http://stackoverflow.com/questions/372365/set-timeout-for-xmlrpclib-serverproxy for alternative
    t_server = GRSRPCServer(kernel, options)
    t_server.start()
    
    logger.debug("network.rpcServer started")
    
def stop():
    """docstring for stop"""
    #global t_server
    t_server.stop_serving()
    from core.specialized.logger import Logger
    logger = Logger()
    logger.debug( "network.rpc.stop() called")
    t_server.shutdown()
    t_server.join()    
    
def connect_to_peer(peer, ident):
    from core.specialized.logger import Logger
    logger = Logger()
    try:
        v = None
        logger.info ("%s connecting to %s" % (__name__, peer))
        (address, port) = peer.connection
        try:        
            proxy_link = GRSServerProxy('http://%s:%d' % (address, port), allow_none = True)        
            logger.debug ("%s link established. Node_register(%s)" % (__name__, ident))
            if peer.recontact:
                v = proxy_link.node_register(ident)
            logger.debug( "%s connected - %s returned  '%s'" % (__name__, peer, v))
            return (proxy_link, v)
        except Exception, se:
            logger.error( "%s unable to connect to %s (%s)"  % (__name__, peer, se))
            return None        
    finally:
        pass
#END_DEF connect_to_peers
    
def leave_network(options, state):
    for remote in options.connected_peers[:]:
        try:
            remote.node_unregister((socket.gethostname(), options.serverport))
        except Exception, e:
            raise e
        finally:
            options.connected_peers.remove(remote) 
#END_DEF leave_network
