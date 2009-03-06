#!/bin/bash
# Setting MIG_HOST, some gives full hostname 
# others gives only machinename

SHELL="/bin/bash"
DEFAULT_PIPE="2>/dev/null 1>/dev/null"

if [ `hostname | grep -c "\."` -eq 0 ]; then
   MIG_HOST="`hostname`"
else
   MIG_HOST="`hostname | awk -F '.' '{print $1}'`"
fi

MIG_DOMAIN="`domainname`"

MIG_FQDN="$MIG_HOST.$MIG_DOMAIN"
MIG_HOST_IDENTIFIER="0"

MIG_FRONTEND_PATH="/usr/local/mig_xsss"
MIG_FRONTEND_SCRIPT_STOP="stop_resource_frontend.sh $MIG_FQDN.$MIG_HOST_IDENTIFIER"
MIG_FRONTEND_SCRIPT_START="start_resource_frontend.sh $MIG_FQDN.$MIG_HOST_IDENTIFIER"
MIG_EXE_SCRIPT_STOP="stop_resource_exe.sh $MIG_FQDN.$MIG_HOST_IDENTIFIER $MIG_HOST"

PYTHON_INTERPRETER="/usr/bin/python"
MIG_XSSS_PATH="/usr/local/mig_xsss"
MIG_XSSS="mig_xsss.py"
MIG_XSSS_COMMAND="$PYTHON_INTERPRETER ./$MIG_XSSS"

MIG_PID_FILE="/tmp/mig_xsss_job.gpid"

XSCREENSAVER_COMMAND="/usr/X11R6/bin/xscreensaver-command -watch"

# Exports is nessesay for start at bootup.
export DISPLAY=":0.0"

# XAUTHORITY only nessesary for usage with gdm.
export XAUTHORITY="/var/lib/gdm/:0.Xauth"
# For debug
#export XAUTHORITY="/home/rehr/.Xauthority"

# If this is not an active mig_xsss resource, quit.
MIG_ACTIVE_RESOURCES="/usr/local/mig_xsss/data/activeresources.dat"
activeResource="`cat $MIG_ACTIVE_RESOURCES | grep -wc "$MIG_FQDN"`"
if [ $activeResource -eq 0 ]; then
   echo ""
   echo "'$MIG_FQDN' is _NOT_ an active mig_xsss resource."
   echo "'$0 $1' _NOT_ executet!"
   echo ""
   exit 0
fi

case "$1" in
  start)
        echo "Starting mig_xsss at '$MIG_HOST.$MIG_DOMAIN'"
  
        # Start MiG frontend
	cd $MIG_FRONTEND_PATH
        $SHELL -c "./$MIG_FRONTEND_SCRIPT_STOP $DEFAULT_PIPE"
	frontendStartet="`./$MIG_FRONTEND_SCRIPT_START 2>/dev/null | grep -wc 'frontend_script.sh started'`"
	
	if [ $frontendStartet -eq 1 ]; then
	   # Start MiG XSSS
	   cd $MIG_XSSS_PATH 
	   $SHELL -c "$MIG_XSSS_COMMAND $DEFAULT_PIPE &"
	fi
	;;
  stop)
        echo  "Stopping mig_xsss at '$MIG_HOST.$MIG_DOMAIN'"
	
        # Kill mig_xsss
	$SHELL -c "kill -9 `ps aux | grep "$MIG_XSSS_COMMAND" | awk '{print $2}'` $DEFAULT_PIPE"
	$SHELL -c "kill -9 `ps aux | grep "$XSCREENSAVER_COMMAND" | awk '{print $2}'` $DEFAULT_PIPE"
	
	# Kill running mig_job
	cd $MIG_XSSS_PATH
	$SHELL -c "./$MIG_EXE_SCRIPT_STOP $DEFAULT_PIPE"
	
	# Remove MiG pid_files
	$SHELL -c "rm -f ${MIG_PID_FILE}* $DEFAULT_PIPE"
		
	# Kill MiG frontend script
	cd $MIG_FRONTEND_PATH
	$SHELL -c "./$MIG_FRONTEND_SCRIPT_STOP $DEFAULT_PIPE"
	;;
  restart)
  	$0 stop
	sleep 5
	$0 start
	;;
  *)
	echo "Usage: $0 {start|stop|restart}"
	exit 1
esac

exit 0

