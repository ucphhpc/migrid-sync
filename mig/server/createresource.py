#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createresource - [insert a few words of module description on this line]
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

# Initial version by Henrik Hoey Karlsen
# Modifications by Martin Rehr

"""Add MiG resource"""

import sys

from shared.conf import get_configuration_object
from shared.resource import create_resource, \
    create_new_resource_configuration, remove_resource
from shared.cgioutput import CGIOutput


def usage(name='createresource.py'):
    return """Usage:
%(name)s RESOURCE_FQDN OWNER_ID [RESOURCE_CONFIG]

The script adds .COUNTER to the resources unique id"""\
         % {'name': name}


# ## Main ###

argc = len(sys.argv)
if not (argc == 3 or argc == 4):
    print usage()
    sys.exit(1)

if argc == 4:
    resource_configfilename = sys.argv[3].strip()
else:
    resource_configfilename = ''

resource_name = sys.argv[1].strip().lower()
client_id = sys.argv[2].strip()

configuration = get_configuration_object()
logger = configuration.logger
o = CGIOutput(logger)

(status, msg, resource_identifier) = create_resource(resource_name,
        client_id, configuration.resource_home, logger)
o.out(msg)

if status and argc == 4:
    (status, msg) = create_new_resource_configuration(
        resource_name,
        client_id,
        configuration.resource_home,
        configuration.resource_pending,
        resource_identifier,
        resource_configfilename,
        )
    o.out(msg)

    if not status:
        (status2, msg) = remove_resource(configuration.resource_home,
                resource_name, resource_identifier)
        o.out(msg)

if status:
    o.client('\n - you might need to do a SSH to the resource before starting the resource to get it in known_hosts!'
              + '\n (this is because SSH hostkey checking is disabled)')
    o.reply_and_exit(o.OK)
else:
    o.reply_and_exit(o.CLIENT_ERROR)

