#!/bin/sh
#
#----------------------------------------------------------------
# Project         : Minimum Intrusion Grid (MiG)
#----------------------------------------------------------------
# chkconfig: 345 80 10
# description: This startup script launches a MiG server.
#----------------------------------------------------------------

# paths
BASE=`dirname $0`
# Where to store the pid
PID_FILE="$BASE/server.pid"
SERVER="$BASE/server.py"

case $1 in
    start)
	echo -n "Starting MiG Server... "
	if [ -f "$PID_FILE" ]; then
	    echo "failed! (pid file exists)."
	else
	    echo
	    env python $SERVER &
	fi
	;;

    stop)
	echo -n "Stopping MiG Server... "
	
	if [ -r "$PID_FILE" ]; then
	    kill `cat $PID_FILE` > /dev/null 2>&1
	    ret=$?
	    if [ $ret = 0 ]; then
		echo "done!"
		rm -f $PID_FILE
	    else
		echo "failed!"
	    fi
	else
	    echo "failed! (pid file not found/readable)."
	fi
	echo
	;;

    restart)
	$0 stop
	sleep 2
	$0 start
	ret=$?
	;;
    force-restart)
	$0 stop
	sleep 2
	rm -f $PID_FILE
	$0 start
	ret=$?
	;;
    *)
	echo "Usage: `basename $0` {start|stop|restart}"
	exit 0
	;;
esac

exit $ret

