#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sandbox_remove_user - [insert a few words of module description on this line]
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


"""This script removes a given sandbox user from the user list"""
from __future__ import print_function
from __future__ import absolute_import

import sys
import os

from mig.shared.serial import load, dump
from mig.shared.conf import get_configuration_object

configuration = get_configuration_object()

sandboxdb_file = configuration.sandbox_home + os.sep\
     + 'sandbox_users.pkl'

PW = 0
RESOURCES = 1

try:
    username = sys.argv[1]
except:
    print('You must specify a username.')
    sys.exit(1)

# Load the user file

userdb = load(sandboxdb_file)

if username in userdb:

    # Open the user file in write-mode - this deletes the file!

    del userdb[username]
    dump(userdb, sandboxdb_file)
    print('Username %s has now been deleted!' % username)
else:
    print('Sorry, username does not exist: %s' % username)
    sys.exit(0)
