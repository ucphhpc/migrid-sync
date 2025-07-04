#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
#
# migproxy - [optionally add short module description on this line]
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import logging
import os
import sys
import threading
import time
import configparser
from http.server import SimpleHTTPRequestHandler

try:
    import OpenSSL
except ImportError:
    print('WARNING: the python OpenSSL module is required for vm-proxy')
    OpenSSL = None

# TODO: switch from private tls conf to this general conf
# from mig.shared.conf import get_configuration_object

import daemon
from migtcpserver import MiGTCPServer
from proxyagenthandler import ProxyAgentHandler
from proxyclienthandler import ProxyClientHandler


class Proxy(daemon.Daemon):

    default_conf = 'etc/migproxy.conf'
    section = 'daemon'
    section_settings = 'proxy'

    def run(self):
        
        # Load configuration from file

        cp = configparser.ConfigParser()
        cp.read([self.default_conf])

        self.clientPort = int(cp.get(self.section_settings,
                              'client_port'))
        self.agentPort = int(cp.get(self.section_settings, 'agent_port'
                             ))
        self.appletPort = int(cp.get(self.section_settings,
                              'applet_port'))

        self.key = cp.get(self.section_settings, 'key')
        self.cert = cp.get(self.section_settings, 'cert')
        self.ca = cp.get(self.section_settings, 'ca')

        if self.key and self.cert and self.ca:
            self.tls_conf = {'key': self.key, 'cert': self.cert,
                             'ca': self.ca}
        else:
            self.tls_conf = None

        print('%d %d %d %s %s %s' % (
            self.clientPort,
            self.agentPort,
            self.appletPort,
            self.key,
            self.cert,
            self.ca,
            ))

        # Get it on!

        self.agentServer = None
        self.clientServer = None
        self.appletServer = None

        # Listen for clients, via ProxyClientHandler

        ProxyClientHandler.use_tls = self.tls_conf != None

        self.clientServer = MiGTCPServer(('', self.clientPort),
                ProxyClientHandler)

        broker_thread = \
            threading.Thread(target=self.clientServer.serve_forever)
        broker_thread.setDaemon(True)
        broker_thread.start()

        # Listen for servers, via the ProxyAgentHandler

        self.agentServer = MiGTCPServer(('', self.agentPort),
                ProxyAgentHandler, self.tls_conf)

        mip_thread = \
            threading.Thread(target=self.agentServer.serve_forever)
        mip_thread.setDaemon(True)
        mip_thread.start()

        # The appletServer below is a quick and dirty http server for serving
        # up applets
        #
        # TODO: Find a better way to manage java applets,
        #       they must be served from the same server as they need to
        #       connect to in most cases this will be the proxy. So having an
        #       integrated applet server actually makes sense.

        os.chdir('applets')
        self.appletServer = MiGTCPServer(('', self.appletPort),
                SimpleHTTPRequestHandler)

        client_thread = \
            threading.Thread(target=self.appletServer.serve_forever)
        client_thread.setDaemon(True)
        client_thread.start()

        # That's it, let the threads do their job

        while True:
            time.sleep(1000)


if __name__ == '__main__':
    try:
        Proxy().main()
    except:
        logging.exception('Unexpected error: %s' % sys.exc_info()[2])
