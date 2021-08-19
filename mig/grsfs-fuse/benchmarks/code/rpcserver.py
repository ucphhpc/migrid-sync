#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rpcserver - minimal rpc benchmark server
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


"""Minimal RPC benchmark server"""
from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
import sys
import getopt

def default_configuration():
    """Return dictionary with default configuration values"""
    # Use empty address to listen on all interfaces
    conf = {'address': "", 'port': 8001, 'transport': 'xmlrpc'}
    return conf

def usage():
    """Usage help"""
    print("Usage: %s" % sys.argv[0])
    print("Run RPC benchmark server")
    print("Options and default values:")
    for (key, val) in default_configuration().items():
        print("--%s: %s" % (key, val))
                
def true():
    """Minimal dummy function"""
    return True


def main(conf):
    """Run minimal benchmark server"""
    if conf["transport"] == "xmlrpc":
        from xmlrpc.server import SimpleXMLRPCServer, \
             SimpleXMLRPCRequestHandler
        handler = SimpleXMLRPCRequestHandler
        # Force keep-alive support - please note that pypy clients may need to
        # force garbage collection to actually close connection
        handler.protocol_version = 'HTTP/1.1'
        server = SimpleXMLRPCServer((conf['address'], conf['port']),
                                    requestHandler=handler)
        # Do not log requests
        server.logRequests = 0
        print("Listening on '%(address)s:%(port)d..." % conf)
        server.register_function(true, 'x')
        server.serve_forever()
    elif conf["transport"] in ["pyro", "pyrossl"]:
        import Pyro.core
        import Pyro.protocol


        class AllWrap(Pyro.core.ObjBase):
            """Pyro needs an object to expose functions/methods"""
            def x(self):
                """Minimal dummy method"""
                return True


        if conf["transport"] == "pyrossl":
            # requires m2crypto module, concatenated ssl key/cert and cacert
            proto = 'PYROSSL'
            Pyro.config.PYROSSL_CERTDIR = '.'
            Pyro.config.PYROSSL_CA_CERT = 'cacert.pem'
            Pyro.config.PYROSSL_SERVER_CERT = "combined.pem"
            Pyro.config.PYROSSL_CLIENT_CERT = "combined.pem"
            Pyro.config.PYRO_DNS_URI = True
        else:
            proto = 'PYRO'
        Pyro.core.initServer(banner=0)
        server = Pyro.core.Daemon(prtcol=proto, host=conf["address"],
                                  port=conf["port"])
        # Optional client certificate check
        #if conf["transport"] == "pyrossl":
        #    server.setNewConnectionValidator(Pyro.protocol.BasicSSLValidator())
        print("Listening on '%(address)s:%(port)d..." % conf)
        # Skip name server and bind wrap object to 'all' with method x.
        # client must open proxy to URI/all to enable use of proxy.x() 
        server.connectPersistent(AllWrap(), "all")
        server.requestLoop()
    else:
        print("unknown transport: %(transport)s" % conf)
        sys.exit(1)

if __name__ == '__main__':
    conf = default_configuration()

    # Parse command line

    try:
        (opts, args) = getopt.getopt(sys.argv[1:],
                                     'a:hp:t:', [
            'address=',
            'help',
            'port=',
            'transport=',
            ])
    except getopt.GetoptError as err:
        print('Error in option parsing: ' + err.msg)
        usage()
        sys.exit(1)
        
    for (opt, val) in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('-a', '--address'):
            conf["address"] = val
        elif opt in ('-p', '--port'):
            try:
                conf["port"] = int(val)
            except ValueError as err:
                print('Error in parsing %s value: %s' % (opt, err))
                sys.exit(1)
        elif opt in ('-t', '--transport'):
            conf["transport"] = val
        else:
            print("unknown option: %s" % opt)
            usage()
            sys.exit(1)
    main(conf)
    
