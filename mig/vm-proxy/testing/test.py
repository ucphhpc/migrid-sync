#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
#
# test - [optionally add short module description on this line]
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

# This Python file uses the following encoding: utf-8
import random
import unittest
import proxyd
import logging
from proxy import mipclient
import threading
import time

class TestProxyFlow(unittest.TestCase):

    def setUp(self):    
      try:        
        proxy_thread = threading.Thread(target=proxyd.Proxy().run)
        proxy_thread.setDaemon(False)
        proxy_thread.start()
        time.sleep(2)
      except:
        logging.exception('LORAT')

    def testProxyConnect(self):
      
      client_thread = threading.Thread(target=mipclient.clientConnect)
      client_thread.setDaemon(False)
      client_thread.start()

if __name__ == '__main__':
    unittest.main()
