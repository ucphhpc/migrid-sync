#!/bin/bash

function update(){
  filename=$1
  suffix=$2
  
  for e in `cat $filename`; do
    ./MiGupdate_resource_configuration.sh "${e}${suffix}.config"
  done
  echo "done"
}
function usage(){
echo "Usage: UpdateClusterConfiguration.sh filename 'suffix_that_makes_hostname_unique'"
echo "Example: UpdateClusterConfiguration.sh imadamaskiner '.0'"
}

if [ $# -eq 2 ]; then
    update $1 $2
else
    usage
fi	
