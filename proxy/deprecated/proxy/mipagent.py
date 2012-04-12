#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# Mip Agent
#
# @author Simon Andreas Frimann Lund
#
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
import logging
import mip
import socket

from binascii import hexlify

from struct import pack, unpack

logging.basicConfig(filename='proxyd.log',level=logging.DEBUG)

HOST = 'amigos18.diku.dk'
PORT = 8113
request = mip.request('jegersimon', 80)

print " [%s,%d] " % (hexlify(request), len(request))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

s.send(request)

while 1: # Wait for setup requests
  data = s.recv(1024)
  s.close()
  print 'Received', repr(data)