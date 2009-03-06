#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobexecuter - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

import sys
import os
import time
import math
import fcntl

# MiG XSSS imports
import jobmanager
import logger

# Omregner fra minutter til MiG cputid
def getMigCpuTimeFactor():
    return 60

def getStatusFileName( param_sPGIDFILE, pid ):
    return param_sPGIDFILE + "." + str(pid) + ".status"

def writeScreensaverStatus( status, param_sPGIDFILE, pid ): 
    fh = open( getStatusFileName( param_sPGIDFILE, pid), "w" )
    fcntl.flock(fh.fileno(),fcntl.LOCK_EX)
    fh.write( status + "\n")
    fcntl.flock(fh.fileno(),fcntl.LOCK_UN)
    fh.close()
   
def getScreensaverStatus( param_sPGIDFILE, pid ):
    status_filename = getStatusFileName( param_sPGIDFILE, pid )
    
    fh = open( status_filename, "r" )
    fcntl.flock(fh.fileno(),fcntl.LOCK_EX)
    status = fh.readline().strip().strip('\n')
    fcntl.flock(fh.fileno(),fcntl.LOCK_UN)
    fh.close()
        
    logger.write( "PID: " + str(os.getpid()) + " status:" + status )
    
    if "deactivated" <> status:
	screensaver_status = 0
    else:
	screensaver_status = 1
    
    return screensaver_status

def startJob( param_tActivatedTime, param_sPGIDFILE ):
    iPID = os.fork()
	
    if ( iPID == 0 ):
	# child process - become leader of new process group that won't be
	# killed by killall -g
	os.setpgrp()
	return iPID
    else:
	#print "pid: ", pid
	#print "pgrp:", os.getpgrp()
   
	writeScreensaverStatus( "activated", param_sPGIDFILE, os.getpid() ) 
	logger.write( "PID: " + str(os.getpid()) + " spawned.")
	
	# If file exists, we are waiting for the killJob to terminate
	# as there can be only one active screensaver at a time
	while os.path.exists( param_sPGIDFILE ):
	    logger.write( "PID: '" + str(param_sPGIDFILE) + "' exists, which means there is an active MiG SSS job.")
	    time.sleep(10)
	
	fh = open( param_sPGIDFILE, "w" )
	fcntl.flock(fh.fileno(),fcntl.LOCK_EX)
	fh.write( str(os.getpid()) + "\n" )
	fcntl.flock(fh.fileno(),fcntl.LOCK_UN)
	fh.close()
	
	tActivatedTime = param_tActivatedTime
	iExpectedActiveMinutes = jobmanager.getExpectedActiveMinutes( tActivatedTime )	

	logger.write( "PID: " + str(os.getpid()) + " iExpectedActiveMinutes: " + str(iExpectedActiveMinutes) )
	
	while (1):
	    iElapsedTime = 0
	    # Keep requesting MiG jobs as long as we are expected to be on screensaver	    	    
	    while ( iElapsedTime < iExpectedActiveMinutes ):
		# We keep punking MiG server for a job, until we get one OR the expected time on screensaver has elapsed.
		status = 1
		while 0 <> status and iElapsedTime < iExpectedActiveMinutes:
		    # If the screensaver is deactivatet, the MiG job has been killed, 
		    # and therefore this procces has no further purpose in life.
		    screensaver_status = getScreensaverStatus( param_sPGIDFILE, os.getpid() )
		    if 0 <> screensaver_status:
			logger.write( "PID: " + str(os.getpid()) + " Screensaver deactivatet, terminating this process" )
			status_file =  getStatusFileName(param_sPGIDFILE, os.getpid())
			if os.path.exists( status_file ):
			    os.remove( status_file )
			return iPID
			    
		    iMaxExecutionTime =  (iExpectedActiveMinutes - iElapsedTime) * getMigCpuTimeFactor()
		    logger.write( "PID: " + str(os.getpid()) + " requesting MiG job, iMaxExecutionTime: " + str(iMaxExecutionTime) )

		    fd = os.popen( "./mig_xsss_start_resource_exe.sh " + str(int(math.floor(iMaxExecutionTime))))
		    exit_code = fd.readline().strip().strip('\n')
		    if exit_code.isdigit():
			status = int(exit_code)
			logger.write("PID: " + str(os.getpid()) + " './mig_xsss_start_resource_exe.sh' executed OK")
		    else:
			status = 1
			# Log output from execution
			log_str = exit_code + "\n"\
			        + logger.get_output(fd)
				
			logger.write("PID: " + str(os.getpid()) + " './mig_xsss_start_resource_exe.sh' execution FAILED:\n" + log_str)
		    fd.close()	
		    
		    time.sleep(60)

		    tCurrentTime = jobmanager.getTimeTuppel()
		    iElapsedTime = jobmanager.getTimeDiff( tActivatedTime, tCurrentTime )
		
		# If we got a MiG job, get the pgid of it.
		if 0 == status:
		    # Get pgid of the MiG job, this is done to get the PGID once and for all 
		    # instead of retrieveing it from the MiG server everytime it is needed.
		    # We Keep punking MiG server until we the pgid 
		    # or the expected time on screensaver has elapsed.
		    pgid = -1
		    while -1 == pgid and iElapsedTime < iExpectedActiveMinutes:
			# If the screensaver is deactivatet, the MiG job has been killed, 
			# and therefore this procces has no further purpose in life.
			screensaver_status = getScreensaverStatus( param_sPGIDFILE, os.getpid() )
			if 0 <> screensaver_status:
			    logger.write( "PID: " + str(os.getpid()) + " Screensaver deactivatet, terminating this process" )
			    status_file =  getStatusFileName(param_sPGIDFILE, os.getpid())
			    if os.path.exists( status_file ):
				os.remove( status_file )
			    return iPID

			fd = os.popen( "./mig_xsss_get_resource_pgid.sh" )
			exit_code = fd.readline().strip().strip('\n')
			if exit_code.isdigit():
			    status = int( exit_code )
			else:
			    status = 1

			readline = fd.readline().strip().strip('\n')

			# Log execution status
			if 0 <> status or (not readline.isdigit() and "starting" <> readline):
			    log_str = exit_code + "\n"\
				    + readline + "\n"\
				    + logger.get_output(fd)
				      
			    logger.write("PID: " + str(os.getpid()) + " ERROR getting pgid:\n" + log_str)
			else:
			    logger.write( "PID: " + str(os.getpid()) + " getpgid status: " + str(status) + " pgid: " + readline )
			fd.close()	
			
			if 0 == status:
			    if readline.isdigit():
				pgid = int( readline )
			    elif "starting" <> readline:
				break
		    
			time.sleep(60)

			tCurrentTime = jobmanager.getTimeTuppel()
			iElapsedTime = jobmanager.getTimeDiff( tActivatedTime, tCurrentTime )
			
		    # If we got the pgid, wee keep looping until this job is done,
		    # or the screensaver has been deactivated
		    if -1 <> pgid:
			while 1:
			    # If the screensaver is deactivatet, the MiG job has been killed, 
			    # and therefore this procces has no further purpose in life.
			    screensaver_status = getScreensaverStatus( param_sPGIDFILE, os.getpid() )
			    if 0 <> screensaver_status:
				logger.write( "PID: " + str(os.getpid()) + " Screensaver deactivatet, terminating this process" )
				status_file =  getStatusFileName(param_sPGIDFILE, os.getpid())
				if os.path.exists( status_file ):
				    os.remove( status_file )
				return iPID
		    
			    fd = os.popen("./mig_xsss_get_pgid_count.sh " + str(pgid) )
			    num_of_migjob_process = int( fd.readline().strip().strip('\n') )
			    fd.close()
			
			    logger.write( "PID: " + str(os.getpid()) + " Found: " + str(num_of_migjob_process) + " running MiG processes with PGID: " + str(pgid) )
			    # If the MiG job has terminated, request a new one.
			    if ( 0 == num_of_migjob_process ):
				logger.write( "PID: " + str(os.getpid()) + " Job finished, request a new one." )
				break;
		    	
			    time.sleep(60)
			    logger.write( "PID: " + str(os.getpid()) + " waking up." )
		    

		tCurrentTime = jobmanager.getTimeTuppel()
		iElapsedTime = jobmanager.getTimeDiff( tActivatedTime, tCurrentTime )
		logger.write( "PID: " + str(os.getpid()) + " iElapsedTime: " + str(iElapsedTime) )
		
	    # Expected Time elapsed, sleep expected minutes, 
	    # and then start over again.
	    logger.write( "PID: " + str(os.getpid()) + " Sleeping: " + str(iExpectedActiveMinutes * 60) + " secs before requesting new job." )
	    time.sleep( iExpectedActiveMinutes * 60 )
	    
	    # We have been active for iExpectedActiveMinutes*2, 
	    # set iExpectedActiveMinutes to that amount, 
	    # Thereby we double iExpectedActiveMinutes for each loop
	    iExpectedActiveMinutes = iExpectedActiveMinutes*2
	    logger.write( "PID: " + str(os.getpid()) + " New ExpectedActiveMinutes: " + str(iExpectedActiveMinutes) )
	    
	    # Get the time that we are reactivated
	    tActivatedTime = jobmanager.getTimeTuppel()
	
	# We never end here as it is right now
	# Job finished, remove param_sPGIDFILE.
	if os.path.exists( param_sPGIDFILE ):
	    os.remove( param_sPGIDFILE )
	return iPID
	
