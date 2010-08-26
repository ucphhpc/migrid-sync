#!/usr/bin/python
"""
    Test script to test the branching mechanism.
"""
import xmlrpclib

proxy = xmlrpclib.ServerProxy("http://n0:8000/")

print proxy.branch("/somedir", "/tmp/mybranch", "%s:%d/%s" % ("localhost", 8000, "mybranch"))

