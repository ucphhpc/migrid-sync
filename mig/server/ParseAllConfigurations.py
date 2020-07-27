#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ParseAllConfigurations - [insert a few words of module description on this line]
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

from __future__ import print_function
import os
import sys

from shared import confparser
from shared.conf import get_configuration_object

if os.getenv('HTTP_METHOD'):
    print('CGI access disabled because of security implications')
    sys.exit(1)

resource_home = '/home/mig/resource_home'

configuration = get_configuration_object()
for (root, dirs, files) in os.walk(resource_home):
    for file in files:
        if file.startswith('config.MiG'):
            unique_resource_name = root.replace(resource_home, '')
            print(unique_resource_name)
            (status, msg) = confparser.run(configuration,
                                           root + '/' + file,
                                           unique_resource_name)
            print(file)
            print(msg)
            if status:
                print('ok')
            else:
                print('error')
