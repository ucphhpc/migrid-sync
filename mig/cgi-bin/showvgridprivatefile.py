#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showvgridprivatefile - [insert a few words of module description on this line]
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

"""Show the requested file located in a given vgrids private_base dir"""

import cgi
import cgitb
cgitb.enable()
import os
import sys

from shared.validstring import valid_dir_input
from shared.cgishared import init_cgi_script_with_cert
from shared.vgrid import vgrid_is_owner_or_member

# ## Main ###

(logger, configuration, cert_name_no_spaces, o) = \
    init_cgi_script_with_cert()

fieldstorage = cgi.FieldStorage()
if not fieldstorage.getfirst('vgrid_name', '') == '':

    # using web form
    # htmlquery = "false" #changed!

    vgrid_name = fieldstorage.getfirst('vgrid_name', '')

specified_filename = fieldstorage.getfirst('file', 'index.html')

# No owner check here so we need to specifically check for illegal
# directory traversals

private_base_dir = os.path.abspath(configuration.vgrid_private_base)\
     + os.sep

if not valid_dir_input(configuration.vgrid_home, vgrid_name):
    o.out('Illegal vgrid_name: %s' % vgrid_name)
    logger.warning("showvgridprivatefile registered possible illegal directory traversal attempt by '%s': vgrid name '%s'"
                    % (cert_name_no_spaces, vgrid_name))
    o.reply_and_exit(o.CLIENT_ERROR)

filename = private_base_dir + vgrid_name + os.sep + specified_filename

if not valid_dir_input(private_base_dir, specified_filename):
    o.out('Illegal file: %s' % specified_filename)
    logger.warning("showvgridprivatefile registered possible illegal directory traversal attempt by '%s': vgrid name '%s', file '%s'"
                    % (cert_name_no_spaces, vgrid_name,
                   specified_filename))
    o.reply_and_exit(o.CLIENT_ERROR)

if not vgrid_is_owner_or_member(vgrid_name, cert_name_no_spaces,
                                configuration):
    o.client('Failure: You (%s) must be an owner or member of %s vgrid to access the entry page.'
              % (cert_name_no_spaces, vgrid_name))
    o.reply_and_exit(o.CLIENT_ERROR)

if not os.path.isfile(filename):
    o.out("%s: No such file in private section of '%s' vgrid"
           % (specified_filename, vgrid_name))
    o.reply_and_exit(o.CLIENT_ERROR)

# do not use CGIOutput if everything is ok, since we do not want a 0 (return code) on the first line

try:
    file = open(filename, 'r')

    # TODO: the html header used in this script will cause clients (browsers) to
    #       ignore newlines in the file - is that a feature or a bug?

    print str(file.read())
    file.close()
except Exception, e:
    o.out("Error reading or printing file '%s' from private section of vgrid '%s'"
           % (specified_filename, vgrid_name), str(e))
    o.reply_and_exit(o.ERROR)

# o.reply_and_exit(o.OK)
