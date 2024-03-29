#!/bin/sh
function stop_resource_frontend(){
	unique_resource_name="$1"
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
        --url "$migserver/cgi-bin/stopfe.py?unique_resource_name=$unique_resource_name"
}
      


function usage(){
	echo "Usage..."
	echo "stop_resource_frontend.sh unique_resource_name"
	echo "Example: stop_resource_frontend.sh dido.imada.sdu.dk.0"
}



########
# Main #
########
MiGuserconf=~/.MiG/MiGuser.conf
if [ ! -r $MiGuserconf ]; then
       	echo "stop_resource_frontend.sh requires a readable configuration in $MiGuserconf"
        usage
	exit 1
fi	
migserver=`awk '/migserver/ {print $2}' $MiGuserconf`
certfile=`awk '/certfile/ {print $2}' $MiGuserconf`
key=`awk '/key/ {print $2}' $MiGuserconf`
if [ $# -eq 1 ]; then
        stop_resource_frontend $1
else
	usage
	exit 1
fi
      
