#!/bin/bash
script_name="MiGvgrid_list_members.sh"

function submit_command() {
    vgrid_name="$1"
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
	--url "$migserver/cgi-bin/vgrid_list_members.py?with_html=false&vgrid_name=${vgrid_name}""
	        #-H "Query-String:  \
		# -H "Query-String: new_owner=${new_owner}" \

}

function usage(){
  echo "Usage:"
  echo "$script_name vgrid_name"
  echo "Example: $script_name dalton"
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

if [ $# -eq 1 ]; then
    submit_command "$1"
else
    usage
fi
