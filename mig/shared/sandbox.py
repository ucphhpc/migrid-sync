#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sandbox - [insert a few words of module description on this line]
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

"""Sandbox functions"""

import os

# MiG imports

from conf import get_configuration_object


def get_resource_name(sandboxkey, logger):
    configuration = get_configuration_object()

    # Retrieve resource_name from sandboxkey symbolic link

    sandbox_link = configuration.sandbox_home + sandboxkey

    if os.path.exists(sandbox_link):
        unique_resource_name = \
            os.path.basename(os.path.realpath(sandbox_link))
        return (True, unique_resource_name)
    else:
        msg = 'Remote IP: %s, No sandbox with sandboxkey: %s'\
             % (os.getenv('REMOTE_ADDR'), sandboxkey)
        logger.error(msg)
        return (False, msg)


