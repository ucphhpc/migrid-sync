#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mip - An implementation of the MIP protocol messages
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

from struct import *

identifiers = {
  'PROXY'           : pack('!B', 0),
  'VIRTUAL_MACHINE' : pack('!B', 1),
  'RESSOURCE'       : pack('!B', 2),
  'USER'            : pack('!B', 3)
}

messages = {
  'HANDSHAKE'       : pack('!B', 0),
  'SETUP_REQUEST'   : pack('!B', 1),
  'SETUP_RESPONSE'  : pack('!B', 2)
}

def handshake(type, identity):
  return pack('!BBI', 0, type, len(identity))+identity
  
def setup_request(ticket, proxy_host, proxy_port, machine_host, machine_port):
  return  pack('!B', 1) +\
          pack('!I', ticket) +\
          pack('!I', len(proxy_host))    + proxy_host    + pack('!I', proxy_port) +\
          pack('!I', len(machine_host))  + machine_host  + pack('!I', machine_port)  

def setup_response(ticket, status=0):
  return pack('!BIB', 2, ticket, status)
  
class ServerInfo:
  
  def __init__(self, request, addressInfo, identifier, type):
    self.request      = request
    self.addressInfo  = addressInfo
    self.type         = type
    self.identifier   = identifier