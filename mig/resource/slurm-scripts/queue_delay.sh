#!/bin/sh
#
# Estimate execution delay for a job with the supplied 
# -node count
# -walltime (seconds)
# -user

if [ -z "$MIG_MAXNODES" -o -z "$MIG_MAXSECONDS" -o -z "$MIG_SUBMITUSER" ]; then
    echo "Usage: $0 [QUEUE_ARGS]"
    echo "where the environment should provide values for MIG_MAXNODES"
    echo "MIG_MAXSECONDS and MIG_SUBMITUSER."
    echo "The optional QUEUE_ARGS are passed directly to the queue command(s)."
    exit 1
fi

# Use NODES, SECONDS and USER to get only matching output lines
# We return false in case of qselect errors in order to avoid false 
# positives if PBS daemon is temporarily unavailable
#backfill=`showbf -n "$MIG_MAXNODES" -d "$MIG_MAXSECONDS" -u "$MIG_SUBMITUSER" $@`
#query_status=$?
#echo "$backfill" | grep -E '[1-9][0-9]* procs available' > /dev/null
#backfill_status=$?
# No easy showbf equivalent for SLURM - use average estimate
query_status=0
backfill_status=1
if [ $query_status -ne 0 ]; then
    # Print warning to stderr to avoid interference with output
    echo "Failed to query SLURM for job delay - aim high" 1>&2
    DELAY="86400"
elif [ $backfill_status -eq 0 ]; then
    # Idle node(s) available - no serious delay (15 mins)
    DELAY=900
else
    # Scale with requested node count
    DELAY=$(($MIG_MAXNODES*900))
fi
echo $DELAY
