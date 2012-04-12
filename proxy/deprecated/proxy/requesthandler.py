#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
import logging
import sys
import socket
import threading
from binascii import unhexlify
import time
import SocketServer

class RequestHandler(SocketServer.BaseRequestHandler):
    
  state = 0
  buffersize  = 1024 # Change this dynamicly to control the stream of incoming data.
  running     = True # Determine whether the handler should continue, usefull for safeguarding.
  auto_close  = True
  
  # TODO: These are shared amongst requesthandlers.
  threads = []
  lock = threading.Lock()

  def __init__(self, request, client_address, server):
    
    self.state = 0
    self.cur_thread = threading.currentThread()

    logging.debug("%s starting." % self)
    
    RequestHandler.lock.acquire()
    self.threads      = RequestHandler.threads
    self.threads.append(self)
    RequestHandler.lock.release()
    
    SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
  
  def setup(self):
    pass
  
  def handle(self):
    
    logging.debug("%s started." % self)
    
    try:
      self.connectionStarted()
    except:
      self.running = False
      logging.exception("%s Unexpected error:" % self)

    while self.running:
      
      try:
        data = self.request.recv(self.buffersize)
        logging.debug('%s Read %d bytes' % (self, self.buffersize))
      except: # Handle premature close of connection
        logging.exception('%s Error receiving %d bytes of data.' % (self, self.buffersize))        
        self.running = False
        break
      
      if not data:
        logging.debug('%s Data empty', self)
        break # Stop when the other side stops sending data
      
      try:
        self.datareceived(data)
      except:
        logging.exception('%s Error in eventfunction: datareceived.', self)
        self.running = False
    
    logging.debug("%s Closing." % self)
    try:
      if self.auto_close:
        self.request.close()
      RequestHandler.lock.acquire()      
      self.threads.remove(self)      
      RequestHandler.lock.release()
    except:
      logging.exception('%s Error in closing connection.', self)
      
    try:
      self.connectionLost()      
    except:
      logging.exception('%s Error in event function.', self)
    
  def closeConnection(self):
    self.running = False
    self.request.close()
    logging.debug('%s Closed connection.', self)
  
  def datareceived(self, data): pass
  def connectionStarted(self): pass
  def connectionLost(self): pass    