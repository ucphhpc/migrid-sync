#!/bin/bash

################

This file is no longer maintained. Remove?

################



function update(){
   unique_resource_name="$1"
   filename="$2"
   # uncomment to debug

   ./start_resource_frontend.sh ${unique_resource_name}
   
   for e in `cat $filename`; do
     sleep 2
     ./start_resource_exe.sh ${unique_resource_name} $e
   done

   echo "done"
}
   
function usage(){
   echo "Usage: StartClusterSingleFrontendMultipleExe.sh unique_resource_name exehosts_filename"
   echo "Example: StartClusterSingleFrontendMultipleExe.sh rocks.cs.uit.no.0 rocks-nodes"
}

if [ $# -eq 2 ]; then
   update $1 $2
else
   usage
fi
	      
