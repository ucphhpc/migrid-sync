#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# VncServerHandler - A FSM managing the logic for Vnc server communication.
#
# Depends on:
# - proxy.protocols.rfb
# - proxy.requesthandler
# - logging
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
from struct import unpack
from binascii import hexlify
from requesthandler import RequestHandler
from d3des import generate_response, decrypt_response, verify_response
import rfb
import time

class VncServerHandler(RequestHandler):

  password = 'leela'
  securityTypeCount = None
  secType = 1

  def __init__(self, request, client_address, server):
    
    self.buffersize = 12
    self.vnc_clients = []
    self.migraId = None
    self.serverInit = None
    
    RequestHandler.__init__(self, request, client_address, server)

  def datareceived(self, data):
    
    # Receive protocol version, send protocol version
    if self.state == 0:
      
      logging.debug('%s received protocol [%s] from vncserver ' % (self, data))
            
      if data == rfb.protocolVersion():
        logging.debug('%s sending protocol [%s] to vncserver ' % (self, rfb.protocolVersion()))
        self.buffersize = 1
        self.request.sendall(rfb.protocolVersion())
        self.state += 10
      else:
        logging.debug('%s Closed connection due to invalid version.' % self)
        self.closeConnection()

    # Receive security type count, choose one and send it back
    elif self.state == 10:
      
      self.securityTypeCount = unpack('!B', data)
      logging.debug('%s about to receive [%s] security types from vncserver' % (self, self.securityTypeCount))      
      
      if (self.securityTypeCount > 0):
        self.buffersize = self.securityTypeCount[0]
        self.state = 11
      else:
        self.closeConnection()
    
    # Receive "self.securityTypeCount" security types, then pick one
    elif self.state == 11:
      
      logging.debug('%s received security types [%s] from vncserver ' % (self, hexlify(data)))
      logging.debug('%s sending choice [%s] to vncserver ' % (self, hexlify(rfb.securityType(self.secType))))
      self.request.sendall(rfb.securityType(self.secType))
      self.buffersize = 4
      self.state = 30

    # Do authentification, this is skipped when choosing security type None
    elif self.state == 20:
      response = generate_response(self.password, data)
      logging.debug('%s received auth challenge [%s]: ' % (self, hexlify(data)))
      logging.debug('%s sending encrypted response [%s]: ' % (self, hexlify(response)))
      self.request.sendall(rfb.vncAuthResponse(response))
      
      # do auth based of chosen method      
      self.state = 30

    # Receive security result, send client init
    elif self.state == 30:
      
      secResult = unpack('!I', data)
      if secResult == (0,): # SUCCESS
        logging.debug('%s send client init message to vncserver'  % self)
        self.request.sendall(rfb.clientInit(True))
        self.buffersize = 24
        self.state = 40
      else: # FAILURE
        self.buffersize = secResult[0]
        self.state = 31
    
    # Received auth failure reason
    elif self.state == 31:
      
      logging.debug('%s received security result [%s] from vncserver ' % (self, hexlify(data)))
      
      if data == rfb.securityResult(False):
        logging.debug('Closed connection due to invalid auth.')
        self.closeConnection()
      else:
        logging.debug('%s send client init message to vncserver'  % self)
        self.request.sendall(rfb.clientInit(True))
        self.buffersize = 24
        self.state = 40
      
    # Receive server init, start sending client messages  
    elif self.state == 40:
          
      self.serverInit = unpack('!HHBBBBHHHBBBBBBI', data)
      logging.debug('%s received server init [%s] len %d hostlen %d'  % (self, self.serverInit, len(self.serverInit), self.serverInit[15]))
      
      self.buffersize = self.serverInit[15]
      self.state = 41

    # Receive server name, send pixelformat and encodings      
    elif self.state == 41:
      
      hostname = data
      
      self.migraId = generate_response(hostname, rfb.vncAuthChallenge())
      
      logging.info('[hostname=%s] [migraid=%s]' % (hostname, hexlify(self.migraId)))
      
      # Set pixel and set encodings
      self.request.sendall(rfb.setPixelFormat(32, 24, False, True, 255, 255, 255, 16, 8, 0))
      self.request.sendall(rfb.setEncodings())
      self.buffersize = 1024
      
      self.state = 50
      
    elif self.state == 50:
            
      # The first byte off all request are the messageType
      # Determine client request and based on policy: forward, local, drop the message.
      messageType = data[0:1]
      knownMessageType = False
      for messageTypesName, messageTypeValue in rfb.clientMessages.iteritems():
        if messageTypeValue == messageType:
          knownMessageType = True
          logging.debug('%s Received message type [%s] from vncserver' % (self, messageTypesName))
            
      # Forward request to client
      logging.debug("%s [clients=%d] >>" % (self, len(self.vnc_clients)))
        
      # Try to find a client connection      
      if len(self.vnc_clients)  == 0:
        
        logging.debug("%s Trying to find a matching vncclient" % self)
        
        self.lock.acquire()
        
        for t in self.threads:        
          if t.__class__.__name__ == 'VncClientHandler' and \
            t.migraId == self.migraId and \
            t.migraId != None:
            
            logging.debug("%s found %s migraIds:[\n %s,\n  %s]" % (self, t, hexlify(t.migraId), hexlify(self.migraId)))
            self.vnc_clients.append(t)
            
        self.lock.release()
      
      # Forward to client(s)
      if len(self.vnc_clients) > 0:
                
        for client in self.vnc_clients:
          logging.debug("%s [forwarding=%s,\n  to client=%s\n  from server %s]" % (self, hexlify(messageType), hexlify(client.migraId), hexlify(self.migraId)))
          
          try:
            client.request.sendall(data)
          except:
            self.vnc_clients.remove(client)
            logging.exception("%s client disconnected %s" % (self, hexlify(client.migraId)))
            logging.debug("%s client disconnected %s" % (self, hexlify(client.migraId)))
      
      logging.debug("%s   <<" % self)
          
    else:
      logging.debug('%s Closed connection due to invalid/unknown state.' % self)
      self.closeConnection()