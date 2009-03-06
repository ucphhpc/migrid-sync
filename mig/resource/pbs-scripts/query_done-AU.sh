#!/bin/sh
#
# Test if job with supplied name and submitted by given user is finished

if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" ]; then
    echo "Usage: $0"
    echo "where the environment should provide values for MIG_JOBNAME"
    echo "and MIG_SUBMITUSER."
    exit 1
fi

# Find job in queue - prints numeric job PID if not yet done
qselect -N "$MIG_JOBNAME" -u "$MIG_SUBMITUSER"| grep -E '[0-9]' > /dev/null
# Invert grep result to return 0 if done
test $? -ne 0
