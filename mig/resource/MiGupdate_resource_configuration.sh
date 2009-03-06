#!/bin/sh
function send_configuration() {
    config_filename=$1
    # Uncomment to debug
    # DEBUG_PREFIX="echo "
    cmd="${DEBUG_PREFIX}curl"
        
    # Specify password without making it visible in process 
    # list (e.g. 'ps awwx')
    # TODO: add \&amp\;recursive=$recursive to string when cgi is ready
    $cmd \
        -H "Content-Type: text/resourceconf" \
	--insecure \
	--cert $certfile \
	--key $key \
	--pass `awk '/pass/ {print $2}' $MiGuserconf` \
	--upload-file "$config_filename" \
	--url $migserver/
}

function usage(){
  echo "Usage..."
  echo "MiGupdate_resource_configration.sh configuration_file"
  echo "Example: MiGupdate_resource_configration.sh dido.imada.sdu.dk.0.config"
}


########
# Main #
########
MiGuserconf=~/.MiG/MiGuser.conf

if [ ! -r $MiGuserconf ]; then
    echo "MiGupdate_resource_configration.sh requires a readable configuration in $MiGuserconf"
    usage
    exit 1
fi 
migserver=`awk '/migserver/ {print $2}' $MiGuserconf`
certfile=`awk '/certfile/ {print $2}' $MiGuserconf`
key=`awk '/key/ {print $2}' $MiGuserconf`

if [ $# -eq 1 ]; then
    send_configuration $1
else
    usage
fi
