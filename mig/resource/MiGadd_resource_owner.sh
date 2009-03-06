#!/bin/bash
script_name="MiGadd_resource_owner.sh"

function submit_command() {
    unique_resource_name="$1"
    new_owner="$2"
    new_owner_without_spaces="${new_owner//" "/_}"
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
	--url "$migserver/cgi-bin/addresowner.py?new_owner=${new_owner_without_spaces}&with_html=false&unique_resource_name=${unique_resource_name}""
	        #-H "Query-String:  \
		# -H "Query-String: new_owner=${new_owner}" \

}

function usage(){
  echo "Usage:"
  echo "$script_name unique_resource_name new_owner_cn"
  echo "Example: $script_name dido.imada.sdu.dk.0 \"Henrik Hoey Karlsen\""
}


########
# Main #
########
MiGuserconf=~/.MiG/MiGuser.conf

if [ ! -r $MiGuserconf ]; then
    echo "$script_name requires a readable configuration in $MiGuserconf"
    usage
    exit 1
fi 
migserver=`awk '/migserver/ {print $2}' $MiGuserconf`
certfile=`awk '/certfile/ {print $2}' $MiGuserconf`
key=`awk '/key/ {print $2}' $MiGuserconf`

if [ $# -eq 2 ]; then
    submit_command "$1" "$2"
else
    usage
fi
