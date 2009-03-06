#!/bin/bash

function list_resource_owners() {
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
	--url "$migserver/cgi-bin/lsresowners.py?with_html=false&unique_resource_name=${unique_resource_name}""
	        #-H "Query-String:  \
		# -H "Query-String: new_owner=${new_owner}" \

}

function usage(){
  echo "Usage..."
  echo "MiGlist_resource_owners.sh unique_resource_name"
  echo "Example: MiGlist_resource_owners.sh.0 dido.imada.sdu.dk"
}


########
# Main #
########
MiGuserconf=~/.MiG/MiGuser.conf

if [ ! -r $MiGuserconf ]; then
    echo "MiGlist_resource_owners.sh requires a readable configuration in $MiGuserconf"
    usage
    exit 1
fi 
migserver=`awk '/migserver/ {print $2}' $MiGuserconf`
certfile=`awk '/certfile/ {print $2}' $MiGuserconf`
key=`awk '/key/ {print $2}' $MiGuserconf`

if [ $# -eq 1 ]; then
    list_resource_owners "$1"
else
    usage
fi
