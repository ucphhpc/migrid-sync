#!/bin/sh
function restart_resource_all_exes(){
	unique_resource_name="$1"
	if [ $# -eq 2 ]; then
	  cputime="$2"
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
        --url "$migserver/cgi-bin/restartallexes.py?unique_resource_name=$unique_resource_name&cputime=$cputime"
}
      
function usage(){
	echo "Usage..."
	echo "restart_resource_all_exes.sh unique_resource_name [cputime]"
	echo "Example: restart_resource_all_exes.sh dido.imada.sdu.dk.0"
}



########
# Main #
########
MiGuserconf=~/.MiG/MiGuser.conf
if [ ! -r $MiGuserconf ]; then
       	echo "restart_resource_all_exes.sh requires a readable configuration in $MiGuserconf"
        usage
	exit 1
fi	
migserver=`awk '/migserver/ {print $2}' $MiGuserconf`
certfile=`awk '/certfile/ {print $2}' $MiGuserconf`
key=`awk '/key/ {print $2}' $MiGuserconf`

if [ $# -eq 1 ]; then
	restart_resource_all_exes $1
elif [ $# -eq 2 ]; then
	restart_resource_all_exes $1 $2
else
	usage
	exit 1
fi
      
