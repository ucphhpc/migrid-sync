#!/bin/bash

# submit a MiG job to LoadLeveler using llsubmit

# the submit command. A custom path can be specified here:
SUBMIT="./my_llsubmit -q "

############################################################
#######            nothing serviceable below             ###

# these variables have to be set, checked below
JOB_ENV="MIG_JOBNAME     MIG_SUBMITUSER MIG_JOBDIR    MIG_JOBNODECOUNT \
         MIG_JOBCPUCOUNT MIG_JOBCPUTIME MIG_JOBMEMORY MIG_JOBDISK"

function usage() {
    echo "Usage: $0 CLASS JOB_SCRIPT [ll options]"
    echo "where the environment should provide values for at least:"
    echo $JOB_ENV
    echo "The optional 'll options' are copied directly into the control"
    echo "file and should have form name=value (otherwise ignored)."
}

if [ -z $1 -o -z $2 ]; then 
    usage
    exit 1
fi

# MiG will automatically append JOB_SCRIPT argument to the call. We require it
# to be the second argument, after a class name as the 1st one.

JOB_CLASS=$1
shift
JOB_SCRIPT=$1
shift
OPTIONS=$@

# and check existence of environment variables:
if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" -o -z "$MIG_JOBDIR" -o -z "$MIG_JOBNODECOUNT" -o -z "$MIG_JOBCPUCOUNT" -o -z "$MIG_JOBCPUTIME" -o -z "$MIG_JOBMEMORY" -o -z "$MIG_JOBDISK" ]; then
    usage
    exit 1
fi

TMP=${MIG_JOBNAME}.`date +%F_%H-%M`

PREFIX="# @"

MIG_JOBSLOTCOUNT=$(( ${MIG_JOBNODECOUNT} * ${MIG_JOBCPUCOUNT} ))

# write the job description. Disk limits are not supported
cat > $TMP <<EOF
$PREFIX job_name   = ${MIG_JOBNAME}
$PREFIX executable = $JOB_SCRIPT
$PREFIX output     = \$(job_name).out
$PREFIX error      = \$(job_name).err
$PREFIX wall_clock_limit  = ${MIG_JOBCPUTIME},${MIG_JOBCPUTIME}
$PREFIX node       = ${MIG_JOBSLOTCOUNT},${MIG_JOBSLOTCOUNT}
$PREFIX resources  = ConsumableMemory(${MIG_JOBMEMORY}) 
$PREFIX initialdir = ${MIG_JOBDIR}
EOF

for OPT in $OPTIONS; do
    (echo $OPT | grep -e "^[a-zA-Z0-9_-]\+\ *=\ *[a-zA-Z0-9_-,.]\+\ *$" > /dev/null) \
	&& echo $PREFIX $OPT >> $TMP
done

$SUBMIT $TMP 

rm -f $TMP

if [ $? -ne 0 ]; then
    echo "Failed to submit to LoadLeveler"
    exit 1 
fi
#!/bin/bash

# submit a MiG job to LoadLeveler using llsubmit

# the submit command. A custom path can be specified here:
SUBMIT="./my_llsubmit -q "

############################################################
#######            nothing serviceable below             ###

# these variables have to be set, checked below
JOB_ENV="MIG_JOBNAME     MIG_SUBMITUSER MIG_JOBDIR    MIG_JOBNODECOUNT \
         MIG_JOBCPUCOUNT MIG_JOBCPUTIME MIG_JOBMEMORY MIG_JOBDISK"

function usage() {
    echo "Usage: $0 CLASS JOB_SCRIPT [ll options]"
    echo "where the environment should provide values for at least:"
    echo $JOB_ENV
    echo "The optional 'll options' are copied directly into the control"
    echo "file and should have form name=value (otherwise ignored)."
}

if [ -z $1 -o -z $2 ]; then 
    usage
    exit 1
fi

# MiG will automatically append JOB_SCRIPT argument to the call. We require it
# to be the second argument, after a class name as the 1st one.

JOB_CLASS=$1
shift
JOB_SCRIPT=$1
shift
OPTIONS=$@

# and check existence of environment variables:
if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" -o -z "$MIG_JOBDIR" -o -z "$MIG_JOBNODECOUNT" -o -z "$MIG_JOBCPUCOUNT" -o -z "$MIG_JOBCPUTIME" -o -z "$MIG_JOBMEMORY" -o -z "$MIG_JOBDISK" ]; then
    usage
    exit 1
fi

TMP=${MIG_JOBNAME}.`date +%F_%H-%M`

PREFIX="# @"

MIG_JOBSLOTCOUNT=$(( ${MIG_JOBNODECOUNT} * ${MIG_JOBCPUCOUNT} ))

