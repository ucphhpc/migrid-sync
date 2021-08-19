#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# webserver - [insert a few words of module description on this line]
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

"""Simple test CGI server"""
from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
import sys
import http.server
import http.server
import socketserver


class Handler(http.server.CGIHTTPRequestHandler):

    cgi_directories = ['/cgi-bin']


class ThreadingServer(socketserver.ThreadingMixIn,
    http.server.HTTPServer):

    pass


class ForkingServer(socketserver.ForkingMixIn,
    http.server.HTTPServer):

    pass


# Listen address

IP = '127.0.0.1'
PORT = 8080

print('Serving at %s port %d' % (IP, PORT))

print('before attr override: have fork: %s' % Handler.have_fork)
Handler.have_fork = False
print('after attr override: have fork: %s' % Handler.have_fork)

# server = BaseHTTPServer.HTTPServer((IP, PORT), Handler)
# server.serve_forever()

# server = ThreadingServer((IP,PORT), Handler)

server = ForkingServer((IP, PORT), Handler)

print('server attr: have fork: %s'\
     % server.RequestHandlerClass.have_fork)
try:
    while True:
        sys.stdout.flush()
        server.handle_request()
except KeyboardInterrupt:
    print('Server killed')

