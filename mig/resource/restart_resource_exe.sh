#!/bin/sh
function restart_resource_exe(){
	unique_resource_name="$1"
	exe_name="$2"
	if [ $# -eq 3 ]; then
	   cputime="&cputime=$3"
	fi
	
	# Uncomment to debug
	# DEBUG_PREFIX="echo "
	
	cmd="${DEBUG_PREFIX}curl"
  	# Specify password without making it visible in process
    	# list (e.g. 'ps awwx')
      	
	$cmd \
	--insecure \
        --cert $certfile \
        --key $key \
        --pass `awk '/pass/ {print $2}' $MiGuserconf` \
        --url "$migserver/cgi-bin/restartexe.py?unique_resource_name=$unique_resource_name&exe_name=$exe_name$cputime"
}
      
function usage(){
	echo "Usage..."
	echo "restart_resource_exe.sh unique_resource_name exe_name [cputime]"
	echo "Example: restart_resource_exe.sh dido.imada.sdu.dk.0 exe"
}



########
# Main #
########
MiGuserconf=~/.MiG/MiGuser.conf
if [ ! -r $MiGuserconf ]; then
       	echo "restart_resource_exe.sh requires a readable configuration in $MiGuserconf"
        usage
	exit 1
fi	
migserver=`awk '/migserver/ {print $2}' $MiGuserconf`
certfile=`awk '/certfile/ {print $2}' $MiGuserconf`
key=`awk '/key/ {print $2}' $MiGuserconf`

if [ $# -eq 2 ]; then
	restart_resource_exe $1 $2
elif [ $# -eq 3 ]; then
        restart_resource_exe $1 $2 $3
else
	usage
	exit 1
fi
      
