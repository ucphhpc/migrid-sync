#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
import time, logging, sys, threading, os, socket, ConfigParser

from SimpleHTTPServer import SimpleHTTPRequestHandler
from migtcpserver import MiGTCPServer
from proxyagenthandler import ProxyAgentHandler
from proxyclienthandler import ProxyClientHandler

import daemon

class Proxy(daemon.Daemon):
  
  default_conf      = 'etc/migproxy.conf'
  section           = 'daemon'
  section_settings  = 'proxy'
        
  def run(self):
    
    # Load configuration from file
    cp = ConfigParser.ConfigParser()
    cp.read([self.default_conf])
    
    self.clientPort = int(cp.get(self.section_settings, 'client_port'))
    self.agentPort  = int(cp.get(self.section_settings, 'agent_port'))
    self.appletPort = int(cp.get(self.section_settings, 'applet_port'))
    
    self.key  = cp.get(self.section_settings, 'key')
    self.cert = cp.get(self.section_settings, 'cert')
    self.ca   = cp.get(self.section_settings, 'ca')
    
    if (self.key and self.cert and self.ca):
      self.tls_conf = {'key':self.key, 'cert':self.cert, 'ca' : self.ca}
    else:
      self.tls_conf = None
    
    print '%d %d %d %s %s %s' % (self.clientPort, self.agentPort, self.appletPort, self.key, self.cert, self.ca)
    
    # Get it on!
    self.agentServer  = None
    self.clientServer = None
    self.appletServer = None    
        
    # Listen for clients, via ProxyClientHandler
    ProxyClientHandler.use_tls = self.tls_conf != None
    
    self.clientServer = MiGTCPServer(('', self.clientPort), ProxyClientHandler)
    
    broker_thread = threading.Thread(target=self.clientServer.serve_forever)
    broker_thread.setDaemon(True)
    broker_thread.start()
    
    # Listen for servers, via the ProxyAgentHandler
    self.agentServer = MiGTCPServer(('', self.agentPort), ProxyAgentHandler, self.tls_conf)
    
    mip_thread = threading.Thread(target=self.agentServer.serve_forever)
    mip_thread.setDaemon(True)
    mip_thread.start()    
    
    # The appletServer below is a quick and dirty http server for serving up applets
    #
    # TODO: Find a better way to manage java applets,
    #       they must be served from the same server as they need to connect to
    #       in most cases this will be the proxy. So having a integrated applet
    #       server actually makes sense.
    os.chdir('applets')
    self.appletServer= MiGTCPServer(('', self.appletPort), SimpleHTTPRequestHandler)
    
    client_thread = threading.Thread(target=self.appletServer.serve_forever)
    client_thread.setDaemon(True)
    client_thread.start()
    
    # That's it, let the threads do their job
    while 1:
      time.sleep(1000)

if __name__ == '__main__':

  try:
    Proxy().main()
  except:
    logging.exception('Unexpected error: %s' % sys.exc_info()[2])
  
else:
  pass