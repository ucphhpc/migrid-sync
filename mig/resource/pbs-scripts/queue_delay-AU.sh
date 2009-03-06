#!/bin/sh
#
# Estimate execution delay for a job with the supplied 
# -node count
# -walltime (seconds)
# -user

if [ -z "$MIG_MAXNODES" -o -z "$MIG_MAXSECONDS" -o -z "$MIG_SUBMITUSER" ]; then
    echo "Usage: $0"
    echo "where the environment should provide values for MIG_MAXNODES"
    echo "MIG_MAXSECONDS and MIG_SUBMITUSER."
    exit 1
fi

# Please note that the CUSTOM variable is used for cluster specific 
# settings, e.g. to only allow hosts in accordance with ARCHITECTURE
# In this case the nodes with node property 's50' are the X86 nodes.
CUSTOM="-f s50"
# No special options
#CUSTOM=""

# Use NODES, SECONDS and USER to get only matching output lines
showbf -n $MIG_MAXNODES -d $MIG_MAXSECONDS -u $MIG_SUBMITUSER $CUSTOM | \
    grep -E '[1-9][0-9]* procs available' > /dev/null
if [ $? -eq 0 ]; then
	# Idle node(s) available - no serious delay (15 mins)
	DELAY=900
else
	# Scale with requested node count
	DELAY=$(($MIG_MAXNODES*900))
fi
echo $DELAY
