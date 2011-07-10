#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# securexmlrpcserver - a secure version of the built-in xmlrpc server
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

"""A SSL/TLS secured version of the built-in XMLRPC server. Requires
python-2.6 or later to provide the ssl module.
"""

import os
import socket
import sys
from BaseHTTPServer import HTTPServer
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler, \
     SimpleXMLRPCDispatcher
from SocketServer import BaseServer, ThreadingMixIn
# Expose extra ssl constants for optional overriding of server attributes
from ssl import wrap_socket, CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED, \
     PROTOCOL_SSLv2, PROTOCOL_SSLv3, PROTOCOL_SSLv23, PROTOCOL_TLSv1


class KeepAliveRequestHandler(SimpleXMLRPCRequestHandler):
    """Restrict to a particular path and enable keep-alive support"""
    # Restrict path to /RPC2
    rpc_paths = ('/RPC2',)
    # Force HTTP v 1.1 and thus automatic keep-alive if available
    protocol_version = 'HTTP/1.1'
    # FIXME Implement request unwrapping here?
    pass


class SecureXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer,
                         SimpleXMLRPCDispatcher): 
    """Threaded Secure XMLRPC server with automatic keep-alive support.

    SSL key and certificate paths are exposed as key_path and cert_path
    attributes that must be overriden before instantiation if they are not
    the default key.pem and cert.pem in the current directory.
    
    The ssl_version, ca_certs and cert_reqs attributes can be used to control
    additional low level settings if overriden before instantiation.
    They map directly to the corresponding ssl.wrap_socket arguments, so
    please refer to the sll module documentation for details.

    The server uses a ssl_version default of PROTOCOL_SSLv23 which allows the
    client to select whatever SSL or TLS protocol that it implements.
    """

    key_path = 'key.pem'
    cert_path = 'cert.pem'
    ssl_version = PROTOCOL_SSLv23
    ca_certs = None
    cert_reqs = CERT_NONE

    def __init__(self, addr, requestHandler=SimpleXMLRPCRequestHandler,
                 logRequests=True, allow_none=False, encoding=None,
                 bind_and_activate=True):
        """Overriding __init__ method of the SimpleXMLRPCServer"""
        print "starting SecureXMLRPCServer on %s:%s" % addr
        self.logRequests = logRequests

        # Validate attributes possibly overridden by user
        if not os.path.isfile(self.key_path):
            raise ValueError("No such server key: %s" % self.key_path)
        if not os.path.isfile(self.cert_path):
            raise ValueError("No such server certificate: %s" % \
                             self.cert_path)
        if not self.ssl_version in (PROTOCOL_SSLv2, PROTOCOL_SSLv3,
                                    PROTOCOL_SSLv23, PROTOCOL_TLSv1):
            raise ValueError("Invalid ssl_version value: %s" % \
                             self.ssl_version)
        if not self.cert_reqs in (CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED):
            raise ValueError("Invalid cert_reqs value: %s" % \
                             self.cert_reqs)

        SimpleXMLRPCDispatcher.__init__(self, allow_none, encoding)
        # Wrap the original socket in SSL/TLS
        BaseServer.__init__(self, addr, KeepAliveRequestHandler)
        self.socket = wrap_socket(socket.socket(self.address_family,
                                                self.socket_type),
                                  server_side=True,
                                  keyfile=self.key_path,
                                  certfile=self.cert_path,
                                  cert_reqs=self.cert_reqs,
                                  ssl_version=self.ssl_version,
                                  ca_certs=self.ca_certs
                                  )
        if bind_and_activate:
            self.server_bind()
            self.server_activate()
            print "server activated"


def echo(input_string):
    """Simple test function that simply echoes input_string"""
    return input_string

if __name__ == '__main__':
    if 'client' in sys.argv[1:]:
        import xmlrpclib
        proxy = xmlrpclib.ServerProxy('https://localhost:8000')
        msg = 'hello world!'
        print "sending message to echo server: %s" % msg
        reply = proxy.echo(msg)
        print "echo server replied: %s" % reply
    else:
        # Create server
        server = SecureXMLRPCServer(("localhost", 8000))
        server.register_introspection_functions()
        server.register_function(echo)
        # Run the server's main loop
        server.serve_forever()

        
