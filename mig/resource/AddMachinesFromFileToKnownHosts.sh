#!/bin/bash

function connect(){
  filename=$1
  
  for e in `cat $filename`; do
    ssh $e "echo hello $e"
  done
  echo "done"
}
function usage(){
echo "Usage: AddMachinesFromFileToKnownHosts.sh filename "
}
if [ $# -eq 1 ]; then
    connect $1
else
    usage
fi	
