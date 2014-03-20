#!/bin/sh
#
# Remove job with supplied job name and submitted by user

if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" -o -z "$MIG_EXEUNIT" ]; then
    echo "Usage: $0 [QUEUE_ARGS]"
    echo "where the environment should provide values for MIG_JOBNAME,"
    echo "MIG_SUBMITUSER and MIG_EXEUNIT."
    echo "The optional QUEUE_ARGS are passed directly to the queue command(s)."
    exit 1
fi

# Kill matching jobs in queue
scancel -n "$MIG_JOBNAME" -u "$MIG_SUBMITUSER" -p "$MIG_EXEUNIT" $@
