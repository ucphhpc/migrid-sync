#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fakecgi - fake a cgi request
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""This is a simple wrapper to fake actual CGI GET/POST execution of a
script. Some of the MiG cgi scripts may require the provided RUNAS user
to exist for actions to work.
"""

import os
import sys

from shared.safeeval import subprocess_call
from shared.useradm import distinguished_name_to_user


def usage():
    print 'Usage: %s SCRIPT [METHOD] [QUERY] [RUNAS]' % sys.argv[0]


if len(sys.argv) < 2:
    usage()
    sys.exit(1)

script = sys.argv[1]
query = ''
method = 'GET'
run_as_dn = '/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Test User/emailAddress=nosuch@bogusdomain.net'
if sys.argv[2:]:
    method = sys.argv[2]
if sys.argv[:3]:
    query = sys.argv[3]
if sys.argv[:4]:
    run_as_dn = sys.argv[4]

run_as_user = distinguished_name_to_user(run_as_dn)

extra_environment = {
    'REQUEST_METHOD': method,
    'SERVER_PROTOCOL': 'HTTP/1.1',
    'GATEWAY_INTERFACE': 'CGI/1.1',
    'PATH': '/bin:/usr/bin:/usr/local/bin',
    'REMOTE_ADDR': '127.0.0.1',
    'SSL_CLIENT_S_DN': run_as_user['distinguished_name'],
    'SSL_CLIENT_S_DN_C': run_as_user['country'],
    'SSL_CLIENT_S_DN_O': run_as_user['organization'],
    'SSL_CLIENT_S_DN_OU': run_as_user['organizational_unit'],
    'SSL_CLIENT_S_DN_L': run_as_user['locality'],
    'SSL_CLIENT_S_DN_CN': run_as_user['full_name'],
    'SSL_CLIENT_I_DN': '/C=DK/ST=Denmark/O=IMADA/OU=MiG/CN=MiGCA',
    'SSL_CLIENT_I_DN_C': 'DK',
    'SSL_CLIENT_I_DN_ST': 'Denmark',
    'SSL_CLIENT_I_DN_O': 'IMADA',
    'SSL_CLIENT_I_DN_OU': 'MiGCA',
    'SSL_CLIENT_I_DN_CN': 'MiGCA',
    }

extra_environment['SCRIPT_FILENAME'] = script
extra_environment['QUERY_STRING'] = query
extra_environment['REQUEST_URI'] = '%s%s' % (script, query)
extra_environment['SCRIPT_URL'] = script
extra_environment['SCRIPT_NAME'] = script
extra_environment['SCRIPT_URI'] = 'https://localhost/cgi-bin/%s'\
     % script
os.environ.update(extra_environment)

if not os.path.isabs(script):
    script = os.path.abspath(script)
print "Running %s with environment:\n%s" % (script, os.environ)
subprocess_call(script, stdin=open('/dev/null', 'r'))
