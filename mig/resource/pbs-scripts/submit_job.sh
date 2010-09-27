#!/bin/sh
#
# Submit supplied job script using all supplied MiG environmnets
# Please note that MiG will automatically append JOB_SCRIPT argument to the call

if [ -z "$MIG_JOBNAME" -o -z "$MIG_SUBMITUSER" -o -z "$MIG_JOBDIR" -o -z "$MIG_JOBNODECOUNT" -o -z "$MIG_JOBCPUCOUNT" -o -z "$MIG_JOBCPUTIME" -o -z "$MIG_JOBMEMORY" -o -z "$MIG_JOBDISK" ]; then
    echo "Usage: $0 [QUEUE_ARGS] JOB_SCRIPT"
    echo "where the environment should provide values for at least:"
    echo "MIG_JOBNAME MIG_SUBMITUSER MIG_JOBDIR MIG_JOBNODECOUNT MIG_JOBCPUCOUNT"
    echo "MIG_JOBCPUTIME MIG_JOBMEMORY MIG_JOBDISK"
    echo "The optional QUEUE_ARGS are passed directly to the queue command(s)."
    exit 1
fi

if [ -z "$MIG_ADMINEMAIL" ]; then
    mail_opt=""
else
    mail_opt="-M $MIG_ADMINEMAIL"
fi

# PBS does not allow total disk limit so we ignore it
qsub -l walltime=$MIG_JOBCPUTIME -l nodes=${MIG_JOBNODECOUNT}:ppn=${MIG_JOBCPUCOUNT} \
    -l mem=${MIG_JOBMEMORY}mb -l pmem=${MIG_JOBMEMORY}mb -r n -N $MIG_JOBNAME \
    -o $MIG_JOBNAME.out -e $MIG_JOBNAME.err -d $MIG_JOBDIR $mail_opt $@
if [ $? -ne 0 ]; then
    echo "Failed to submit to PBS - try again later"
    exit 1 
fi
