#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# isjobactive - [insert a few words of module description on this line]
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

# Created 271006 by Martin Rehr
import cgi
import cgitb; cgitb.enable()
import os

# MiG imports
from shared.cgishared import init_cgiscript_possibly_with_cert
from shared.resadm import get_sandbox_exe_stop_command
from shared.fileio import unpickle

### Main ###
(logger, configuration, cert_name_no_spaces, o) = init_cgiscript_possibly_with_cert()

# Check we are using correct method
if (os.getenv("REQUEST_METHOD") != "GET"):
    # Request method is wrong
    o.out("You must use HTTP GET!")
    o.reply_and_exit(o.CLIENT_ERROR)

# check that the job exists, iosessionid is ok (does symlink exist?)
fieldstorage = cgi.FieldStorage()
iosessionid = fieldstorage.getfirst("iosessionid", None)
sandboxkey = fieldstorage.getfirst("sandboxkey", None)
exe_name = fieldstorage.getfirst("exe_name", None)

if iosessionid and os.path.islink(configuration.webserver_home + iosessionid):
    o.client("jobactive")
    o.reply_and_exit(o.OK)
else:
    if sandboxkey and exe_name:
        (status, msg) = get_sandbox_exe_stop_command(configuration.sandbox_home, sandboxkey, exe_name, logger)
        if status:
            o.client("stop_command: %s" % (msg))
        else:
            o.client(msg)
    else:
        o.client("jobinactive")

    o.reply_and_exit(o.ERROR)



