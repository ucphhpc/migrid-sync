#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
#
# sftp-truncate-debug - [optionally add short module description on this line]
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

#
# Debug issue with truncate operation on sshfs mounted MiG home

import os
import sys

local_path = sys.argv[1]
remote_path = sys.argv[2]

try:
    local_fd = open(local_path, "w+")
    local_fd.truncate(0)
    local_fd.close()
    print "local truncate on %s succeeded" % local_path
    
except Exception, exc:
    print "local truncate on %s failed: %s" % (local_path, exc) 
try:
    remote_fd = open(remote_path, "w+")
    remote_fd.truncate(0)
    remote_fd.close()
    print "remote truncate on %s succeeded" % remote_path
except Exception, exc:
    print "remote truncate on %s failed: %s" % (remote_path, exc) 
      
