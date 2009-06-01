#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# Proxy Agent - Agent enabling secured ingoing traffic via a MiG proxy
#               without opening services anything other than localhost.
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
from mipserver import *
import sys

if __name__ == '__main__':
  
  if len(sys.argv) < 4:
    print 'Usage: python[2] mipclient.py HOST PORT IDENTIFIER'
    sys.exit(1)

  # TODO: - Sanitize commandline arguments
  #       - Provide cert files as commandline arguments
  clientConnect(sys.argv[1], int(sys.argv[2]), sys.argv[3])
  
else:
  pass