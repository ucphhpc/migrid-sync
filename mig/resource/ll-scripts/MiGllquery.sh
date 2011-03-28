#!/bin/bash

# submit a MiG job to LoadLeveler using llsubmit

# the command. A custom path can be specified here:
GET_INFO="./my_llclass "

############################################################
#######            nothing serviceable below             ###

# Estimate execution delay for a job with the supplied 
# -node count
# -walltime (seconds)
# -user

# these variables have to be set, checked below
JOB_ENV="MIG_MAXNODES     MIG_MAXSECONDS     MIG_SUBMITUSER"

function usage() {
    echo "Usage: $0 CLASS"
    echo "CLASS being a LL class, and the environment provides values for "
    echo "MIG_MAXNODES, MIG_MAXSECONDS and MIG_SUBMITUSER"
}

if [ $# -eq 0 -o -z "$MIG_MAXNODES" -o \
     -z "$MIG_MAXSECONDS" -o -z "$MIG_SUBMITUSER" ]; then
    usage
    exit 1
fi

CLASS=$1

echo Doing $GET_INFO "$CLASS"

# expected format:

FREE_SLOTS=`$GET_INFO "$CLASS" | grep "$CLASS" | head -1 | awk '{ print $4}' `
query_status=$?
if [ $query_status -ne 0 ]; then
    # Print warning to stderr to avoid interference with output
    echo "Failed to query for free slots - aim high" 1>&2
    DELAY="1800"
else
    if [ $FREE_SLOTS -ge $MIG_MAXNODES ]; then
        # Idle node(s) available - no serious delay (5 mins)
	DELAY=300
    else
        # Scale with requested node count
	DELAY=$(($MIG_MAXNODES*300))
    fi
fi
echo $DELAY
#!/bin/bash

# submit a MiG job to LoadLeveler using llsubmit

# the command. A custom path can be specified here:
GET_INFO="./my_llclass "

############################################################
#######            nothing serviceable below             ###

# Estimate execution delay for a job with the supplied 
# -node count
# -walltime (seconds)
# -user

# these variables have to be set, checked below
JOB_ENV="MIG_MAXNODES     MIG_MAXSECONDS     MIG_SUBMITUSER"

function usage() {
    echo "Usage: $0 CLASS"
    echo "CLASS being a LL class, and the environment provides values for "
    echo "MIG_MAXNODES, MIG_MAXSECONDS and MIG_SUBMITUSER"
}

if [ $# -eq 0 -o -z "$MIG_MAXNODES" -o \
     -z "$MIG_MAXSECONDS" -o -z "$MIG_SUBMITUSER" ]; then
    usage
    exit 1
fi

CLASS=$1

echo Doing $GET_INFO "$CLASS"

# expected format:

FREE_SLOTS=`$GET_INFO "$CLASS" | grep "$CLASS" | head -1 | awk '{ print $4}' `
query_status=$?
if [ $query_status -ne 0 ]; then
    # Print warning to stderr to avoid interference with output
    echo "Failed to query for free slots - aim high" 1>&2
    DELAY="1800"
else
    if [ $FREE_SLOTS -ge $MIG_MAXNODES ]; then
        # Idle node(s) available - no serious delay (5 mins)
	DELAY=300
    else
        # Scale with requested node count
	DELAY=$(($MIG_MAXNODES*300))
    fi
fi
echo $DELAY
#!/bin/bash

# submit a MiG job to LoadLeveler using llsubmit

# the command. A custom path can be specified here:
GET_INFO="./my_llclass "

############################################################
#######            nothing serviceable below             ###

# Estimate execution delay for a job with the supplied 
# -node count
# -walltime (seconds)
# -user

# these variables have to be set, checked below
JOB_ENV="MIG_MAXNODES     MIG_MAXSECONDS     MIG_SUBMITUSER"

function usage() {
    echo "Usage: $0 CLASS"
    echo "CLASS being a LL class, and the environment provides values for "
    echo "MIG_MAXNODES, MIG_MAXSECONDS and MIG_SUBMITUSER"
}

if [ $# -eq 0 -o -z "$MIG_MAXNODES" -o \
     -z "$MIG_MAXSECONDS" -o -z "$MIG_SUBMITUSER" ]; then
    usage
    exit 1
fi

CLASS=$1

echo Doing $GET_INFO "$CLASS"

# expected format:

FREE_SLOTS=`$GET_INFO "$CLASS" | grep "$CLASS" | head -1 | awk '{ print $4}' `
query_status=$?
if [ $query_status -ne 0 ]; then
    # Print warning to stderr to avoid interference with output
    echo "Failed to query for free slots - aim high" 1>&2
    DELAY="1800"
else
    if [ $FREE_SLOTS -ge $MIG_MAXNODES ]; then
        # Idle node(s) available - no serious delay (5 mins)
	DELAY=300
    else
        # Scale with requested node count
	DELAY=$(($MIG_MAXNODES*300))
    fi
fi
echo $DELAY
#!/bin/bash

# submit a MiG job to LoadLeveler using llsubmit

# the command. A custom path can be specified here:
GET_INFO="./my_llclass "

############################################################
#######            nothing serviceable below             ###

# Estimate execution delay for a job with the supplied 
# -node count
# -walltime (seconds)
# -user

# these variables have to be set, checked below
JOB_ENV="MIG_MAXNODES     MIG_MAXSECONDS     MIG_SUBMITUSER"

function usage() {
    echo "Usage: $0 CLASS"
    echo "CLASS being a LL class, and the environment provides values for "
    echo "MIG_MAXNODES, MIG_MAXSECONDS and MIG_SUBMITUSER"
}

if [ $# -eq 0 -o -z "$MIG_MAXNODES" -o \
     -z "$MIG_MAXSECONDS" -o -z "$MIG_SUBMITUSER" ]; then
    usage
    exit 1
fi

CLASS=$1

echo Doing $GET_INFO "$CLASS"

# expected format:

FREE_SLOTS=`$GET_INFO "$CLASS" | grep "$CLASS" | head -1 | awk '{ print $4}' `
query_status=$?
if [ $query_status -ne 0 ]; then
    # Print warning to stderr to avoid interference with output
    echo "Failed to query for free slots - aim high" 1>&2
    DELAY="1800"
else
    if [ $FREE_SLOTS -ge $MIG_MAXNODES ]; then
        # Idle node(s) available - no serious delay (5 mins)
	DELAY=300
    else
        # Scale with requested node count
	DELAY=$(($MIG_MAXNODES*300))
    fi
fi
echo $DELAY
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
