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

import sys
import getopt
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

def default_configuration():
    """Return dictionary with default configuration values"""
    # Use empty address to listen on all interfaces
    conf = {'address': "", 'port': 8000}
    return conf

def usage():
    """Usage help"""
    print("Usage: %s" % sys.argv[0])
    print("Run RPC benchmark server")
    print("Options and default values:")
    for (key, val) in default_configuration().items():
        print("--%s: %s" % (key, val))
                
def x():
        return True

def main(conf):
    """Run minimal benchmark server"""
    server = SimpleXMLRPCServer((conf['address'], conf['port']))
    print("Listening on '%(address)s:%(port)d..." % conf)
    server.register_function(x, "x")
    server.serve_forever()


if __name__ == '__main__':
    conf = default_configuration()

    try:
        raise Exception("test")
    except Exception as err:
        print("caught error: %s" % err)
        
    # Parse command line

    try:
            (opts, args) = getopt.getopt(sys.argv[1:],
                                         'a:hp:', [
                    'address=',
                    'help',
                    'port=',
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
            except Exception, err:
                print('Error in parsing port value: %s' % err)
                sys.exit(1)
        elif opt in ('-u', '--url'):
            conf["url"] = val
        else:
            print("unknown option: %s" % opt)
            usage()
            sys.exit(1)
    main(conf)
