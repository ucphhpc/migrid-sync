#!/bin/bash

# get status information for a MiG job in LoadLeveler using llq

# the command. A custom path can be specified here:
QUERY="llq"

############################################################
#######            nothing serviceable below             ###

# these variables have to be set, checked below
JOB_ENV="MIG_JOBNAME     MIG_SUBMITUSER"

function usage() {
    echo "Usage: $0 [CLASS]"
    echo "where CLASS is the LL class and the environment should provide"
    echo "values for MIG_JOBNAME and MIG_SUBMITUSER"
}

#  check existence of environment variables:
if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" ]; then
    usage
    exit 1
fi

# a class name can be given
if [ ! -z "$1" ]; then
    CLASS_OPT="-c $1"
fi


# Find job in queue - prints alphanumeric job PID if not yet done
# query might return several lines, in which case we only use the first one.
job=`$QUERY -f %st %jn %id $CLASS_OPT -u "$MIG_SUBMITUSER" | \
    grep -e "$MIG_JOBNAME" | head -1`

# job not found? ($jobs empty)
[ -z "$job" ] && exit 0
# job might be in queue with status "Complete" (first column)
echo "$job" | grep -e "^C.*$MIG_JOBNAME$" && exit 0
# otherwise, the job is still in the queue.
exit 1
