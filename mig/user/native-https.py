#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# native-https - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Test native python SSL using HTTPSConnection against MiG
server.
"""

import os
import sys
import httplib

try:
    HOME = os.getenv('HOME')
except Exception:
    HOME = '.'
args = ['mig-1.imada.sdu.dk', 443, '%s/.mig/key.pem' % HOME,
        '%s/.mig/cert.pem' % HOME]
input_args = sys.argv[1:]
if len(input_args) > 4:
    input_args = input_args[:4]
args = input_args[:len(input_args)] + args[len(input_args):]

(server, port, key_path, cert_path) = args

print 'Connecting to %s:%s using key in %s and cert in %s' % tuple(args)
try:
    connection = httplib.HTTPSConnection(server, int(port), key_path,
            cert_path)

    sys.stdin = os.open('pp.txt', os.O_RDWR)
    connection.connect()

    print 'Received server certificate data:'

    # print repr(ssl_sock.server())

    print repr(connection.sock._ssl.server())
    print 'Received CA certificate data:'

    # print repr(ssl_sock.issuer())

    print repr(connection.sock._ssl.issuer())

    print ''

    request = ['GET', '/']

    print 'sending request:\n%s' % request

    connection.request(request[0], request[1])
    reply = connection.getresponse()
    print reply.status, reply.reason
    data = reply.read()
    print 'received:\n%s' % data
except Exception, err:

    print 'Failed to create SSL connnection: %s' % err
    sys.exit(1)

try:
    connection.close()
except:
    pass
