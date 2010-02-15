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
EXE_CLEAN_CMD="./clean_and_start_resource.py"
EXE_CLEAN_ALL_CMD="./clean_and_start_resources.sh"
EXE_CHECK_DICT = {}
EXE_CHECKS_BEFORE_RESTART = 10

def usage():
    print "Usage: keepalive.py resource_description_file"
    print "Where OPTIONS include:"
    print "-v               verbose mode"
    print "-h               display this help"
    print ""
    print "Example: keepalive.py resources/lucia.imada.sdu.dk.0"
        
def restart_exe(resource_name):
    fh = open(resource_name, "r")
    readline = fh.readline()
    while readline:
        cmd = "%s %s %s 2>/dev/null" % (EXE_RESTART_CMD, resource_name, readline[:-1])
        fd = os.popen(cmd)
        status = int(fd.readline()[:-1])
        print "%s: %s" % (cmd, str(status))
        fd.close()
        readline = fh.readline()
        
    fh.close()
    
def check_exe(resource_description_file):
     # Only last part of the resource_desription_file is the FE resource_name
     resource_name = (resource_description_file.split(os.sep))[-1]
     
     fh = open(resource_description_file, "r")
     readline = fh.readline()
     while readline:
        exe_name = readline[:-1]
        cmd = "%s %s %s 2>/dev/null" % (EXE_STATUS_CMD, resource_name, exe_name)
        fd = os.popen(cmd)

        exe_running = False
        readline2 = fd.readline()
        while readline2 and not exe_running:
            if readline2.find("returned 0") > -1:
                exe_running = True
            readline2 = fd.readline()
        fd.close()

        if not exe_running:
            # Check how long exe has been down, to avoid restaring healty exe
            # waiting for MiG server to restart it.
            if not EXE_CHECK_DICT.has_key(exe_name):
                EXE_CHECK_DICT[exe_name] = 0
            elif EXE_CHECK_DICT[exe_name] < EXE_CHECKS_BEFORE_RESTART:
                EXE_CHECK_DICT[exe_name] += 1
                print "Adding to '%s' EXE_CHECK_DICT: %s" % (exe_name, EXE_CHECK_DICT[exe_name])
            else:
                # Reset check counter
                EXE_CHECK_DICT[exe_name] = 0
                
                # Clean exe
                cmd = "%s %s %s 2>/dev/null" % (EXE_CLEAN_CMD, resource_name, exe_name)
                print cmd
                fd2 = os.popen(cmd)
                readline3 = fd2.readline()
                while readline3:
                    print readline3[:-1]
                    readline3 = fd2.readline()
                fd2.close()
                
        # Reset check counter, as resource is running
        if exe_running:
            EXE_CHECK_DICT[exe_name] = 0
            print "%s: '%s' is Running" % (time.strftime("%c"), exe_name)           
        else:
            print "%s: '%s' Checks/Restart: %s/%s " % (time.strftime("%c"), exe_name, EXE_CHECK_DICT[exe_name], EXE_CHECKS_BEFORE_RESTART)

        readline = fh.readline()
        #status = int(fd.readline()[:-1])
        #print "%s: %s 2>/dev/null" % (cmd, str(status))
           
        #if status == 0:
        #    fd.readline()
        #    fd.readline()
        #    readline2 = fd.readline()
        #    print readline2
        #    if readline2.find("returned 0") == -1:
        #        cmd = "%s %s %s 2>/dev/null" % (EXE_START_CMD, resource_name, readline[:-1])
        #        fd2 = os.popen(cmd)
        #        status = int(fd2.readline()[:-1])
        #        fd2.close()
        #        print "%s: %s" % (cmd, str(status))
                
     fh.close()
                
def check_fe(resource_description_file):
    fe_running = False
    if os.path.exists(resource_description_file):
        # Only last part of the resource_desription_file is the FE resource_name
        resource_name = (resource_description_file.split(os.sep))[-1]
        cmd = "%s %s 2>/dev/null" % (FE_STATUS_CMD, resource_name)
        fd = os.popen(cmd)
        readline = fd.readline()
        while readline and not fe_running:
            if readline.find("returned 0") > -1:
                fe_running = True
            readline = fd.readline()
        fd.close()
        print "%s: Frontend running: %s" % (time.strftime("%c"), str(fe_running))
        
        if not fe_running:
            # Start FE
            cmd = "%s %s 2>/dev/null" % (FE_START_CMD, resource_name)
            fd = os.popen(cmd)
            status = fd.readline()
            fd.close()
            print "%s: '%s'" % (cmd, str(status))
    else:
        print "No such resource: %s " % resource_name
    
# === Main ===
verbose = False

arg_zero = sys.argv[0]
args = sys.argv[1:]
opt_args = "hv"

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
min_count = 1
                                                                                                
if arg_count < min_count:
    print "Too few arguments: got %d, expected %d!" % (arg_count, min_count)
    usage()
    sys.exit(1)


sleep_time=60
while True:
    check_fe(sys.argv[1])
    check_exe(sys.argv[1])
    print "SLEEPING: %s" % (str(sleep_time))
    time.sleep(sleep_time)
