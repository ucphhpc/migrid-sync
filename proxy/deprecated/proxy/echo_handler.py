#!/usr/bin/env python
# -*- coding: utf-8 -*-
import SocketServer
import socket

class MyEchoHandler(SocketServer.BaseRequestHandler):
  """
  The RequestHandler class for our server.

  It is instantiated once per connection to the server, and must
  override the handle() method to implement communication to the
  client.
  """

  def handle(self):
    # self.request is the TCP socket connected to the client
    while 1:
      self.data = self.request.recv(1024).strip()
      print "%s wrote:" % self.client_address[0]
      print self.data
      # just send back the same data, but upper-cased
      self.request.send(self.data.upper())
      #self.request.send("EHJ")
