#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resource_list - [insert a few words of module description on this line]
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

# Minimum Intrusion Grid
# Martin Rehr rehr@imada.sdu.dk August 2005

import cgi
import cgitb
cgitb.enable()
import os
import sys
import time

from shared.html import get_cgi_html_header
from shared.conf import get_configuration_object

# ## Main ###

cert_name = str(os.getenv('SSL_CLIENT_S_DN_CN'))
cert_no_spaces = cert_name.replace(' ', '_')
if cert_no_spaces == 'None':
    sys.exit(1)

configuration = get_configuration_object()
logger = configuration.logger
logger.info('Resource list GUI: start')

print '''Content-type: text/html

'''

form = cgi.FieldStorage()

print get_cgi_html_header('MiG Resource administration',
                          'Welcome to the MiG resource administration.')

dir_list = os.listdir(configuration.resource_home)
for file in dir_list:
    hosturl = file[0:file.rindex('.')]
    hostidentifier = file[file.rindex('.') + 1:]
    print "     <A HREF='resource_edit.py?hosturl=" + hosturl\
         + '&hostidentifier=' + hostidentifier\
         + "'>edit</A>&nbsp;&nbsp;<B>" + file + '</B><BR>'

print """	<hr>
	    <form action="./resource_edit.py" method="post">
	    <input type="hidden" name="new_resource" value="true">
	    <input type="submit" name="New" value="New">
	    </form>
	    </body>
	    </html>
	    """

