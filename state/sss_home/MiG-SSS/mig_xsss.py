#!/usr/bin/env python
import os
import time

MiG_DIR = "~/MiG-SSS"
G_XSCREENSAVER_COMMAND = "/usr/X11R6/bin/xscreensaver-command -watch"
G_GPIDFILE = "/tmp/mig_xsss_job.gpid"

# Returns Group ID of running job
def getRunningGPID( param_sGPIDFile ):
    iGPID = -1
    if ( os.path.isfile( param_sGPIDFile ) ):
	input = open( param_sGPIDFile, "r" )
	iGPID = int(input.readline())
	input.close()
    return iGPID

# Writes Group ID of running job to param_sGPIDFile
def writeRunningGPID( param_iGPID, param_sGPIDFile ):
    output = open( param_sGPIDFile, "w" )
    output.write( str(param_iGPID) + "\n" )
    output.close()
	
def startJob(param_sGPIDFile):
    iPID = os.fork()
    if ( iPID == 0 ):
	os.setpgrp()
    else:
	# Write GPID to file
	writeRunningGPID( os.getpgrp(), param_sGPIDFile )
        cmd = "qemu -hda "+MiG_DIR+"/hda.img -cdrom "+MiG_DIR+"/MiG.iso -boot d -kernel-kqemu -nographic"
        fd = os.popen(cmd)
        fd.close()
	
	# We never end here as it is right now
	# Job finished, remove param_sGPIDFile.
	os.unlink( param_sGPIDFile )
	os._exit(0)
	
def killJob( param_sGPIDFile ):
    iGPID = getRunningGPID( param_sGPIDFile );
    if (iGPID != -1) :
	try:
	    # Kill all processes with group id GPID
	    os.kill( 0-iGPID, 9 )
        except OSError, e:
	    # Process doesnt exist, ignore
	    print ""
		
	# Job killed, remove param_sGPIDFile.
	os.unlink( param_sGPIDFile )


def SSS():
    while(1):
	str = ""
	bScreenSaverActive = 0
	fd = os.popen( G_XSCREENSAVER_COMMAND )
	str = fd.readline()
	while ( len(str) != 0 ):
	    if ( (str[0:5] == "BLANK" or str[0:4] == "LOCK") and bScreenSaverActive == 0 ):
		bScreenSaverActive = 1
		startJob(G_GPIDFILE)
		fd = os.popen(G_XSCREENSAVER_COMMAND)
	    elif  ( str[0:7] == "UNBLANK" and bScreenSaverActive == 1 ):
		bScreenSaverActive = 0
		killJob(G_GPIDFILE)
	    str = fd.readline()
	fd.close()
    
def main():
    iPID = os.fork()
    if (iPID == 0):
	os.setpgrp()
	SSS()

if __name__ == '__main__' : main()
