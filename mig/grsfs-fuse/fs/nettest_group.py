#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# nettest_group - [insert a few words of module description on this line]
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

"""
Starts the required number of processes to have a full group and then leaves them alone.

Created by Jan Wiberg on 2010-03-29.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""

import os, subprocess, time

master = subprocess.Popen("python nettest_server.py", shell=True)
time.sleep(1)
replica1 = subprocess.Popen("python nettest_replica.py 1", shell=True)
time.sleep(0.5)
replica2 = subprocess.Popen("python nettest_replica.py 2", shell=True)

print "Should be good now"
time.sleep(20)
