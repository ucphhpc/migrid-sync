#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
import time
import logging
import sys
import threading
import os

from proxy.vncclienthandler import VncClientHandler
from proxy.vncserverhandler import VncServerHandler
from proxy.mipserver import MipServer
from proxy.mipserver import MipBroker
from proxy.tcplistener import TcpListener
from SimpleHTTPServer import SimpleHTTPRequestHandler
from proxy.echo_handler import MyEchoHandler

import daemon

logging.basicConfig(filename='proxyd.log',level=logging.DEBUG)

class Proxy(daemon.Daemon):
  
  default_conf  = 'proxyd.conf'
  section       = 'proxyd'
  tls_conf      = {'key':'host.key', 'cert':'host.cert'}
  
  def __init__(self):
    
    self.maxclients = 100
    self.maxservers = 100
    
    self.serverPort = 8112
    self.clientPort = 8111
    self.mipPort    = 8113
    self.appletPort = 8114
    self.mipBrokerPort  = 8115
    
    # Access to these structues should be safeguarded
    self.servers    = []
    self.clients    = []
    self.sessions   = []
    self.listeners  = []
    
    self.serverListener = None
    self.clientListener = None
    self.mipListener    = None
    self.brokerListener = None
    self.appletListener = None
    
  def run(self):

    # Standalone
    #self.serverListener = TcpListener(('', self.serverPort), VncServerHandler)
    #self.listeners.append(self.serverListener)
    #server_thread = threading.Thread(target=self.serverListener.serve_forever)
    #server_thread.setDaemon(True)
    #server_thread.start()
    #
    #self.clientListener = TcpListener(('', self.clientPort), VncClientHandler)
    #self.listeners.append(self.clientListener)
    #client_thread = threading.Thread(target=self.clientListener.serve_forever)
    #client_thread.setDaemon(True)
    #client_thread.start()
    
    # Listen for servers
    #self.mipListener = TcpListener(('', self.mipPort), MipServer)
    self.mipListener = TcpListener(('', self.mipPort), MipServer, self.tls_conf)
    self.listeners.append(self.mipListener)
    mip_thread = threading.Thread(target=self.mipListener.serve_forever)
    mip_thread.setDaemon(True)
    mip_thread.start()
    
    # Listen for clients
    self.brokerListener = TcpListener(('', self.mipBrokerPort), MipBroker)
    self.listeners.append(self.brokerListener)
    broker_thread = threading.Thread(target=self.brokerListener.serve_forever)
    broker_thread.setDaemon(True)
    broker_thread.start()
    
    #self.ssltestListener = TcpListener(('', self.mipBrokerPort), MyEchoHandler, tls_conf)
    #self.listeners.append(self.ssltestListener)
    #ssl_thread = threading.Thread(target=self.ssltestListener.serve_forever)
    #ssl_thread.setDaemon(True)
    #ssl_thread.start()
    
    # The listener below is a quick and dirty http server for serving up applets
    #
    # TODO: Find a better way to manage java applets,
    #       they must be served from the same server as they need to connect to
    #       in most cases this will be the proxy. So having a integrated applet
    #       server actually makes sense.
    os.chdir('applets')
    self.appletListener = TcpListener(('', self.appletPort), SimpleHTTPRequestHandler)
    self.listeners.append(self.appletListener)
    client_thread = threading.Thread(target=self.appletListener.serve_forever)
    client_thread.setDaemon(True)
    client_thread.start()
  
    # Wait for the listeners to exit
    # Join can take a timeout parameter.
    #for t in self.listeners:
    #  t.join()
    #  logging.debug("Listener closing????")  
    
    while 1:
      try:
        time.sleep(0.0001)
      except KeyboardInterrupt:
        for t in self.listeners:
          t.shutdown()

if __name__ == '__main__':

  try:
    Proxy().run()
  except:
    logging.exception('LORAT')
  
else:
  pass