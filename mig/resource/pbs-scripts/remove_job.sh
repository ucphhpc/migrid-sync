#!/bin/sh
#
# Remove job with supplied job name and submitted by user

if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" ]; then
    echo "Usage: $0 [QUEUE_ARGS]"
    echo "where the environment should provide values for MIG_JOBNAME"
    echo "and MIG_SUBMITUSER."
    echo "The optional QUEUE_ARGS are passed directly to the queue command(s)."
    exit 1
fi

# Find job in queue - prints alphanumeric job PID if not yet done
job_id=`qselect -N "$MIG_JOBNAME" -u "$MIG_SUBMITUSER" $@`
# Delete job if found in queue
if [ ! -z "$job_id" ]; then
    qdel $job_id
else
    echo "no such job in queue"
    exit 1
fi
