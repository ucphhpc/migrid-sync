#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sandbox_list_users - [insert a few words of module description on this line]
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

""" List sandbox users and print total number of registered users """
import pickle
import os
import sys
from shared.conf import get_configuration_object
configuration = get_configuration_object()

sandboxdb_file = configuration.sandbox_home + os.sep + "sandbox_users.pkl"

userdb = None
if not os.path.isfile(sandboxdb_file):
    print "%s is not an existing file!" % sandboxdb_file
    sys.exit(1)
    
try:
    fd = open(sandboxdb_file, 'rb')
    userdb = pickle.load(fd)
    fd.close()
except Exception, exc:
    print "Exception reading %s, (%s)" % (sandboxdb_file, exc)
user_count = 0

for key, value in userdb.items():
    print key, ":", value
    user_count += 1

print "Total number of registered users: %d" % user_count
