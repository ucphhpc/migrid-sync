#!/bin/bash
#
#	/etc/rc.d/init.d/MiG
#
#	MiG is a Grid middleware with minimal installation requirements
#
#	Recognized arguments:
#	    start   - start MiG system components
#	    stop    - terminate MiG system components
#	    restart - terminate and start MiG system 
#	    status  - report MiG system component's status
#
#	Customization of the MiG installation should be specified by
#	variables in /etc/sysconfig/MiG
#
# Made from the template /usr/share/doc/initscripts-8.45.25/sysinitvfiles
# from our CEntOS-5.2 installation on grid.dk
#
# <tags ...>
#
# chkconfig: - 90 10
# description: MiG is a Grid solution with minimal installation requirements
# processname: grid_script.py(default)
# processname: grid_monitor.py(default)
# config: /etc/sysconfig/MiG
# 

# Source function library.
. /etc/init.d/functions

# <define any local shell functions used by the code that follows>

# first, pull in custom configuration (if it exists):
if [ -f /etc/sysconfig/MiG ]; then
    . /etc/sysconfig/MiG
fi
# define default locations and user for MiG if not set:
if [ -z $MIG_USER ]; then 
    MIG_USER=mig
fi
if [ -z $MIG_PATH ]; then 
    MIG_PATH=/home/${MIG_USER}
fi
# more configurable paths:
if [ -z $MIG_STATE ]; then 
    MIG_STATE=${MIG_PATH}/state
fi
if [ -z $MIG_CODE ]; then 
    MIG_CODE=${MIG_PATH}/mig
fi
if [ -n $MIG_CONF ]; then 
    CUSTOMCONF="MIG_CONF=$MIG_CONF "
fi
# you probably do not want to modify these...
MIG_SERVER=${MIG_CODE}/server/grid_script.py
MIG_MONITOR=${MIG_CODE}/server/grid_monitor.py
DELAY=5

start() {
	echo -n "Starting MiG server daemon: "
	daemon --user ${MIG_USER} \
	           "$CUSTOMCONF ${MIG_SERVER} 2>&1 > ${MIG_STATE}/server.out &"
	RET=$?
	if [ $RET -ne 0 ]; then 
	    failure
	    exit $RET
	else 
	    # some input for the mig server...
	    echo "" >> ${MIG_CODE}/server/server.stdin
	    success
	fi
	echo
	echo -n "Starting MiG monitor daemon:"
	daemon --user ${MIG_USER} \
	           "$CUSTOMCONF ${MIG_MONITOR} 2>&1 > ${MIG_STATE}/monitor.out &"
	RET2=$?
	[ $RET2 ] && success
	echo
	# if monitor does not work, too bad... continue
	[ $RET2 ] || echo "Warning: Monitor not started."
	touch /var/lock/subsys/MiG
	return $RET
}	

stop() {
	echo -n "Shutting down MiG monitor: "
	killproc ${MIG_MONITOR}
	echo
	pid=`pidofproc ${MIG_SERVER}`
	if [ -z "$pid" ]; then
	    echo -n "MiG server is not running..."
	    failure
	    echo
	else
            # try a shutdown before killing it
	    echo -n "SHUTDOWN MiG server (pid $pid)"
	    echo SHUTDOWN >> $MIG_PATH/mig/server/server.stdin
	    sleep ${DELAY}
	    checkpid $pid
	    KILLED=$?
	    if [ $KILLED ]; then 
		success;
	    else 
		failure
		echo
		echo -n "Killing MiG server"
		killproc ${MIG_SERVER} -KILL;
	    fi
	    echo
	fi
	
	rm -f /var/lock/subsys/MiG
	return $RET
}

case "$1" in
    start)
	start
	;;
    stop)
	stop
	;;
    status)
	status ${MIG_SERVER}
	status ${MIG_MONITOR}
	;;
    restart)
    	stop
	start
	;;
