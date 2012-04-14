#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# MipBroker - An Mip broker
#
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
import SocketServer
import threading
from struct import unpack, pack
import mip

class MipBroker(SocketServer.BaseRequestHandler):
        
  def __init__(self, request, client_address, server):
    
    self.cur_thread = threading.currentThread()
    self.running = True
    
    logging.debug("%s starting." % self)
    
    SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
  
  def setup(self):
    logging.debug("%s started." % self)
    
    try:
      logging.debug('%s MIP Broker is here!' % self)
          
      #MipServer.lock.acquire()
      for proxy in MipServer.proxies:
        logging.debug('%s proxy %s' %(self, proxy))
      #MipServer.lock.release()
      
      logging.debug('%s Thats it im done..' % self)
    except:
      self.running = False
      logging.exception("%s Unexpected error:" % self)

      # Find a server
      # Send request to server
      # Connect pinhole
      pass
  
  def handle(self):
    while self.running:
      pass
    
  def closeConnection(self):
    self.running = False
    self.request.close()
    logging.debug('%s Closed connection.', self)
  
"""
  def datareceived(self, data):
    
    logging.debug('%s MIP Broker is here!' % self)
          
    MipServer.lock.acquire()
    self.proxies.append(proxyHost)
    for proxy in MipServer.proxies:
      logging.debug('%s proxy %s' %(self, proxy))
    MipServer.lock.release()
    
    logging.debug('%s Thats it im done..' % self)
    """