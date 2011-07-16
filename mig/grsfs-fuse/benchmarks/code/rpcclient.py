#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rpcclient - simple rpc client benchmark
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


"""Simple RPC client benchmark"""

import sys
import getopt
import timeit

allowed_transports ={'xmlrpc': "http://localhost:8001/",
                     'pyro': "PYROLOC://localhost:8001/all",
                     'pyrossl': "PYROLOCSSL://localhost:8001/all"}

def default_configuration():
    """Return dictionary with default configuration values"""
    conf = {'uri': '', 'repeat': 3, 'number': 10000, 'transport': 'xmlrpc'}
    return conf

def usage():
    """Usage help"""
    print("Usage: %s" % sys.argv[0])
    print("Run RPC client benchmark")
    print("Options and default values:")
    for (key, val) in default_configuration().items():
        print("--%s: %s" % (key, val))
                
def main(conf):
    """Run timed benchmark"""
    print timeit.repeat("proxy.x()", setup = conf['setup'],
                        repeat=conf['repeat'], number=conf['number'])

if __name__ == '__main__':
    conf = default_configuration()

    # Parse command line

    try:
        (opts, args) = getopt.getopt(sys.argv[1:],
                                     'hn:r:t:u:', [
            'help',
            'number=',
            'repeat=',
            'transport=',
            'uri=',
            ])
    except getopt.GetoptError, err:
        print('Error in option parsing: ' + err.msg)
        usage()
        sys.exit(1)
        
    for (opt, val) in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('-n', '--number'):
            try:
                conf["number"] = int(val)
            except ValueError, err:
                print('Error in parsing %s value: %s' % (opt, err))
                sys.exit(1)
        elif opt in ('-r', '--repeat'):
            try:
                conf["repeat"] = int(val)
            except ValueError, err:
                print('Error in parsing %s value: %s' % (opt, err))
                sys.exit(1)
        elif opt in ('-t', '--transport'):
            if not val in allowed_transports.keys():
                print("unknown transport: %s" % val)
                usage()
                sys.exit(1)
            conf["transport"] = val
        elif opt in ('-u', '--uri'):
            conf["uri"] = val
        else:
            print("unknown option: %s" % opt)
            usage()
            sys.exit(1)
    # Use default transport specific uri if left unset
    if not conf['uri']:
        conf['uri'] = allowed_transports[conf["transport"]]
    # Manual garbage collection is required with pypy to avoid permanent
    # hang waiting for client shutdown when keep-alive is enabled on server
    conf['setup'] = """
try:
    proxy = None
    import gc
    gc.collect()
except Exception, exc:
    print 'proxy shutdown failed: ', exc
"""
    if conf["transport"] == "xmlrpc":
        conf['setup'] += """
import xmlrpclib
proxy = xmlrpclib.ServerProxy('%(uri)s')
""" % conf
    elif conf["transport"] in ["pyro", "pyrossl"]:
        conf['setup'] += """
import Pyro.core
proxy = Pyro.core.getProxyForURI('%(uri)s')
""" % conf
    else:
        print("Unsupported transport: %(transport)s" % conf)
        sys.exit(1)
    main(conf)