# write the job description. Disk limits are not supported
cat > $TMP <<EOF
$PREFIX job_name   = ${MIG_JOBNAME}
$PREFIX executable = $JOB_SCRIPT
$PREFIX output     = \$(job_name).out
$PREFIX error      = \$(job_name).err
$PREFIX wall_clock_limit  = ${MIG_JOBCPUTIME},${MIG_JOBCPUTIME}
$PREFIX node       = ${MIG_JOBSLOTCOUNT},${MIG_JOBSLOTCOUNT}
$PREFIX resources  = ConsumableMemory(${MIG_JOBMEMORY}) 
$PREFIX initialdir = ${MIG_JOBDIR}
EOF

for OPT in $OPTIONS; do
    (echo $OPT | grep -e "^[a-zA-Z0-9_-]\+\ *=\ *[a-zA-Z0-9_-,.]\+\ *$" > /dev/null) \
	&& echo $PREFIX $OPT >> $TMP
done

$SUBMIT $TMP 

rm -f $TMP

if [ $? -ne 0 ]; then
    echo "Failed to submit to LoadLeveler"
    exit 1 
fi
#!/bin/bash

# submit a MiG job to LoadLeveler using llsubmit

# the submit command. A custom path can be specified here:
SUBMIT="llsubmit -q "

############################################################
#######            nothing serviceable below             ###

# these variables have to be set, checked below
JOB_ENV="MIG_JOBNAME     MIG_SUBMITUSER MIG_JOBDIR    MIG_JOBNODECOUNT \
         MIG_JOBCPUCOUNT MIG_JOBCPUTIME MIG_JOBMEMORY MIG_JOBDISK"

function usage() {
    echo "Usage: $0 CLASS JOB_SCRIPT [ll options]"
    echo "where the environment should provide values for at least:"
    echo $JOB_ENV
    echo "The optional 'll options' are copied directly into the control"
    echo "file and should have form name=value (otherwise ignored)."
}

