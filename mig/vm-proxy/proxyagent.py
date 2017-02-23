#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# Proxy Agent - Agent enabling secured ingoing traffic via a MiG proxy
#               without opening services to anything other than localhost.
#
# @author Simon Andreas Frimann Lund
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
import os
import socket
import sys
import threading
import time
import ConfigParser
import SocketServer
from struct import unpack, pack
from threading import Thread

from OpenSSL import SSL


import daemon
import mip
from plumber import *


class ProxyAgent(daemon.Daemon):
  
  default_conf      = 'etc/proxyagent.conf'
  section           = 'daemon'
  section_settings  = 'agent'

  control_socket  = None  # Life-line to the proxy
  connections     = []    # List of connections to close and cleanup gracefully
  buffer_size     = 4096  # Must be "mod 2", 4096 might be too big for some...
                          # but it is much faster if it's supported
                        
  retry_count   = -1  # Retry forever: retry_count = -1
  retry_timeout = 60  # Seconds to wait before trying to retry
  
  # Debug variables
  handshake_count = 0
  setup_count     = 0

  def run(self):
    # Load configuration from file
    cp = ConfigParser.ConfigParser()
    cp.read([self.default_conf])
    
    self.proxy_host = cp.get(self.section_settings, 'proxy_host')
    self.proxy_port  = int(cp.get(self.section_settings, 'proxy_port'))
    
    self.retry_count    = int(cp.get(self.section_settings, 'retry_count'))
    self.retry_timeout  = int(cp.get(self.section_settings, 'retry_timeout'))
    
    self.identifier  = cp.get(self.section_settings, 'identifier')
    
    self.key  = cp.get(self.section_settings, 'key')
    self.cert = cp.get(self.section_settings, 'cert')
    self.ca   = cp.get(self.section_settings, 'ca')
    
    if (self.key and self.cert and self.ca):
      self.tls_conf = {'key':self.key, 'cert':self.cert, 'ca' : self.ca}
    else:
      self.tls_conf = None
    
    print '%s %d %s %s %s %s' % (self.proxy_host, self.proxy_port, self.identifier, self.key, self.cert, self.ca)
    
    # Now connect
    self.connect(self.proxy_host, self.proxy_port, self.identifier, self.key and self.cert and self.ca) 

  # Helper for ssl
  def verify_cb(self, conn, cert, errnum, depth, ok):
    logging.debug('Proxy certificate: %s %s' % (cert.get_subject(), ok))
    return ok
  
  def connect(self, host, port, identity, tls=True):    
    
    initial_retry   = self.retry_count
    
    while initial_retry == -1 or initial_retry != 0: # Retry proxy connection when it fails
              
      initial_retry -= 1
      try:
        
        # Connect to proxy and identify
        self.handshake(host, port, identity)
        
        # Handle Setup request forever
        while 1:
          
          try:
            
            data = self.control_socket.recv(1) # Get the message type
            
            if (data == mip.messages['SETUP_REQUEST']):
              
              (ticket,) = unpack('!I', self.control_socket.recv(4))        
              (proxy_host_length,) = unpack('!I', self.control_socket.recv(4))
              proxy_host = self.control_socket.recv(proxy_host_length)      
              (proxy_port,) = unpack('!I', self.control_socket.recv(4))
              
              (machine_host_length,) = unpack('!I', self.control_socket.recv(4))
              machine_host = self.control_socket.recv(machine_host_length)
              (machine_port,) = unpack('!I', self.control_socket.recv(4))
              
              self.handle_setup_request(ticket, proxy_host, proxy_port, machine_host, machine_port, tls)
            else:
              logging.debug(' Broken data! %s' % repr(data))
            
          except:
            logging.debug(' Unexpected error, shutting down control connection.')
            logging.exception('%s ' % sys.exc_info()[2])
            self.control_socket.close()
            break
      
      except:
        logging.error(' Error in control connections, retrying in %d seconds' % self.retry_timeout)
        self.control_socket.close()
        time.sleep(self.retry_timeout)  
  
  """
    handshake,
   
    Identify proxy agent to proxy server
    TODO: catch those exceptions and add return error code...
  """
  def handshake(self, host, port, identity, tls=True):
    
    self.handshake_count += 1
    logging.debug(" Handshake count = %d" % self.handshake_count)
    
    handshakeMessage = mip.handshake(1, identity)
    
    dir = os.path.dirname(sys.argv[0])
    if dir == '':
        dir = os.curdir
    
    if tls:
      
      # Initialize context
      ctx = SSL.Context(SSL.TLSv1_METHOD)
      ctx.set_verify(SSL.VERIFY_NONE, self.verify_cb)
      ctx.use_privatekey_file (os.path.join(dir, 'certs/client.pkey'))
      ctx.use_certificate_file(os.path.join(dir, 'certs/client.cert'))
      ctx.load_verify_locations(os.path.join(dir, 'certs/CA.cert'))
      
      # Set up client
      logging.debug(' Socket: TLS wrapped! %s')
      self.control_socket = SSL.Connection(ctx, socket.socket(socket.AF_INET, socket.SOCK_STREAM))      
      
    else:
      logging.debug(' Socket: plain! %s')
      self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  
    self.control_socket.connect((host, port))
    self.control_socket.send(handshakeMessage)      
  
  """
   handle_setup_request,
   
   Set's up a new tunnel between local endpoint and proxy server
  """
  def handle_setup_request(self, ticket, proxy_host, proxy_port, machine_host, machine_port, tls=True):
    
    self.setup_count += 1
    logging.debug(" Setup request count = %d" % self.setup_count)
    
    logging.debug('Performing setup (ticket:%s, phost:%s, pport:%s,\n  mhost:%s,mport:%s)' % (ticket, proxy_host, proxy_port, machine_host, machine_port))
    
    # Connect to proxy
    dir = os.path.dirname(sys.argv[0])
    if dir == '':
        dir = os.curdir
    
    proxyConnected    = False
    endPointConnected = False
  
    # Connect to endpoint  
    try:
      endpoint = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      endpoint.connect((machine_host, machine_port))
    
      endPointConnected = True
    except:
      logging.debug('Socket error when contacting endpoint.')
    
    # Connect to proxy and prepend setup response
    if endPointConnected:
      try:
        
        if tls:
          # Initialize context
          ctx = SSL.Context(SSL.TLSv1_METHOD)
          ctx.set_verify(SSL.VERIFY_NONE, self.verify_cb) # Demand a certificate
          ctx.use_privatekey_file (os.path.join(dir, 'certs/client.pkey'))
          ctx.use_certificate_file(os.path.join(dir, 'certs/client.cert'))
          ctx.load_verify_locations(os.path.join(dir, 'certs/CA.cert'))
          
          logging.debug(' Socket: TLS wrapped! %s')
          proxy_socket = SSL.Connection(ctx, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        else:
          logging.debug(' Socket: plain! %s')
          proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          
        proxy_socket.connect((proxy_host, proxy_port))
                      
        proxyConnected = True
      except:
        logging.exception('Socket error when contacting proxy. %s %d' %(proxy_host, proxy_port))
    
    # Send status to the connection handler in proxy
    if proxyConnected:
      proxy_socket.sendall(mip.setup_response(ticket, int(endPointConnected and proxyConnected)))
    
    # Send status back over control line to proxy  
    self.control_socket.sendall(mip.setup_response(ticket, int(endPointConnected and proxyConnected)))  
    
    # Setup tunnel between proxy and endpoint  
    if proxyConnected and endPointConnected:
      
      # Add connections to list so they can be shut down gracefully
      self.connections.append(endpoint)
      self.connections.append(proxy_socket)
      mario = PlumberTS(endpoint, proxy_socket, self.buffer_size, True)
      #mario = Plumber(endpoint, ss, 1024, True)
      logging.debug('Setup done!')
      
    else:
      logging.debug('Setup Failure!')
    
    return proxyConnected and endPointConnected

if __name__ == '__main__':
  
  try:
    ProxyAgent().main()
  except:
    logging.exception('Unexpected error: %s' % sys.exc_info()[2])
  
else:
  pass
