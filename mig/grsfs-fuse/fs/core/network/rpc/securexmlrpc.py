#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# securexmlrpc - a secure version of the built-in xmlrpc server and proxy
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""A SSL/TLS secured version of the built-in XMLRPC server and proxy. Requires
python-2.7 or later to provide the ssl module.
"""

import os
import re
import sys
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
from SocketServer import ThreadingMixIn
# Expose extra ssl constants for optional overriding of server attributes
from ssl import wrap_socket, CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED, \
     PROTOCOL_SSLv23, PROTOCOL_TLSv1_2


# Exception marshalling partially by http://code.activestate.com/recipes/365244/
__all__ = ['Server']

# List of exceptions that are allowed.
# Only exceptions listed here will be reconstructed from an xmlrpclib.Fault
# instance.
allowed_errors = [ValueError, TypeError, IOError, OSError]

# changed to properly reconstruct FUSE understandable exceptions
# Example of a typical FUSE error:
# <type 'exception.OSError'>: [Errno 2] File not found or something else
error_pat = re.compile(r"<type 'exceptions.(?P<exception>[^:]*)'>:" + \
                       "(\[Errno (?P<errno>\d+)\])?(?P<rest>.*$)")

# Binary wrapping
def wrapbinary(data):
    """Pack binary data"""
    return xmlrpclib.Binary(data)
    
def unwrapbinary(binary):
    """Unpack binary data"""
    return binary.data


class XMLRPCUnmarshaller (xmlrpclib.Unmarshaller):
    """Custom unmarshaller to handle exceptions"""
    def close(self):
        """return response tuple and target method"""
        if self._type is None or self._marks:
            raise xmlrpclib.ResponseError()
        if self._type == "fault":
            res_dict = self._stack[0]
            hit = error_pat.match(res_dict['faultString'])
            if hit:
                exception_name = hit.group('exception')
                errno = hit.group('errno')
                rest = hit.group('rest')
                for exc in allowed_errors:
                    if exc.__name__ == exception_name:
                        if errno is not None:
                            raise exc(int(errno), rest)
                        else:
                            raise exc(rest)

            # Fall through and just raise the fault
            raise xmlrpclib.Fault(**res_dict)
        return tuple(self._stack)


class SecureXMLRPCExceptionTransport (xmlrpclib.SafeTransport):
    """Exception handling transport using the HTTPS specific SafeTransport"""
    # Override user-agent if desired
    ##user_agent = "xmlrpc-exceptions/0.0.1"

    def getparser (self):
        """We want to use our own custom unmarshaller"""
        unmarshaller = XMLRPCUnmarshaller()
        parser = xmlrpclib.ExpatParser(unmarshaller)
        return parser, unmarshaller


class SecureXMLRPCServerProxy(xmlrpclib.ServerProxy): 
    """Secure XMLRPC server proxy suitable for our use cases"""
    def __init__(self, address_tuple, **kwargs):
        """Supply our own transport, enable None values and translate
        address_tuple to suitable uri.
        """
        kwargs['transport'] = SecureXMLRPCExceptionTransport()
        kwargs['allow_none'] = True
        kwargs['uri'] = 'https://%s:%d' % address_tuple
        xmlrpclib.ServerProxy.__init__(self, **kwargs)


class KeepAliveRequestHandler(SimpleXMLRPCRequestHandler):
    """Restrict to a particular path and enable keep-alive support"""
    # Restrict path to /RPC2
    rpc_paths = ('/RPC2',)
    # Force HTTP v 1.1 and thus automatic keep-alive if available
    protocol_version = 'HTTP/1.1'
    # FIXME Implement request unwrapping here?


class BlockingSecureXMLRPCServer(SimpleXMLRPCServer):
    """Blocking Secure XMLRPC server with automatic keep-alive support.

    Optional SSL key and certificate paths are exposed as key_path and
    cert_path arguments that may be overriden in instantiation if they are not
    the default key.pem and cert.pem in the current directory.

    You can create suitable key and cert files with:
    openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem
    
    The optional ssl_version, ca_certs and cert_reqs arguments can be used to
    control additional low level settings during instantiation.
    They map directly to the corresponding ssl.wrap_socket arguments, so
    please refer to the ssl module documentation for details.

    The server uses a ssl_version default of PROTOCOL_SSLv23 which allows the
    client to select whatever SSL or TLS protocol that it implements.
    """
    def __init__(self, addr, requestHandler=KeepAliveRequestHandler,
                 logRequests=True, allow_none=True, encoding=None,
                 bind_and_activate=True, key_path='key.pem',
                 cert_path='cert.pem', ca_certs=None, cert_reqs=CERT_NONE,
                 ssl_version=PROTOCOL_SSLv23):
        """Overriding __init__ method of the SimpleXMLRPCServer to add SSL in
        between basic init and network activation.
        """
        # Initializing SecureXMLRPCServer *without* network
        SimpleXMLRPCServer.__init__(self, addr, requestHandler=requestHandler,
                                    logRequests=logRequests,
                                    allow_none=allow_none, encoding=encoding,
                                    bind_and_activate=False)
        # Validate arguments possibly supplied by user
        if not os.path.isfile(key_path):
            raise ValueError("No such server key: %s" % key_path)
        if not os.path.isfile(cert_path):
            raise ValueError("No such server certificate: %s" % cert_path)
        if not ssl_version in (PROTOCOL_SSLv23, PROTOCOL_TLSv1_2):
            raise ValueError("Invalid ssl_version value: %s" % ssl_version)
        if not cert_reqs in (CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED):
            raise ValueError("Invalid cert_reqs value: %s" % cert_reqs)
        self.socket = wrap_socket(self.socket, server_side=True,
                                  keyfile=key_path, certfile=cert_path,
                                  cert_reqs=cert_reqs, ssl_version=ssl_version,
                                  ca_certs=ca_certs)
        if bind_and_activate:
            self.server_bind()
            self.server_activate()
            

class SecureXMLRPCServer(ThreadingMixIn, BlockingSecureXMLRPCServer): 
    """Threaded secure XMLRPC server"""
    pass


class BlockingInsecureXMLRPCServer(SimpleXMLRPCServer): 
    """Blocking insecure XMLRPC server"""
    def __init__(self, addr, requestHandler=KeepAliveRequestHandler,
                 logRequests=True, allow_none=False, encoding=None,
                 bind_and_activate=True):
        SimpleXMLRPCServer.__init__(self, addr,
                                    requestHandler=requestHandler,
                                    logRequests=logRequests,
                                    allow_none=allow_none,
                                    encoding=encoding,
                                    bind_and_activate=bind_and_activate)


class InsecureXMLRPCServer(ThreadingMixIn, BlockingInsecureXMLRPCServer):
    """Threaded insecure XMLRPC server"""
    pass


if __name__ == '__main__':
    address_tuple = ("localhost", 8000)
    if sys.argv[1:]:
        address_tuple = (sys.argv[1], address_tuple[1])
    if sys.argv[2:]:
        address_tuple = (address_tuple[0], int(sys.argv[2]))
    if 'client' in sys.argv[3:]:
        proxy = SecureXMLRPCServerProxy(address_tuple)
        print "requesting list of methods from server on %s:%d" % address_tuple
        reply = proxy.system.listMethods()
        print "server replied: %s" % reply
    else:
        # Create server
        server = SecureXMLRPCServer(address_tuple)
        server.register_introspection_functions()
        # Run the server's main loop
        print "Starting SecureXMLRPCServer on %s:%s" % address_tuple
        server.serve_forever()

        
