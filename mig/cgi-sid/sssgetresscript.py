#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sssgetresscript - For updating resource scripts inside SSS
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

# Martin Rehr 27/03/2007

import cgi
import cgitb
cgitb.enable()
import os

from shared.sandbox import get_resource_name
from shared.resadm import get_frontend_script, get_master_node_script

from shared.cgishared import init_cgiscript_possibly_with_cert

# ## Main ###
# Get Querystring object

fieldstorage = cgi.FieldStorage()
(logger, configuration, client_id, o) = \
    init_cgiscript_possibly_with_cert()

# Check we are using GET method

if os.getenv('REQUEST_METHOD') != 'GET':

    # Request method is not GET

    o.out('You must use HTTP GET!')
    o.reply_and_exit(o.ERROR)

# Make sure that we're called with HTTPS.

if str(os.getenv('HTTPS')) != 'on':
    o.out('Please use HTTPS with session id for authenticating job requests!'
          )
    o.reply_and_exit(o.ERROR)

action = fieldstorage.getfirst('action', None)
sandboxkey = fieldstorage.getfirst('sandboxkey', None)
exe_name = fieldstorage.getfirst('exe_name', 'localhost')

if not sandboxkey:
    o.out('No sandboxkey provided')
    o.reply_and_exit(o.ERROR)

(status, unique_resource_name) = get_resource_name(sandboxkey, logger)
if not status:
    o.out(unique_resource_name)
    o.reply_and_exit(o.ERROR)

if action == 'get_frontend_script':
    (status, msg) = get_frontend_script(unique_resource_name, logger)
elif action == 'get_master_node_script':
    (status, msg) = get_master_node_script(unique_resource_name,
            exe_name, logger)
else:
    status = False
    msg = 'Unknown action: %s' % action

# Get a resource for the connection client.

o.out(msg)
if status:
    o.reply_and_exit(o.OK)
else:
    o.reply_and_exit(o.ERROR)
