#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
import logging, sys, socket, os, time, threading, SocketServer
from OpenSSL import SSL

"""
 Whitelisting mixin request are only allowed from the list of peers.
"""
class Whitelist:
  
  peers = []
    
  def verify_request(self, request, client_address):
    print request
    print client_address
    return false
    
  def peerAllowed(self, peer):
    return peer[0] in self.peers

"""
  Callback for certificate verification
"""
def verify_cb(conn, cert, errnum, depth, ok):
  logging.debug("%s Got certificate: %s" % (self, cert.get_subject()))
  return ok

"""
  An extension of TcpServer this adds:
  
  * Threading (mix-in)
  * Whitelisting (mix-in + server_bind)
  * FQDN/Hostname extraction (mix-in + verify_request)
  
  * TLS: tls_conf = {key='path', cert='path'}
  
"""
class TcpListener(Whitelist,
                  SocketServer.ThreadingMixIn,
                  SocketServer.TCPServer):
  
  allow_reuse_address = 1 # Mostly for testing purposes
  
  """
    Constructor overwritten to initialize TLS
  """
  def __init__(self, server_address, RequestHandlerClass, tls_conf=None):
    SocketServer.BaseServer.__init__(self, server_address, RequestHandlerClass)

    if (tls_conf !=None):
      ctx = SSL.Context(SSL.TLSv1_METHOD)
      ctx.set_options(SSL.OP_NO_SSLv2|SSL.OP_NO_SSLv3)
      ctx.set_verify(SSL.VERIFY_NONE, verify_cb)
      dir = os.curdir
      ctx.use_privatekey_file (os.path.join(dir, tls_conf['key']))
      ctx.use_certificate_file(os.path.join(dir, tls_conf['cert']))
  
      self.socket = SSL.Connection(ctx, socket.socket(self.address_family,
                                                                self.socket_type))
    else:
      self.socket = socket.socket(self.address_family, self.socket_type)
      
    self.server_bind()
    self.server_activate()    
  
  """
   verify_request,
  
   Extended to provide whitelisting features,
  """
  def verify_request(self, request, client_address):
    #return self.peerAllowed(client_address)
    return True
  
  """
   server_bind,
  
   Extended for hostname extraction, hostname is used in http servers,
   vnc servers and many others, so it is conveniently added in this generic class.
  """
  def server_bind(self):
    SocketServer.TCPServer.server_bind(self)
    host, port = self.socket.getsockname()[:2]
    
    self.server_host = host
    self.server_name = socket.getfqdn(host)
    self.server_port = port
    logging.debug("%s Listening on %d, handling %s" % (self, self.server_port, self.RequestHandlerClass))