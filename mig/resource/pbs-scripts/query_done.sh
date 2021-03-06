#!/bin/sh
#
# Test if job with supplied name and submitted by given user is finished

if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" ]; then
    echo "Usage: $0 [QUEUE_ARGS]"
    echo "where the environment should provide values for MIG_JOBNAME"
    echo "and MIG_SUBMITUSER."
    echo "The optional QUEUE_ARGS are passed directly to the queue command(s)."
    exit 1
fi

# Find job in queue - prints numeric job PID if not yet done.
# We return false in case of qselect errors in order to avoid false 
# positives if PBS daemon is temporarily unavailable
jobs=`qselect -N "$MIG_JOBNAME" -u "$MIG_SUBMITUSER" $@`
if [ $? -ne 0 ]; then
    echo "Failed to query PBS for job status - try again later"
    exit 1 
fi

echo "$jobs" | grep -E '[0-9]' > /dev/null
# Invert grep result to return 0 if done
test $? -ne 0
