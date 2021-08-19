#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# ProxyClientHandler - Handles connections from clients by setting up tunnels.
#                      and do content filtering stuff.
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

from future import standard_library
standard_library.install_aliases()
import logging
import md5
import os
import random
import sys
import threading
import time
import socketserver
from binascii import hexlify
from struct import unpack, pack

import mip
import rfb
from d3des import generate_response, decrypt_response, verify_response
from migtcpserver import MiGTCPServer
from plumber import *


class ProxyClientHandler(socketserver.BaseRequestHandler):

    """ProxyClientHandler,
  Handles connections from clients by setting up tunnels and do content
  filtering stuff.
  """

    use_tls = False

    def __init__(
        self,
        request,
        client_address,
        server,
        ):

        self.cur_thread = threading.currentThread()
        self.running = True
        self.count = 0

    # Parameters for setup requests

        self.ticket = random.randint(1, 9999)  # TODO: do it smarter!

        self.proxy_agent_port = 8112  # TODO: put this somewhere else!

        self.provider_port = 5900
        self.provider_address = 'localhost'
        self.provider_identifier = '__foo__'

        socketserver.BaseRequestHandler.__init__(self, request,
                client_address, server)

  # Extract client information from proxy aware user procedures

    def vncSetupStrategy(self):
        self.password = 'leela'

        logging.debug('%s Started.' % self)
        logging.debug('%s Connection started, sending protocol version: [%s]'
                       % (self, rfb.protocolVersion()))
        self.request.sendall(rfb.protocolVersion())

        cli_ver = self.request.recv(12)
        logging.debug('%s received client protocol [%s]' % (self,
                      cli_ver))

    # Offer security types

        if cli_ver[:11] == rfb.protocolVersion()[:11]:
            logging.debug('%s Sending security types to client' % self)
            self.request.sendall(rfb.securityTypes())
        else:
            logging.debug("%s sending 'invalid version' to client"
                          % self)
            self.request.sendall(rfb.invalidVersion())
            logging.debug('%s Closed connection due to invalid version.'
                           % self)
            self.request.close()

    # Receive client chosen security type

        cli_sec_type = self.request.recv(1)
        logging.debug('%s received security type [%s] from client'
                      % (self, hexlify(cli_sec_type)))

    # VNC authentification:

        if cli_sec_type == rfb.security['VNC_AUTH']:
            logging.debug('%s sending auth challenge: [%s] to client'
                          % (self,
                          hexlify(rfb.vncStaticAuthChallenge())))
            self.request.sendall(rfb.vncAuthChallenge())

            cli_sec_response = self.request.recv(16)

            logging.debug('%s received security response [%s] from client'
                           % (self, hexlify(cli_sec_response)))

      # logging.debug("%s decrypted response [%s] from client" % (self, hexlify(decrypt_response(self.password, cli_sec_response))))

      # TODO: consider if verification of the userinputable jobidentifer can
      #       be verified at this stage
      # if verify_response(self.password, data, rfb.vncAuthChallenge()):

            if 1:
                logging.debug('%s sending security result OK2 to client'
                               % self)
                self.request.sendall(rfb.securityResult(True))

        # THIS IS THE MAGIC: THE IDENTFIER IS FOUND!

                self.provider_identifier = hexlify(cli_sec_response)
            else:
                logging.debug('%s Closed connection invalid authentification.'
                               % self)
                self.request.sendall(rfb.securityResult(False))
                self.closeConnection()
        elif cli_sec_type == rfb.security['NONE']:

    # None: TODO: block this since it not usefull for proxy-awareness

            logging.debug('%s sending security result OK1 to client'
                          % self)
            self.request.sendall(rfb.securityResult(True))
        else:

    # Implement other authentification mechanisms here if
    # specifications for TightVNC / UltraVNC can be found.
    # Note: this doesn't matter in the chase of proxy-awareness... anyway this is
    #       where it would be done.

            logging.debug('%s sending security result BAD to client'
                          % self)
            self.request.sendall(rfb.securityResult(False))
            self.closeConnection()

    # Client is "authed", initialization can begin

    def setup(self):
        logging.debug('%s server PORT [%s]' % (self,
                      self.server.server_address[1]))

    # if self.server.server_address[1] == 8113:
    #  self.proxy_agent_port = 8115
    #  self.provider_port    = 22
    # else:

        self.vncSetupStrategy()

    def handle(self):

    # Find a proxy agent with self.provider_identifier

        try:

      # Find a provider

            MiGTCPServer.proxyLock.acquire()

            logging.debug('AGENTS: ')
            for shitface in MiGTCPServer.proxy_agents:
                logging.debug(' %s ' % shitface)

            logging.debug(' Searching for %s '
                          % self.provider_identifier)
            if len(MiGTCPServer.proxy_agents) > 0 \
                and self.provider_identifier \
                in MiGTCPServer.proxy_agents:

        # Provider found, sending setup request

                try:

                    MiGTCPServer.proxy_agents[self.provider_identifier].request.sendall(mip.setup_request(self.ticket,
                            self.server.server_name,
                            self.proxy_agent_port,
                            self.provider_address, self.provider_port))
                except:
                    logging.exception(' Error when sending setup request.'
                            )

        # Wait for the setup response

                try:
                    (msg_type, cli_ticket, cli_status) = unpack('!BIB',
                            MiGTCPServer.proxy_agents[self.provider_identifier].request.recv(6))
                    logging.debug('%s mshg=%s ticket=%s, status=%s'
                                  % (self, msg_type, cli_ticket,
                                  cli_status))
                except:
                    (msg_type, cli_ticket, cli_status) = (0, 0, 0)
                    logging.exception(' Error when waiting for setup response.'
                            )

        # Check status to see if end-point to be connected

                if cli_status == 0:
                    self.running = False
                    self.request.close()
            else:

                logging.debug('%s no proxy agent, closing connection.'
                              % self)
                self.running = False
                self.request.close()

            MiGTCPServer.proxyLock.release()
        except:

            self.running = False
            logging.exception('%s Unexpected failure in finding proxy agent: %s'
                               % (self, self))

        if self.running:

      # Wait for proxy agent to respond, a timeout of 5, if this does not happen within 5 second then we are dead and gone.
      # TODO: THis is not enough to keep it from hanging forever it the client
      #       just freezes after connecting the socket.

            proxy = None
            while proxy is None:

                MiGTCPServer.connectionCondition.acquire()
                MiGTCPServer.connectionCondition.wait(3)

                if len(MiGTCPServer.connections) > 0 and self.ticket \
                    in MiGTCPServer.connections:
                    proxy = MiGTCPServer.connections.pop(self.ticket)
                    logging.debug('%s found a connection! %s' % (self,
                                  proxy))

                MiGTCPServer.connectionCondition.release()

      # Start piping with proxy agent

            if not proxy is None:

                self.count = self.count + 1
                logging.debug('%s Plumbing time! %d TLS=%d' % (self,
                              self.count, self.use_tls))

        # louigi = Plumber(self.request, proxy.request, 1024, False)
        # louigi = PlumberTS(self.request, proxy.request, 1024, False)

                louigi = PlumberTS(self.request, proxy.request, 4096,
                                   False)
            else:
                logging.debug('%s Setup request failed! %d' % (self,
                              self.count))


