#!/bin/bash

# estimate delay from information about LoadLeveler queue status using llclass

# the command. A custom path can be specified here:
GET_INFO="llclass"

############################################################
#######            nothing serviceable below             ###

# Estimate execution delay for a job with the supplied 
# -node count
# -walltime (seconds)
# -user

# these variables have to be set, checked below
JOB_ENV="MIG_MAXNODES     MIG_MAXSECONDS     MIG_SUBMITUSER"

function usage() {
    echo "Usage: $0 CLASS"
    echo "CLASS being a LL class, and the environment provides values for "
    echo "MIG_MAXNODES, MIG_MAXSECONDS and MIG_SUBMITUSER"
}

if [ $# -eq 0 -o -z "$MIG_MAXNODES" -o \
     -z "$MIG_MAXSECONDS" -o -z "$MIG_SUBMITUSER" ]; then
    usage
    exit 1
fi

CLASS=$1

# expected format (llclass standard, cannot be modified by flags):
#Name   MaxJobCPU  MaxProcCPU  Free-Slots   Max-Slots  Description
# we extract the free-slots field (field 4)
FREE_SLOTS=`$GET_INFO "$CLASS" | grep "$CLASS" | head -1 | awk '{ print $4}' `
query_status=$?
if [ $query_status -ne 0 ]; then
    # Print warning to stderr to avoid interference with output
    echo "Failed to query for free slots - aim high" 1>&2
    DELAY="1800"
else
    if [ $FREE_SLOTS -ge $MIG_MAXNODES ]; then
        # Idle node(s) available - no serious delay (5 mins)
	DELAY=300
    else
        # Scale with requested node count
	DELAY=$(($MIG_MAXNODES*300))
    fi
fi
echo $DELAY
