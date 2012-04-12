#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# VncClientHandler - A FSM managing the logic for Vnc client communication.
# @author Simon A. F. Lund
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
from binascii import hexlify

from struct import pack, unpack

from requesthandler import RequestHandler
import SocketServer
from d3des import generate_response, decrypt_response, verify_response
import rfb

class VncClientHandler(RequestHandler):
  
  def __init__(self, request, client_address, server):
    
    self.buffersize = 12
    self.vnc_server    = None
    self.migraId   = None # Minimum intrusion grid remote access identity
    self.password  = 'leela'
    
    RequestHandler.__init__(self, request, client_address, server)
    
  def connectionStarted(self):
    logging.debug("%s Connection started, sending protocol version: [%s]" % (self, rfb.protocolVersion()))
    self.request.sendall(rfb.protocolVersion())
  
  def datareceived(self, data):
        
    # receive protocol version and send security types
    if self.state == 0:
     
      logging.debug("%s received client protocol [%s]" % (self, data))
      
      if data == rfb.protocolVersion():
        logging.debug("%s Sending security types to client" % self)
        self.request.sendall(rfb.securityTypes())
        self.buffersize = 1
        self.state += 10
      else:
        logging.debug("%s sending 'invalid auth' to client" % self)
        self.request.sendall(rfb.invalidVersion())
        logging.debug('%s Closed connection due to invalid version.' % self)
        self.closeConnection()

    # received clients chosen security type, start authentification
    elif self.state == 10:
      
      logging.debug("%s received security type [%s] from client" % (self, hexlify(data)))
      
      # VNC authentification:
      if data == rfb.security['VNC_AUTH']:
        logging.debug("%s sending auth challenge: [%s] to client" % (self, hexlify(rfb.vncAuthChallenge())))
        self.request.sendall(rfb.vncAuthChallenge())
        self.state += 10
        self.buffersize = 16
      # None
      elif data == rfb.security['NONE']:
        logging.debug("%s sending security result OK1 to client" % self)
        self.request.sendall(rfb.securityResult(True))
        self.buffersize = 0
        self.state += 20 # Proceed to initilization (30)
        
      # Implement other authentification mechanisms here if
      # specifications for TightVNC / UltraVNC can be found.
      else:
        logging.debug("%s sending security result BAD to client" % self)
        self.request.sendall(rfb.securityResult(False))
        self.closeConnection()
    
    # received security response from client, send security result back
    elif self.state == 20:
      
      logging.debug("%s received security response [%s] from client" % (self, hexlify(data)))
      logging.debug("%s decrypted response [%s] from client" % (self, hexlify(decrypt_response(self.password, data))))
      
      self.buffersize = 1 # TODO: does this work??
      
      # Do a stuff depending on auth method, currently only
      #if verify_response(self.password, data, rfb.vncAuthChallenge()):
      if 1:
        logging.debug("%s sending security result OK2 to client" % self)
        self.request.sendall(rfb.securityResult(True))
        self.state += 10
        
        # TODO: store the auth reponse
        self.migraId = data
      else:
        logging.debug('%s Closed connection invalid authentification.' % self)
        self.request.sendall(rfb.securityResult(False))
        self.closeConnection()
    
    # received client init, sending server init
    elif self.state == 30:
      
      logging.debug("%s received client init [%s]" % (self, hexlify(data)))
      logging.debug("%s sending server init to client" % self)
      
      if 1: # TODO: Verify client message and store it in client structure
        
        serverInit = None
        
        # TODO: IMPROVE ON THIS
        self.lock.acquire()
        
        for t in self.threads:        
          if t.__class__.__name__ == 'VncServerHandler' and \
            t.migraId == self.migraId and \
            t.migraId != None:

            serverInit = t.serverInit
            logging.debug("%s trying to find a serverInit [%s] [%s,%s]" % (self, serverInit, serverInit[0],serverInit[1]))

        self.lock.release()
        
        if serverInit != None:
            self.request.sendall(rfb.serverInit(serverInit[0], serverInit[1], rfb.PIXEL_FORMAT, 'MIG Virtual Machine.'))
        else:
            # TODO: do something better when server is not connected yet.
            self.request.sendall(rfb.serverInit(1024, 768, rfb.PIXEL_FORMAT, 'MIG Virtual Machine.'))
            
        self.buffersize = 1024
        self.state += 10
      else:
        logging.debug('%s Closed connection due to bad initialisation.'  % self)
        self.closeConnection()
    
    # Vnc doing it's thing
    elif self.state == 40:
      
      # The first byte off all request are the messageType
      # Determine client request and based on policy: forward, local, drop the message.
      messageType = data[0:1]
      knownMessageType = False
      for messageTypesName, messageTypeValue in rfb.clientMessages.iteritems():
        if messageTypeValue == messageType:
          knownMessageType = True
          logging.debug('%s Received message [%s]' % (self, messageTypesName))
      
      if not knownMessageType:
        logging.debug('%s Unknown messagetype [%s]' % (self, messageType))
      
      logging.debug("%s   >>" % self)
      
      # Try to find a server connection
      if self.vnc_server == None:
        
        logging.debug("%s Trying to find a matching vncserver" % self)
        
        self.lock.acquire()
        for t in self.threads:        
          if t.__class__.__name__ == 'VncServerHandler' and \
            t.migraId == self.migraId and \
            t.migraId != None:
            self.vnc_server = t
            logging.debug("%s found %s migraIds:[\n %s,\n  %s]" % (self, self.vnc_server, hexlify(self.vnc_server.migraId), hexlify(self.migraId)))

        self.lock.release()

      # Forward request to server
      if self.vnc_server != None:
        
        try:
          logging.debug("%s [forwarding=%s,\n from client=%s\n to server %s]" % (self, hexlify(messageType), hexlify(self.migraId), hexlify(self.vnc_server.migraId)))        
          self.vnc_server.request.sendall(data)
        except:
          logging.exception("%s server disconnected %s" % (self, hexlify(self.vnc_server.migraId)))
          self.vnc_server = None
                
      logging.debug("%s   <<" % self)
      
      # Put this somewhere else, it's very sexy and very experimental :)
      # TODO:  reverse the text, fix colors
      if messageType == rfb.clientMessages.get('FRAMEBUFFER_UPDATE_REQUEST') and self.vnc_server == None:
        
        logging.debug("%s trying to send fake framebufferupdate" % self)
        blockSize = 1024 * 768 * (32 / 8)
        input = open('/home/safl/proxy/vncmedia/wait.bmp', 'r')
        block = input.read(blockSize+70) # funny offset due to bmp representation
        block = block[70::]
        
        fakestatus = rfb.Rectangle(0, 0, 1024, 768, block)
        
        framebufferupdate = pack("!BBHHHHHi", 0, 0, 1,
                                 fakestatus.x, fakestatus.y, fakestatus.width, fakestatus.height,
                                 0)
        try:          
          self.request.sendall(framebufferupdate)
          self.request.sendall(block[::-1]) # reverse the order
        except:
          logging.exception('%s Closed connection due to failure in sending status image!' % self)
          self.closeConnection()          
      
    else:
      logging.debug('%s Closed connection due to unknown data input!' % self)
      self.closeConnection()