#!/bin/bash

function remove_resource_owner() {
    unique_resource_name="$1"
    remove_owner="$2"
    remove_owner_without_spaces="${remove_owner//" "/_}"
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
	--url "$migserver/cgi-bin/rmresowner.py?remove_owner=${remove_owner_without_spaces}&with_html=false&unique_resource_name=${unique_resource_name}""
	        #-H "Query-String:  \
		# -H "Query-String: new_owner=${new_owner}" \

}

function usage(){
  echo "Usage..."
  echo "MiGremove_resource_owner.sh unique_resource_name remove_owner_cn"
  echo "Example: MiGremove_resource_owner.sh dido.imada.sdu.dk.0 \"Henrik Hoey Karlsen\""
}


########
# Main #
########
MiGuserconf=~/.MiG/MiGuser.conf

if [ ! -r $MiGuserconf ]; then
    echo "MiGremove_resource_owner.sh requires a readable configuration in $MiGuserconf"
    usage
    exit 1
fi 
migserver=`awk '/migserver/ {print $2}' $MiGuserconf`
certfile=`awk '/certfile/ {print $2}' $MiGuserconf`
key=`awk '/key/ {print $2}' $MiGuserconf`

if [ $# -eq 2 ]; then
    remove_resource_owner "$1" "$2"
else
    usage
fi
