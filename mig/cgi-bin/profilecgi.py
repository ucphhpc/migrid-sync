#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fakecgi - fake a cgi request
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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
from __future__ import print_function
from __future__ import absolute_import

import os
import sys

import cProfile
import importlib
import io
import pstats

from mig.shared.base import distinguished_name_to_user
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import csrf_field
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.url import parse_qs


def usage():
    """Basic usage help."""
    print('Usage: %s SCRIPT [METHOD] [QUERY] [RUNAS] [REMOTE_USER] [REMOTE_ADDR] [AUTO_CSRF]' % sys.argv[0])


if len(sys.argv) < 2:
    usage()
    sys.exit(1)

script = sys.argv[1]
query = ''
method = 'GET'
run_as_dn = '/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Test User/emailAddress=nosuch@bogusdomain.net'
auto_csrf = False
remote_user = ''
remote_addr = ''
print(sys.argv)
if sys.argv[2:]:
    method = sys.argv[2]
if sys.argv[3:]:
    query = sys.argv[3]
if sys.argv[4:]:
    run_as_dn = sys.argv[4]
if sys.argv[5:]:
    remote_user = sys.argv[5]
if sys.argv[6:]:
    remote_addr = sys.argv[6]
if sys.argv[7:]:
    auto_csrf = (sys.argv[7].lower() in ('yes', 'true'))

run_as_user = distinguished_name_to_user(run_as_dn)
client_id = run_as_dn

if method.lower() == 'post' and auto_csrf:
    configuration = get_configuration_object()
    form_method = method.lower()
    csrf_limit = get_csrf_limit(configuration)
    target_op = os.path.splitext(os.path.basename(script))[0]
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    # IMPORTANT: in python3 urllib.parse.parse_qs* changed to '&' as sep to
    #            avoid a web cache poisoning issue (CVE-2021-23336)
    query += "&%s=%s" % (csrf_field, csrf_token)

print("run as user: %s" % run_as_user)
extra_environment = {
    'REQUEST_METHOD': method,
    'SERVER_PROTOCOL': 'HTTP/1.1',
    'GATEWAY_INTERFACE': 'CGI/1.1',
    'PATH': '/bin:/usr/bin:/usr/local/bin',
    'REMOTE_ADDR': '127.0.0.1',
    'SSL_CLIENT_S_DN': run_as_user['distinguished_name'],
    'SSL_CLIENT_S_DN_C': run_as_user.get('country', 'NA'),
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
extra_environment['SCRIPT_URI'] = 'https://localhost/cgi-bin/%s' % script

if remote_user:
    extra_environment['REMOTE_USER'] = remote_user

if remote_addr:
    extra_environment['REMOTE_ADDR'] = remote_addr

os.environ.update(extra_environment)

script_path = script
if not os.path.isabs(script_path):
    script_path = os.path.abspath(script_path)
if not os.path.exists(script_path):
    print("No such script: %s" % script_path)
    sys.exit(1)
backend = script.rstrip('.py')
module_path = 'mig.shared.functionality.%s' % backend

print("Running %s with environment:\n%s" % (script, os.environ))
profiler = cProfile.Profile()
profiler.enable()
try:
    # Import main from backend module

    print("import main from %r" % module_path)
    # NOTE: dynamic module loading to find corresponding main function
    module_handle = importlib.import_module(module_path)
    main = module_handle.main
except Exception as err:
    print("could not import %r (%s): %s" % (backend, module_path, err))
    sys.exit(2)
try:
    user_arguments_dict = parse_qs(query)
    (output_objects, (ret_code, ret_msg)) = main(client_id, user_arguments_dict)
except Exception as err:
    import traceback
    print("%s script crashed: %s" % (backend, traceback.format_exc()))
    sys.exit(3)

profiler.disable()
s = io.StringIO()
stats = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
# Print top 20 functions
stats.print_stats(20)
print(s.getvalue())
