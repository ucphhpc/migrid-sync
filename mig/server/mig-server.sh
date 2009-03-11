#!/bin/sh
#
# --- BEGIN_HEADER ---
#
# mig-server - MiG server init script
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

