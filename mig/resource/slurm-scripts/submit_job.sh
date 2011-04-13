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
    mail_opt="--mail-user=$MIG_ADMINEMAIL"
fi

# mig cputime uses seconds but sbatch uses minutes
mins=$(($MIG_JOBCPUTIME/60))
secs=$(($MIG_JOBCPUTIME%60))

sbatch --time=$mins:$secs --nodes=${MIG_JOBNODECOUNT} --mincpus=${MIG_JOBCPUCOUNT} \
    --mem=${MIG_JOBMEMORY} --no-requeue --job-name=$MIG_JOBNAME \
    -o $MIG_JOBNAME.out -e $MIG_JOBNAME.err --workdir=$MIG_JOBDIR $mail_opt $@
if [ $? -ne 0 ]; then
    echo "Failed to submit to SLURM - try again later"
    exit 1 
fi
