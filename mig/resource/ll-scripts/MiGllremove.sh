#!/bin/bash

# delete a MiG job from LoadLeveler using llq and llcancel

# the needed commands. A custom path can be specified here:
CANCEL="llcancel"
QUERY="llq"

############################################################
#######            nothing serviceable below             ###

# these variables have to be set, checked below
JOB_ENV="MIG_JOBNAME     MIG_SUBMITUSER"

function usage() {
    echo "Usage: $0 CLASS"
    echo "where CLASS is the job class used, and the environment should"
    echo "provide values for MIG_JOBNAME and MIG_SUBMITUSER"
}

# check argument count and existence of environment variables:
if [ $# -ne 1 -o -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" ]; then
    usage
    exit 1
fi

CLASS=$1

# Find job in queue - print alphanumeric job PID if still present
# the command might return several jobs in several lines, we take only one
job_id=`$QUERY -c "$CLASS" -u "$MIG_SUBMITUSER" -f %st %jn %id | \
        grep -e "$MIG_JOBNAME" | \
        awk '{print $3}' | head -1`
# Delete job if found in queue
if [ ! -z "$job_id" ]; then
    $CANCEL "$job_id"
else
    echo "no such job in queue"
    exit 1
fi