def killJob( param_sPGIDFILE ):

    # If file does not exists, we are waiting for the startJob 
    # to create the file, as the screensaver must be active,
    # before it can be deactivatet.
    while not os.path.exists( param_sPGIDFILE ):
	logger.write ( "Waiting for file: '" +  param_sPGIDFILE + "' to be created" )
	time.sleep(10)
 
    fh = open( param_sPGIDFILE, "r" )
    pid = int( fh.readline().strip().strip('\n') )
    fh.close()
    
    writeScreensaverStatus( "deactivated", param_sPGIDFILE, pid )

    if os.path.exists( param_sPGIDFILE ):
	os.remove( param_sPGIDFILE )

    fd = os.popen( "./mig_xsss_stop_resource_exe.sh ")
    exit_code = fd.readline().strip().strip('\n')
    fd.close()		
    
    logger.write( "PID: " + str(pid) + " deactivated, resource stop status: " + exit_code )
    
# Main only for test
def main():
    sPIDFile = "/tmp/_MiG_SSS_GPID"
    
    killJob( sPIDFile )
    time.sleep(5)
    
    iPID = os.fork()
    if (iPID == 0):
	while (1):
	    startJob( "./xeyes.sh", sPIDFile )
	    time.sleep(5)
	    killJob( sPIDFile )
	    time.sleep(5)
	    
 
	
	
if __name__ == '__main__' : main()
