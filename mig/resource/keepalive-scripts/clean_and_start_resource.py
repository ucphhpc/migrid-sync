#!/usr/bin/python

import sys
import os
import time
import getopt

MIG_HOME="./MiG/"
FE_STATUS_CMD = MIG_HOME + "migstatusfe.sh"
FE_STOP_CMD = MIG_HOME + "migstopfe.sh"
FE_START_CMD = MIG_HOME + "migstartfe.sh"

EXE_STATUS_CMD = MIG_HOME + "migstatusexe.sh"
EXE_START_CMD = MIG_HOME + "migstartexe.sh"
EXE_RESTART_CMD = MIG_HOME + "migrestartexe.sh"
EXE_CLEAN_CMD = MIG_HOME + "migcleanexe.sh"

def usage():
    print "Usage: restart_resource.py resource_fe resource_exe"
    print "Where OPTIONS include:"
    print "-v               verbose mode"
    print "-h               display this help"
    print ""
    print "Example: restart_resource.py lucia.imada.sdu.dk.0 lucia"
	
def clean_and_restartexe(resource_fe, resource_exe):
    cmd = "%s %s %s 2>/dev/null" % (EXE_CLEAN_CMD, resource_fe, resource_exe)
    print cmd
    fd = os.popen(cmd)
    readline = fd.readline()
    while readline:
	print readline[:-1]
	readline = fd.readline()
    fd.close()

    cmd = "%s %s %s 2>/dev/null" % (EXE_START_CMD, resource_fe, resource_exe)
    print cmd
    fd = os.popen(cmd)
    readline = fd.readline()
    while readline:
	print readline[:-1]
	readline = fd.readline()
    fd.close()

# === Main ===
verbose = False

arg_zero = sys.argv[0]
args = sys.argv[1:]
opt_args = "h"

try:
    opts, args = getopt.getopt(args, opt_args)
except getopt.GetoptError, e:
    print "Error: ", e.msg
    usage()
    sys.exit(1)
    
for (opt, val) in opts:
    if opt == "-v":
	verbose = True
    elif opt == "-h":
	usage()
	sys.exit(0)
    else:
	print "Error: %s not supported!" % (opt)
	
# Drop options while preserving original sys.argv[0]
sys.argv = [arg_zero] + args

arg_count = len(sys.argv) - 1
min_count = 2
												
if arg_count < min_count:
    print "Too few arguments: got %d, expected %d!" % (arg_count, min_count)
    usage()
    sys.exit(1)
    
resource_fe = sys.argv[1]
resource_exe = sys.argv[2]
clean_and_restartexe(resource_fe, resource_exe)




