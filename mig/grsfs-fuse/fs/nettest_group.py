#!/usr/bin/env python
# encoding: utf-8
"""
nettest_group.py

Starts the required number of processes to have a full group and then leaves them alone.

Created by Jan Wiberg on 2010-03-29.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""

import os, subprocess, time

master = subprocess.Popen("python nettest_server.py", shell=True)
time.sleep(1)
replica1 = subprocess.Popen("python nettest_replica.py 1", shell=True)
time.sleep(0.5)
replica2 = subprocess.Popen("python nettest_replica.py 2", shell=True)

print "Should be good now"
time.sleep(20)