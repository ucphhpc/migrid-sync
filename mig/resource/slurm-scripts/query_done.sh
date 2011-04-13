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

# Find job in queue - prints numeric job PID if not yet done. -o prints full jobname which is otherwise shortened.
# We return false in case of squeue errors in order to avoid false 
# positives if SLURM daemon is temporarily unavailable
jobs=`squeue -u "$MIG_SUBMITUSER" -o "%j" $@`
if [ $? -ne 0 ]; then
    echo "Failed to query SLURM for job status - try again later"
    exit 1 
fi

echo "$jobs" | grep "$MIG_JOBNAME" > /dev/null
# Invert grep result to return 0 if done
test $? -ne 0
