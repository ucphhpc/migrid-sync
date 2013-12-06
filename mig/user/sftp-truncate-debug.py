#!/usr/bin/python
#
# Debug issue with truncate operation on sshfs mounted MiG home

import os
import sys

local_path = sys.argv[1]
remote_path = sys.argv[2]

try:
    local_fd = open(local_path, "w+")
    local_fd.truncate(0)
    local_fd.close()
    print "local truncate on %s succeeded" % local_path
    
except Exception, exc:
    print "local truncate on %s failed: %s" % (local_path, exc) 
try:
    remote_fd = open(remote_path, "w+")
    remote_fd.truncate(0)
    remote_fd.close()
    print "remote truncate on %s succeeded" % remote_path
except Exception, exc:
    print "remote truncate on %s failed: %s" % (remote_path, exc) 
      
