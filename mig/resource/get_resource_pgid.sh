#!/bin/sh
function get_resource_pgid(){
	unique_resource_name="$1"
	exe_name="$2"

        if [ "$exe_name" == "" ]; then
	   type="FE"
	else
	   type="EXE"
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
        --url "$migserver/cgi-bin/get_resource_pgid?unique_resource_name=$unique_resource_name&exe_name=$exe_name&type=$type"
}
      
function usage(){
	echo "Usage..."
	echo "get_resource_pgid.sh unique_resource_name [exe_name]"
	echo "Example: get_resource_pgid.sh dido.imada.sdu.dk.0 exe"
}



########
# Main #
########
MiGuserconf=~/.MiG/MiGuser.conf
if [ ! -r $MiGuserconf ]; then
       	echo "get_resource_pgid.sh requires a readable configuration in $MiGuserconf"
        usage
	exit 1
fi	
migserver=`awk '/migserver/ {print $2}' $MiGuserconf`
certfile=`awk '/certfile/ {print $2}' $MiGuserconf`
key=`awk '/key/ {print $2}' $MiGuserconf`
if [ $# -eq 1 ]; then
	get_resource_pgid $1 ""
elif [ $# -eq 2 ]; then
        get_resource_pgid $1 $2
else
	usage
	exit 1
fi
      
