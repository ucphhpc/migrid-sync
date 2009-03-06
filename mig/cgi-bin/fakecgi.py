#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fakecgi - [insert a few words of module description on this line]
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

# DO NOT CHANGE THIS SCRIPT TO BE GENERALLY CGI EXECUTABLE!
# It should only be accessible from the command line to avoid
# unauthenticated user access to CGI scripts.

"""This is a simple wrapper to fake actual CGI execution of a
script. Some of the MiG cgi scripts may require the user, Test User, to exist for actions to work."""

import os
import sys

def usage():
    print "Usage: %s SCRIPT [QUERY]" % sys.argv[0]

if len(sys.argv) < 2:
    usage()
    sys.exit(1)

script = sys.argv[1]
query = ''
if len(sys.argv) > 2:
    query = sys.argv[2]

extra_environment = {'REQUEST_METHOD': 'GET', 'SSL_CLIENT_S_DN': '/C=DK/L=IMADA/O=MiG/CN=Test User', 'SERVER_PROTOCOL': 'HTTP/1.1', 'PATH': '/bin:/usr/bin:/usr/local/bin', 'SSL_CLIENT_I_DN': '/C=DK/ST=Denmark/O=IMADA/OU=MiG/CN=MiGCA', 'SSL_CLIENT_I_DN_O': 'IMADA', 'REMOTE_ADDR': '127.0.0.1', 'SSL_CLIENT_I_DN_C': 'DK', 'SSL_CLIENT_S_DN_O': 'MiG', 'SSL_CLIENT_S_DN_L': 'IMADA', 'SSL_CLIENT_S_DN_C': 'DK', 'SSL_CLIENT_I_DN_ST': 'Denmark', 'GATEWAY_INTERFACE': 'CGI/1.1', 'SSL_CLIENT_S_DN_CN': 'Test User', 'SSL_CLIENT_I_DN_CN': 'MiGCA'}

extra_environment['SCRIPT_FILENAME'] = script
extra_environment['QUERY_STRING'] = query
extra_environment['REQUEST_URI'] = '%s%s' % (script, query)
extra_environment['SCRIPT_URL'] = script
extra_environment['SCRIPT_NAME'] = script
extra_environment['SCRIPT_URI'] = 'https://localhost/cgi-bin/%s' % script
os.environ.update(extra_environment)

os.system(script)
