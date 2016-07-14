#!/bin/sh
#
# Estimate execution delay for a job with the supplied 
# -node count
# -walltime (seconds)
# -user
# -partition (implicit by MIG_EXENODE)

if [ -z "$MIG_MAXNODES" -o -z "$MIG_MAXSECONDS" -o -z "$MIG_SUBMITUSER" -o -z "$MIG_EXENODE" ]; then
    echo "Usage: $0 [QUEUE_ARGS]"
    echo "where the environment should provide values for MIG_MAXNODES,"
    echo "MIG_MAXSECONDS, MIG_SUBMITUSER and MIG_EXENODE."
    echo "The optional QUEUE_ARGS are passed directly to the queue command(s)."
    exit 1
fi

#PARTITION="$MIG_EXENODE"

# We return false in case of sinfo errors in order to avoid false 
# positives if SLURM daemon is temporarily unavailable
query_status=0
# Check if partition exist
if [ `sinfo -h -p "$MIG_EXENODE" | wc -l` -eq 0 ]; then
   query_status=1
fi

idle_nodes=`sinfo -h -a idle -p "$MIG_EXENODE" -o "%A" | awk -F'/' '{print $2}'`
query_status=$(($query_status+$?))

max_queue_time=`sinfo -h -p "$MIG_EXENODE" -o "%l" | \
                awk -F[:-] '{if (NF == 4) print $1*86400+$2*3600+$3*60+$4; \
                             else print $1*3600+$2*60+$3}'`
query_status=$(($query_status+$?))

suspendable=`scontrol show part "$MIG_EXENODE" | grep "PreemptMode=SUSPEND" | wc -l`
query_status=$(($query_status+$?))

if [ $query_status -ne 0 ] || [ $max_queue_time -eq 0 ] || [ $suspendable -gt 0 ]; then
    # Print warning to stderr to avoid interference with output
    echo -n "Failed to query SLURM for job delay, " 1>&2
    echo "infinite queue time or suspendalbe queue - aim high" 1>&2
    DELAY="84600"
elif [ $idle_nodes -ge $MIG_MAXNODES ]; then
    # Idle node(s) available - no delay (1 min)
    DELAY=60
else
    # Wait for jobs to finish 
    DELAY=$max_queue_time
fi

echo $DELAY
