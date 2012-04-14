#!/usr/bin/env python
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
