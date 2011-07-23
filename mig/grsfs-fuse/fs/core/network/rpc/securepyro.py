#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# securepyro - a secure version of the built-in pyro server and proxy
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

"""A SSL/TLS secured version of the built-in XMLRPC server and proxy. Requires
python-2.6 or later to provide the ssl module.
"""

import os
import sys
import Pyro.core
import Pyro.protocol


# Binary wrapping (for symmetry with xmlrpc implementation)
def wrapbinary(data):
    """Pack binary data - no action required"""
    return data
    
def unwrapbinary(binary):
    """Unpack binary data - no action required"""
    return binary


class InsecurePyroServerProxy(Pyro.core.DynamicProxyWithAttrs): 
    """Insecure XMLRPC server proxy suitable for our use cases"""
    def __init__(self, address_tuple, **kwargs):
        """Translate address_tuple to suitable uri"""
        kwargs['uri'] = 'PYROLOC://%s:%d/base' % address_tuple
        Pyro.core.DynamicProxyWithAttrs.__init__(self, '%(uri)s' % kwargs)


class SecurePyroServerProxy(Pyro.core.DynamicProxyWithAttrs): 
    """Secure XMLRPC server proxy suitable for our use cases"""
    def __init__(self, address_tuple, **kwargs):
        """Prepare secure socket and translate address_tuple to suitable uri"""
        kwargs['uri'] = 'PYROLOCSSL://%s:%d/base' % address_tuple
        # requires m2crypto module and concatenated ssl key/cert
        Pyro.config.PYROSSL_CERTDIR = '.'
        Pyro.config.PYROSSL_SERVER_CERT = 'combined.pem'
        Pyro.config.PYROSSL_CA_CERT = 'cacert.pem'
        Pyro.config.PYROSSL_CLIENT_CERT = 'combined.pem'
        Pyro.config.PYRO_DNS_URI = True
        Pyro.core.DynamicProxyWithAttrs.__init__(self, '%(uri)s' % kwargs)


class BaseHelper(Pyro.core.ObjBase):
    """Wrapper for all exposed objects and functions"""
    def __init__(self):
        """Prepare public base"""
        Pyro.core.ObjBase.__init__(self)


class IntrospectionHelper:
    """For introspection functions"""
    def __init__(self):
        """Prepare public introspection functions"""
        pass

    def listMethods(self):
        """List available methods"""
        # TODO: should look up methods from parent
        return ['listMethods']


class SecurePyroServer(Pyro.core.Daemon):
    """Secure Pyro server with automatic keep-alive support.

    Optional SSL key and certificate paths are exposed as key_path and
    cert_path arguments that may be overriden in instantiation if they are not
    the default combined.pem and combined.pem in the current directory.

    You can create suitable key and cert files with:
    openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem
    
    The optional ssl_version, ca_certs and cert_reqs arguments can be used to
    control additional low level settings during instantiation.
    They map directly to the corresponding ssl.wrap_socket arguments, so
    please refer to the ssl module documentation for details.

    The server uses a ssl_version default of None which allows the
    client to select whatever SSL or TLS protocol that it implements.
    """
    def __init__(self, addr, allow_none=True, key_path='combined.pem',
                 cert_path='combined.pem', ca_certs=None, cert_reqs=None,
                 ssl_version=None):
        """Overriding __init__ method of the Pyro server Daemon to add SSL in
        between basic init and network activation.
        """
        # Validate arguments possibly supplied by user
        if not os.path.isfile(key_path):
            raise ValueError("No such server key: %s" % key_path)
        if not os.path.isfile(cert_path):
            raise ValueError("No such server certificate: %s" % cert_path)
        # requires m2crypto module, concatenated ssl key/cert and cacert
        proto = 'PYROSSL'
        Pyro.config.PYROSSL_CERTDIR = os.path.join(os.getcwd(),
                                                   os.path.dirname(key_path))
        if ca_certs:
            Pyro.config.PYROSSL_CA_CERT = ca_certs[0]
        else:
            Pyro.config.PYROSSL_CA_CERT = 'cacert.pem'
        Pyro.config.PYROSSL_SERVER_CERT = cert_path
        Pyro.config.PYROSSL_CLIENT_CERT = cert_path
        Pyro.config.PYRO_DNS_URI = True
        Pyro.core.initServer(banner=0)
        Pyro.core.Daemon.__init__(self, prtcol=proto, host=addr[0],
                                  port=addr[1])
        # Expose everything as attributes of base object
        self.base = BaseHelper()
        self.connectPersistent(self.base, 'base')
        
    def register_instance(self, obj, name=None):
        """Fake object registration interface like xmlrpc"""
        # Skip name server and bind wrap object to 'all' with method x.
        # client must open proxy to URI/all to enable use of proxy.x() 
        instance_name = name
        if not name:
            instance_name = obj.__name__
        setattr(self.base, instance_name, obj)

    def register_introspection_functions(self):
        """Fake introspection registration interface like xmlrpc"""
        system = IntrospectionHelper()
        self.register_instance(system, 'system')

    def serve_forever(self):
        """Fake xmlrpc server request loop interface"""
        self.requestLoop()
            

class InsecurePyroServer(Pyro.core.Daemon): 
    """Insecure Pyro server"""
    def __init__(self, addr, allow_none=True):
        Pyro.core.initServer(banner=0)
        Pyro.core.Daemon.__init__(self, host=addr[0], port=addr[1])

        # Expose everything as attributes of base object
        self.base = BaseHelper()
        self.connectPersistent(self.base, 'base')
        
    def register_instance(self, obj, name=None):
        """Fake object registration interface like xmlrpc"""
        # Skip name server and bind wrap object to 'all' with method x.
        # client must open proxy to URI/all to enable use of proxy.x() 
        instance_name = name
        if not name:
            instance_name = obj.__name__
        setattr(self.base, instance_name, obj)

    def register_introspection_functions(self):
        """Fake introspection registration interface like xmlrpc"""
        system = IntrospectionHelper()
        self.register_instance(system, 'system')

    def serve_forever(self):
        """Fake xmlrpc server request loop interface"""
        self.requestLoop()


if __name__ == '__main__':
    address_tuple = ("localhost", 8000)
    if sys.argv[1:]:
        address_tuple = (sys.argv[1], address_tuple[1])
    if sys.argv[2:]:
        address_tuple = (address_tuple[0], int(sys.argv[2]))
    if 'client' in sys.argv[3:]:
        if 'insecure' in sys.argv[3:]:
            print "Open InsecurePyroServerProxy for %s:%s" % address_tuple
            proxy = InsecurePyroServerProxy(address_tuple)
        else:
            print "Open SecurePyroServerProxy for %s:%s" % address_tuple
            proxy = SecurePyroServerProxy(address_tuple)
        print "requesting list of methods from server on %s:%d" % address_tuple
        reply = proxy.system.listMethods()
        print "server replied: %s" % reply
        #reply = proxy.true()
        #print "server replied: %s" % reply
    else:
        if 'insecure' in sys.argv[3:]:
            print "Starting InsecurePyroServer on %s:%s" % address_tuple
            server = InsecurePyroServer(address_tuple)
        else:
            print "Starting SecurePyroServer on %s:%s" % address_tuple
            server = SecurePyroServer(address_tuple)
        server.register_introspection_functions()
        server.serve_forever()
