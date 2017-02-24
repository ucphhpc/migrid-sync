#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ProxyAgentHandler - An Mip server
#
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

import logging
import md5
import os
import sys
import time
import SocketServer
from binascii import hexlify
from struct import unpack, pack

import mip
import rfb
from d3des import generate_response, decrypt_response, verify_response
from migtcpserver import MiGTCPServer
from plumber import *

def vnc_jobid(job_id='Unknown'):
  """
  1: Job identifier = 64_5_30_2009__10_10_15_localhost.0

  2: Md5 sum (16bytes) 32 char hex. string = 01b19818762fbaf81693001639b1379c

  3: Lower to (8bytes) 16 char hex. string: 01 b1 98 18 76 2f ba f8

  4: Convert to user inputable ascii table characters:

      Ascii table offset by 64 + [0-16]
  
  This methods provides 127^8 identifiers.
  """
  
  job_id_digest = md5.new(job_id).hexdigest()[:16]  # 2
  password = ''
  for i in range(0, len(job_id_digest), 2):         # 3, 4
    
    char = 32 + int(job_id_digest[i:i+2], 16)
    if char > 251:
      password += chr(char/3)
    elif char > 126:
      password += chr(char/2)
    else:
      password += chr(char)
  
  return password


# TODO: -add timeouts to the handshake, it should not wait forever if the other side is hanging in a handshake
class ProxyAgentHandler(SocketServer.BaseRequestHandler):
  """ProxyAgentHandler,
  A MIP server.
  """
  
  def setup(self):

    logging.debug("%s Started." % (self))
    MiGTCPServer.count = MiGTCPServer.count + 1
    logging.debug('%s Do I know you? %d %s' % (self, MiGTCPServer.count, MiGTCPServer))

  def vncServerStrategy(self):
    ### TODO: Do a fake server handshake
    secType = 1
          
    # Receive protocol version, send protocol version
    srv_ver = self.request.recv(12)
    logging.debug('%s received protocol [%s] from vncserver ' % (self, srv_ver))
    
    if srv_ver == rfb.protocolVersion():
      logging.debug('%s sending protocol [%s] to vncserver ' % (self, rfb.protocolVersion()))
      self.request.sendall(rfb.protocolVersion())
    else:
      logging.debug('%s Closed connection due to invalid version.' % self)
      self.request.close()
    
    # Receive security type count, choose one and send it back  
    srv_sec_count =  unpack('!B', self.request.recv(1))
    
    if (srv_sec_count > 0):
      srv_sec_types = self.request.recv(srv_sec_count[0])
      logging.debug('%s received security types [%s] from vncserver ' % (self, hexlify(srv_sec_types)))
      logging.debug('%s sending choice [%s] to vncserver ' % (self, hexlify(rfb.securityType(secType))))
      self.request.sendall(rfb.securityType(secType))

    else:
      self.closeConnection()
    
    # Receive security result
    srv_sec_res = self.request.recv(4)
  
  def handle(self):
    
    logging.debug('%s MIP Server is here!' % self)
    
    identifier  = None
    proxyHost   = None
    
    #try:
    #  self.request.settimeout(30)
    data = self.request.recv(1)
    #except:
    #  logging.debug('%s Proxy Agent Request timeout!' % self)
    #  data = -1

    if data == mip.messages['HANDSHAKE']:
      
      try:
        logging.debug('%s Data-raw [%s] ' % (self, repr(data)))
        handshake = self.request.recv(5)
        logging.debug('%s Init-raw [%s] ' % (self, repr(handshake)))
        initMessage = unpack('!BI', handshake) # Grab the proxys handshake
        logging.debug('%s Init [%s] ' % (self, initMessage))
        
        identifier  = self.request.recv(initMessage[1])
        
        # Transform identifier to user inputable representation, vnc style
        identifier = hexlify(generate_response(vnc_jobid(identifier), rfb.vncAuthChallenge()))
        
        logging.debug('%s Ident [%s] ' % (self, identifier))
              
        proxyHost   = mip.ServerInfo(self.request, self.client_address, initMessage[1], identifier)
        logging.debug('%s Proxy Agent [%s] ' % (self, proxyHost))        
        
      except: # Handle premature close of request
        logging.exception('%s Error receiving data.' % self)
        
      if not data:
        logging.debug('%s Data empty' % self)
        pass
      
      logging.debug('%s Taking a lock' % self)
      
      MiGTCPServer.proxyLock.acquire()
                  
      # Check if it already there ( in case of reconnect )
      if identifier in MiGTCPServer.proxy_agents:
        del MiGTCPServer.proxy_agents[identifier]
      
      # Add proxy agent to list of agent
      MiGTCPServer.proxy_agents[identifier] = proxyHost
      MiGTCPServer.proxyLock.release()      
      
      logging.debug('%s Thats it im done..' % self)    
    
    # TODO: this is where daisy chaining stuff chould be added...
    elif data == mip.messages['SETUP_REQUEST']:
      
      logging.debug('%s setup request ' % self)

    elif data == mip.messages['SETUP_RESPONSE']:
      
      logging.debug('%s response request ' % self)
      
      (ticket,status) = unpack('!IB', self.request.recv(5))
      logging.debug('%s ticket %s, status %s' % (self, ticket, status))
      
      # handle vnc server
      self.vncServerStrategy()
      
      # Add proxy_agent to connection pool
      MiGTCPServer.connectionCondition.acquire()
      MiGTCPServer.connections[ticket] = mip.ServerInfo(self.request, self.client_address, 0, 3)
      MiGTCPServer.connectionCondition.notifyAll()
      MiGTCPServer.connectionCondition.release()  
        
    else:
      logging.debug('%s Incorrect messagetype %s' % (self, repr(data)))
      
    # This is fucking annoying! If the handler exited then the socket is closed... so it must stay alive doing shit but consume resources...
    while 1: 
      time.sleep(1000)
