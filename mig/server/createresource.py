#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createresource - Create resource from user request file
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""Add MiG resource from pending request file"""
from __future__ import print_function
from __future__ import absolute_import

import sys

from mig.shared.conf import get_configuration_object
from mig.shared.resource import create_resource


def usage(name='createresource.py'):
    """Usage help"""
    return """Usage:
%(name)s RESOURCE_FQDN OWNER_ID RESOURCE_CONFIG

The script adds .COUNTER to the resources unique id"""\
         % {'name': name}


# ## Main ###

if '__main__' == __name__:
    if not sys.argv[3:]:
        print(usage())
        sys.exit(1)
        
    resource_name = sys.argv[1].strip().lower()
    client_id = sys.argv[2].strip()
    pending_file = sys.argv[3].strip()
    
    configuration = get_configuration_object()

    (create_status, msg) = create_resource(configuration, client_id,
                                           resource_name, pending_file)
    if create_status:
        print('Resource created with ID: %s.%s' % (resource_name, msg))
    else:
        print('Resource creation failed: %s' % msg)