#    reload)
#	<cause the service configuration to be reread, either with
#	kill -HUP or by restarting the daemons, in a manner similar
#	to restart above>
#	;;
#    condrestart)
#    	<Restarts the servce if it is already running. For example:>
#	[ -f /var/lock/subsys/<service> ] && restart || :
#    probe)
#	<optional.  If it exists, then it should determine whether
#	or not the service needs to be restarted or reloaded (or
#	whatever) in order to activate any changes in the configuration
#	scripts.  It should print out a list of commands to give to
#	$0; see the description under the probe tag below.>
#	;;
    *)
#	echo "Usage: <servicename> {start|stop|status|reload|restart[|probe]"
	echo "Usage: <servicename> {start|stop|status|restart]"
	exit 1
	;;
esac
exit $?

Notes: 

- The restart and reload functions may be (and commonly are)
  combined into one test, vis:
    restart|reload)
- You are not prohibited from adding other commands; list all commands
  which you intend to be used interactively to the usage message.
- Notice the change in that stop() and start() are now shell functions.
  This means that restart can be implemented as
     stop
     start
  instead of
     $0 stop
     $0 start
  This saves a few shell invocations.

Functions in /etc/init.d/functions
=======================================

daemon  [ --check <name> ] [ --user <username>] 
	[+/-nicelevel] program [arguments] [&]

	Starts a daemon, if it is not already running.  Does
	other useful things like keeping the daemon from dumping
	core if it terminates unexpectedly.
	
	--check <name>:
	   Check that <name> is running, as opposed to simply the
	   first argument passed to daemon().
	--user <username>:
	   Run command as user <username>

killproc program [signal]

	Sends a signal to the program; by default it sends a SIGTERM,
	and if the process doesn't die, it sends a SIGKILL a few
	seconds later.

	It also tries to remove the pidfile, if it finds one.

pidofproc program

	Tries to find the pid of a program; checking likely pidfiles,
	and using the pidof program.  Used mainly from within other
	functions in this file, but also available to scripts.

status program

	Prints status information.  Assumes that the program name is
	the same as the servicename.


Tags
====

# chkconfig: <startlevellist> <startpriority> <endpriority>

	Required.  <startlevellist> is a list of levels in which
	the service should be started by default.  <startpriority>
	and <endpriority> are priority numbers.  For example:
	# chkconfig: 2345 20 80
	Read 'man chkconfig' for more information.

	Unless there is a VERY GOOD, EXPLICIT reason to the
	contrary, the <endpriority> should be equal to
	100 - <startpriority>
	
# description: <multi-line description of service>

	Required.  Several lines of description, continued with '\'
	characters.  The initial comment and following whitespace
	on the following lines is ignored.

# description[ln]: <multi-line description of service in the language \
#                  ln, whatever that is>

	Optional.  Should be the description translated into the
	specified language.

# processname:

	Optional, multiple entries allowed.  For each process name
	started by the script, there should be a processname entry.
	For example, the samba service starts two daemons:
	# processname: smdb
	# processname: nmdb

# config:

	Optional, multiple entries allowed.  For each static config
	file used by the daemon, use a single entry.  For example:
	# config: /etc/httpd/conf/httpd.conf
	# config: /etc/httpd/conf/srm.conf

	Optionally, if the server will automatically reload the config
	file if it is changed, you can append the word "autoreload" to
	the line:
	# config: /etc/foobar.conf autoreload

# pidfile:

	Optional, multiple entries allowed.  Use just like the config
	entry, except that it points at pidfiles.  It is assumed that
	the pidfiles are only updated at process creation time, and
	not later.  The first line of this file should be the ASCII
	representation of the PID; a terminating newline is optional.
	Any lines other than the first line are not examined.

# probe: true

	Optional, used IN PLACE of processname, config, and pidfile.
	If it exists, then a proper reload-if-necessary cycle may be
	acheived by running these commands:

	command=$(/etc/rc.d/init.d/SCRIPT probe)
	[ -n "$command" ] && /etc/rc.d/init.d/SCRIPT $command

	where SCRIPT is the name of the service's sysv init script.

	Scripts that need to do complex processing could, as an
	example, return "run /var/tmp/<servicename.probe.$$"
	and implement a "run" command which would execute the
	named script and then remove it.

	Note that the probe command should simply "exit 0" if nothing
	needs to be done to bring the service into sync with its
	configuration files.

Copyright (c) 2000 Red Hat Software, Inc.
