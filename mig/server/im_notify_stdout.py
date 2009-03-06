#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# im_notify_stdout - [insert a few words of module description on this line]
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

# Write im messages to stdout instead of sending them

import string
import time

im_msg_stdin_filename = "im_msg_stdin"

try:
    im_msg_stdin = open(im_msg_stdin_filename, "r")
except Exception, e:
    print "could not open im_msg_stdin %s, exception: %s" % (im_msg_stdin_filename, e)

# never exit    
while True:
    line = im_msg_stdin.readline()
    if line  == '':
	time.sleep(1)
	continue		  
    if string.find(line.upper(), "SENDMESSAGE ") == 0:
	print line
    else:
	print "unknown message received: %s" % line
