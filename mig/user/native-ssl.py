#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# native-ssl - native ssl socket access
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""Test native python SSL sockets against MiG server:
This test is based on the example at 
http://docs.python.org/lib/socket-example.html
"""

import os
import sys
import socket

try:
    HOME = os.getenv('HOME')
except Exception:
    HOME = '.'
args = ['dk-cert.migrid.org', 443, '%s/.mig/key.pem' % HOME,
        '%s/.mig/cert.pem' % HOME]
input_args = sys.argv[1:]
if len(input_args) > 4:
    input_args = input_args[:4]
args = input_args[:len(input_args)] + args[len(input_args):]

(server, port, key_path, cert_path) = args

print 'Connecting to %s:%s using key in %s and cert in %s' % tuple(args)
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server, int(port)))
    fd = open('pp.txt', 'r')
    passphrase = fd.read()
    fd.close()
    os.close(0)
    sys.stdin = open('pp.txt', 'r')
    print sys.stdin.fileno()
    ssl_sock = socket.ssl(s, key_path, cert_path)
except Exception, err:
    print 'Failed to create SSL connnection: %s' % err
    sys.exit(1)

print 'Received server certificate data:'
print repr(ssl_sock.server())
print 'Received CA certificate data:'
print repr(ssl_sock.issuer())

print ''

request = """GET / HTTP/1.0\r
Host: %s\r
\r
""" % server
print 'sending request:\n%s' % request
ssl_sock.write(request)

# Read a chunk of data.  Will not necessarily
# read all the data returned by the server.

data = ssl_sock.read()
print 'received:\n%s' % data

# Note that you need to close the underlying socket, not the SSL object.

del ssl_sock
s.close()