# MiG will automatically append JOB_SCRIPT argument to the call. We require it
# to be the second argument, after a class name as the 1st one.
if [ $# -le 1 ]; then 
    usage
    exit 1
fi

JOB_CLASS=$1
shift
JOB_SCRIPT=$1
shift
OPTIONS=$@

# and check existence of environment variables:
if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" -o -z "$MIG_JOBDIR" -o -z "$MIG_JOBNODECOUNT" -o -z "$MIG_JOBCPUCOUNT" -o -z "$MIG_JOBCPUTIME" -o -z "$MIG_JOBMEMORY" -o -z "$MIG_JOBDISK" ]; then
    usage
    exit 1
fi

TMP=${MIG_JOBNAME}.`date +%F_%H-%M`

PREFIX="# @"

MIG_JOBSLOTCOUNT=$(( ${MIG_JOBNODECOUNT} * ${MIG_JOBCPUCOUNT} ))

# write the job description. Disk limits are not supported
cat > $TMP <<EOF
$PREFIX job_name   = ${MIG_JOBNAME}
$PREFIX executable = $JOB_SCRIPT
$PREFIX output     = \$(job_name).out
$PREFIX error      = \$(job_name).err
$PREFIX wall_clock_limit  = ${MIG_JOBCPUTIME},${MIG_JOBCPUTIME}
$PREFIX node       = ${MIG_JOBSLOTCOUNT},${MIG_JOBSLOTCOUNT}
$PREFIX resources  = ConsumableMemory(${MIG_JOBMEMORY}) 
$PREFIX initialdir = ${MIG_JOBDIR}
EOF

for OPT in $OPTIONS; do
    (echo $OPT | grep -e "^[a-zA-Z0-9_-]\+\ *=\ *[a-zA-Z0-9_-,.]\+\ *$" > /dev/null) \
	&& echo $PREFIX $OPT >> $TMP
done

$SUBMIT $TMP 

rm -f $TMP

if [ $? -ne 0 ]; then
    echo "Failed to submit to LoadLeveler"
    exit 1 
fi
#!/bin/bash

# submit a MiG job to LoadLeveler using llsubmit

# the submit command. A custom path can be specified here:
SUBMIT="./my_llsubmit -q "

############################################################
#######            nothing serviceable below             ###

# these variables have to be set, checked below
JOB_ENV="MIG_JOBNAME     MIG_SUBMITUSER MIG_JOBDIR    MIG_JOBNODECOUNT \
         MIG_JOBCPUCOUNT MIG_JOBCPUTIME MIG_JOBMEMORY MIG_JOBDISK"

function usage() {
    echo "Usage: $0 CLASS JOB_SCRIPT [ll options]"
    echo "where the environment should provide values for at least:"
    echo $JOB_ENV
    echo "The optional 'll options' are copied directly into the control"
    echo "file and should have form name=value (otherwise ignored)."
}

if [ -z $1 -o -z $2 ]; then 
    usage
    exit 1
fi

# MiG will automatically append JOB_SCRIPT argument to the call. We require it
# to be the second argument, after a class name as the 1st one.

JOB_CLASS=$1
shift
JOB_SCRIPT=$1
shift
OPTIONS=$@

# and check existence of environment variables:
if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" -o -z "$MIG_JOBDIR" -o -z "$MIG_JOBNODECOUNT" -o -z "$MIG_JOBCPUCOUNT" -o -z "$MIG_JOBCPUTIME" -o -z "$MIG_JOBMEMORY" -o -z "$MIG_JOBDISK" ]; then
    usage
    exit 1
fi

TMP=${MIG_JOBNAME}.`date +%F_%H-%M`

PREFIX="# @"

MIG_JOBSLOTCOUNT=$(( ${MIG_JOBNODECOUNT} * ${MIG_JOBCPUCOUNT} ))

# write the job description. Disk limits are not supported
cat > $TMP <<EOF
$PREFIX job_name   = ${MIG_JOBNAME}
$PREFIX executable = $JOB_SCRIPT
$PREFIX output     = \$(job_name).out
$PREFIX error      = \$(job_name).err
$PREFIX wall_clock_limit  = ${MIG_JOBCPUTIME},${MIG_JOBCPUTIME}
$PREFIX node       = ${MIG_JOBSLOTCOUNT},${MIG_JOBSLOTCOUNT}
$PREFIX resources  = ConsumableMemory(${MIG_JOBMEMORY}) 
$PREFIX initialdir = ${MIG_JOBDIR}
EOF

for OPT in $OPTIONS; do
    (echo $OPT | grep -e "^[a-zA-Z0-9_-]\+\ *=\ *[a-zA-Z0-9_-,.]\+\ *$" > /dev/null) \
	&& echo $PREFIX $OPT >> $TMP
done

$SUBMIT $TMP 

rm -f $TMP

if [ $? -ne 0 ]; then
    echo "Failed to submit to LoadLeveler"
    exit 1 
fi
#!/bin/bash

# submit a MiG job to LoadLeveler using llsubmit

# the submit command. A custom path can be specified here:
SUBMIT="llsubmit -q "

############################################################
#######            nothing serviceable below             ###

# these variables have to be set, checked below
JOB_ENV="MIG_JOBNAME     MIG_SUBMITUSER MIG_JOBDIR    MIG_JOBNODECOUNT \
         MIG_JOBCPUCOUNT MIG_JOBCPUTIME MIG_JOBMEMORY MIG_JOBDISK"

function usage() {
    echo "Usage: $0 CLASS JOB_SCRIPT [ll options]"
    echo "where the environment should provide values for at least:"
    echo $JOB_ENV
    echo "The optional 'll options' are copied directly into the control"
    echo "file and should have form name=value (otherwise ignored)."
}

# MiG will automatically append JOB_SCRIPT argument to the call. We require it
# to be the second argument, after a class name as the 1st one.
if [ $# -le 1 ]; then 
    usage
    exit 1
fi

JOB_CLASS=$1
shift
JOB_SCRIPT=$1
shift
OPTIONS=$@

# and check existence of environment variables:
if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" -o -z "$MIG_JOBDIR" -o -z "$MIG_JOBNODECOUNT" -o -z "$MIG_JOBCPUCOUNT" -o -z "$MIG_JOBCPUTIME" -o -z "$MIG_JOBMEMORY" -o -z "$MIG_JOBDISK" ]; then
    usage
    exit 1
fi

TMP=${MIG_JOBNAME}.`date +%F_%H-%M`

PREFIX="# @"

MIG_JOBSLOTCOUNT=$(( ${MIG_JOBNODECOUNT} * ${MIG_JOBCPUCOUNT} ))

# write the job description. Disk limits are not supported
cat > $TMP <<EOF
$PREFIX job_name   = ${MIG_JOBNAME}
$PREFIX executable = $JOB_SCRIPT
$PREFIX output     = \$(job_name).out
$PREFIX error      = \$(job_name).err
$PREFIX wall_clock_limit  = ${MIG_JOBCPUTIME},${MIG_JOBCPUTIME}
$PREFIX node       = ${MIG_JOBSLOTCOUNT},${MIG_JOBSLOTCOUNT}
$PREFIX resources  = ConsumableMemory(${MIG_JOBMEMORY}) 
$PREFIX initialdir = ${MIG_JOBDIR}
EOF

for OPT in $OPTIONS; do
    (echo $OPT | grep -e "^[a-zA-Z0-9_-]\+\ *=\ *[a-zA-Z0-9_-,.]\+\ *$" > /dev/null) \
	&& echo $PREFIX $OPT >> $TMP
done

$SUBMIT $TMP 

rm -f $TMP

if [ $? -ne 0 ]; then
    echo "Failed to submit to LoadLeveler"
    exit 1 
fi
