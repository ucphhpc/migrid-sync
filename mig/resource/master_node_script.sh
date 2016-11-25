
pid=$$
pgid=`ps -o pgid= -p $pid`
master_pgid=${exe}.pgid

debug="echo"
# Uncomment next line to enable debugging
debug=""

copy_command="$debug ${copy_command}"
move_command="$debug ${move_command}"
clean_command="$debug rm -f"
umount_command="$debug fusermount -uz"
# We don't want recursive clean up to delete mounted file systems
clean_recursive="${clean_command} -r --one-file-system"
end_marker="### END OF SCRIPT ###"


complete_file_available() {
    # a file is complete when the last line contains $end_marker .
    # this function tests whether that is the case: 
    # returns zero on success and non-zero on failure
    file="$1"
    grep "$end_marker" $file > /dev/null 2> /dev/null
    return $?
}

file_gone() {
    path="$1"
    [ ! -e "$path" ] && return 0
}

sync_disk() {
    # Call sync and log any errors
    if [ $# -gt 0 ]; then
        log="$1"
    else
        log="/dev/null"
    fi
    sync 1>> $log 2>> $log
    ret="$?"
    if [ $ret -ne '0' ]; then
        echo "sync failed with exit value ${ret}!" >> $log
    fi
    return $ret
}

# On NFS systems updates can be extremely slow because of local cache:
# http://techtavern.wordpress.com/2008/08/06/polling-files-on-nfs-shared-directories/
force_refresh() {
    # Force cache update - see above
    ls -la $@ 1> /dev/null 2> /dev/null
}

sync_complete() {
    path="$1"
    complete_file_available "$path" && return 0
    for i in 1 2 3 4 5 6 7 8 9 10; do
        sleep $((i*i))
        echo "`date`: forcing cache update to complete $path" >> $exehostlog
        force_refresh "$path"
        complete_file_available "$path" && return 0
    done
    echo "`date`: forcing disk sync to complete $path!" >> $exehostlog
    sync_disk $exehostlog
    complete_file_available "$path"
}

sync_clean() {
    # after a file or directory is removed make sure that is is gone:
    # on e.g. NFS the remove may be cached, so we do a timeout check 
    # and force sync after a while if it is still not gone.
    path="$1"
    file_gone "$path" && return 0
    for i in 1 2 3 4 5 6 7 8 9 10; do
        sleep $((i*i))
        echo "`date`: forcing cache update to clean $path" >> $exehostlog
        force_refresh "$path"
        file_gone "$path" && return 0
    done
    echo "`date`: forcing disk sync to clean $path!" >> $exehostlog
    sync_disk $exehostlog
    file_gone "$path" && return 0
    return 1
}

fuseumount_job() {
    localjobdir=$1
    jobfusemounts=`mount | grep "${localjobdir}" | awk -F' ' '{ORS=" "; print $3}'` 1>> $exehostlog 2>> $exehostlog
    
    if [ ! -z "$jobfusemounts" ]; then
        for jobmount in $jobfusemounts; do
            $umount_command $jobmount 1>> $exehostlog 2>> $exehostlog
        done
    fi
}

clean_job() {
    localjobname="$1"
    echo "deleting .jobdone " 1>> $exehostlog 2>> $exehostlog
    $clean_command ${localjobname}.jobdone 1>> $exehostlog 2>> $exehostlog
    sync_clean ${localjobname}.jobdone
    
    # Leave job dir before cleaning it (recursively removing working dir is not portable) 
    cd ${execution_dir}

    echo "unmounting fuse mounts in job-dir_${localjobname}" 1>> $exehostlog 2>> $exehostlog
    fuseumount_job ${execution_dir}/job-dir_${localjobname}

    echo "deleting recursive job-dir_${localjobname}" 1>> $exehostlog 2>> $exehostlog
    $clean_recursive ${execution_dir}/job-dir_${localjobname} 1>> $exehostlog 2>> $exehostlog
    sync_clean ${execution_dir}/job-dir_${localjobname}
    
    echo "deleting run_handle_updates.${localjobname}" 1>> $exehostlog 2>> $exehostlog
    $clean_command ${execution_dir}/run_handle_updates.${localjobname} 1>> $exehostlog 2>> $exehostlog
    sync_clean ${execution_dir}/run_handle_updates.${localjobname}
}

clean_and_exit() {
    localjobname="$1"
    exit_code=$2
    
    clean_job $localjobname
    
    echo "master_node_script.sh end, exitcode: $exit_code" >> $exehostlog
    exit $exit_code
}

handle_update() {
    localjobname=$1
        
    # any .sendupdate file available?
    sendreq="${localjobname}.sendupdate"
    if [ -f "$sendreq" ]; then
        runreq="${localjobname}.runsendupdate"
        echo "$sendreq found! Send files to frontend" 1>> $exehostlog 2>> $exehostlog
        force_refresh .
        reqjobid=`awk '/^#MIG_JOBID/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ./${localjobname}.job`
        reqsrc=`awk '/source/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ./$sendreq`
        if [ -z "$reqsrc" ]; then
            reqsrc="${reqjobid}.stdout ${reqjobid}.stderr"
        fi
        echo "$copy_command ${reqsrc} ${copy_frontend_prefix}${frontend_dir}/job-dir_${localjobname}/" >> $exehostlog
        
        $copy_command ${reqsrc} ${copy_frontend_prefix}${frontend_dir}/job-dir_${localjobname}/ >> $exehostlog 2>> $exehostlog
        retval=$?
        if [ ! $retval -eq 0 ]; then
            echo "ERROR ($retval) copying update files to frontend ${copy_frontend_prefix}${frontend_dir}/job-dir_${localjobname}/" >> $exehostlog
            echo "DEBUG: dir contents: " * >> $exehostlog
            return 1
        fi
        
        cat $sendreq > $runreq
        grep 'copy_command' $sendreq 1> /dev/null 2> /dev/null || { \
            echo "execution_user $execution_user" >> $runreq && \
            echo "execution_node $execution_node" >> $runreq && \
            echo "execution_dir $execution_dir" >> $runreq && \
            echo "copy_command $copy_command" >> $runreq && \
            echo "copy_frontend_prefix $copy_frontend_prefix" >> $runreq && \
            echo "copy_execution_prefix $copy_execution_prefix" >> $runreq && \
            echo "move_command $move_command" >> $runreq; }
        echo "$end_marker" >> $runreq
        sync_complete $runreq
        $copy_command "$runreq" ${copy_frontend_prefix}${frontend_dir}/ >> $exehostlog 2>> $exehostlog
        retval=$?
        if [ ! $retval -eq 0 ]; then
            echo "ERROR ($retval) copying $runreq to frontend ${copy_frontend_prefix}${frontend_dir}/" >> $exehostlog
            return 1
        fi
        $clean_command "$sendreq" "$runreq"
        sync_clean "$sendreq"
        sync_clean "$runreq"
    fi
    # any .getupdate file available?
    getreq="${localjobname}.getupdate"
    if [ -f "$getreq" ]; then
        runreq="${localjobname}.rungetupdate"
        echo "$getreq found! Get files from frontend" 1>> $exehostlog 2>> $exehostlog
        cat $getreq > $runreq
        grep 'copy_command' $getreq 1> /dev/null 2> /dev/null || { \
            echo "execution_user $execution_user" >> $runreq && \
            echo "execution_node $execution_node" >> $runreq && \
            echo "execution_dir $execution_dir" >> $runreq && \
            echo "copy_command $copy_command" >> $runreq && \
            echo "copy_frontend_prefix $copy_frontend_prefix" >> $runreq && \
            echo "copy_execution_prefix $copy_execution_prefix" >> $runreq && \
            echo "move_command $move_command" >> $runreq; }
        echo "$end_marker" >> $runreq
        sync_complete $runreq
        $copy_command "$runreq" ${copy_frontend_prefix}${frontend_dir}/ >> $exehostlog 2>> $exehostlog
        retval=$?
        if [ ! $retval -eq 0 ]; then
            echo "ERROR ($retval) copying $runreq to frontend ${copy_frontend_prefix}${frontend_dir}/" >> $exehostlog
            return 1
        fi
        $clean_command "$getreq" "$runreq"
        sync_clean "$getreq"
        sync_clean "$runreq"
    fi
}

handle_update_loop() {
    localjobname=$1
    loop_count=0
    while [ 1 ]; do
        if [ ! -f "${execution_dir}/run_handle_updates.${localjobname}" ]; then
            echo "exit update loop" 1>> $exehostlog 2>> $exehostlog
            exit 0
        fi
        
        handle_update $localjobname
        loop_count=$((loop_count+1))
        # slow down
        sleep 20
    done &
}


start_master() {
    # jobname is full date (DateMonthYear-HourMinuteSecond) with .PID appended.
    # In that way it should be both portable and unique :)
    localjobname=`date +%d%m%y-%H%M%S`.$$

    echo "$pgid" > $master_pgid
    # Copy EXE PGID file to frontend
    if [ -z "$pgid" -o $pgid -lt 1 ]; then
	pgid=0
    fi
    # Export variables for LRMS commands to use at will
    export MIG_MAXNODES=$nodecount
    export MIG_MAXSECONDS=$cputime
    export MIG_USER=$execution_user
    export MIG_SUBMITUSER=$MIG_USER
    export MIG_EXEUNIT=$exe
    export MIG_JOBNAME="MiG_$exe"
    export MIG_LOCALJOBNAME=$localjobname
    export MIG_JOBDIR="$execution_dir/job-dir_$localjobname"
    export MIG_EXENODE=$execution_node
    export MIG_ADMINEMAIL="$admin_email"
    export MIG_LRMS_OUT="MiG_$exe.out"
    export MIG_LRMS_ERR="MiG_$exe.err"
    echo "MiG environment settings:" >> $exehostlog
    env|grep -E '^MIG_' >> $exehostlog


    # Now start job handling
    cd ${execution_dir}
    # Ready to request job? otherwise make sure we get a sleep job
    if [ ! -z "$execution_precondition" ]; then
	# Run precondition test silently in subshell to avoid side effects
	(eval $execution_precondition) < /dev/null > /dev/null 2> /dev/null
	ret=$?
	if [ $ret -ne 0 ]; then
	    echo "Execution precondition unsatisfied ($ret) - request sleep job" >> $exehostlog
	    nodecount=0
	else
	    echo "Execution precondition satisfied - requesting job" >> $exehostlog
	fi
    fi

    echo "local job name: ${localjobname}" >> $exehostlog
    mkdir job-dir_${localjobname}
    cd job-dir_${localjobname}

    if [ -z "$execution_delay_command" ]; then
	# Simple resources can execute jobs immediately
	execution_delay=0
    else
	# LRMS resources with strict job fill must include delay estimate 
	# in job requests.
	echo "testing execution delay: MIG_MAXNODES=$nodecount MIG_MAXSECONDS=$cputime MIG_SUBMITUSER=$execution_user $execution_delay_command" >> $exehostlog
	export MIG_MAXNODES=$nodecount
	export MIG_MAXSECONDS=$cputime
	export MIG_SUBMITUSER=$execution_user
	command="`eval echo ${execution_delay_command}`"
	echo "$command" >> $exehostlog 2>> $exehostlog
	execution_delay=`$command` 2>> $exehostlog
	echo "execution delay is $execution_delay s" >> $exehostlog
    fi

    givejob=${localjobname}.givejob
    echo "exeunit $exe" > $givejob &&\
    echo "cputime $cputime" >> $givejob &&\
    echo "nodecount $nodecount" >> $givejob &&\
    echo "localjobname $localjobname" >> $givejob &&\
    echo "execution_user $execution_user" >> $givejob &&\
    echo "execution_node $execution_node" >> $givejob &&\
    echo "execution_dir $execution_dir" >> $givejob &&\
    echo "copy_command $copy_command" >> $givejob &&\
    echo "copy_frontend_prefix $copy_frontend_prefix" >> $givejob &&\
    echo "copy_execution_prefix $copy_execution_prefix" >> $givejob &&\
    echo "move_command $move_command" >> $givejob &&\
    echo "execution_delay $execution_delay" >> $givejob &&\
    echo "exe_pgid $pgid" >> $givejob &&\
    echo "$end_marker" >> $givejob
    retval=$?

    # Should this be looped ?
    if [ ! $retval -eq 0 ]; then
	echo "Writing .givejob file returned: $retval, nothing we can do, cleanup and exit 1" 1>> $exehostlog 2>> $exehostlog
	clean_and_exit $localjobname 1
    fi

    while [ 1 ]; do
	echo "$copy_command $givejob ${copy_frontend_prefix}${frontend_dir}" >> $exehostlog
	$copy_command $givejob ${copy_frontend_prefix}${frontend_dir} >> $exehostlog 2>> $exehostlog
	retval=$?
	if [ $retval -eq 0 ]; then
	    break
	else
	    echo "ERROR copying ($retval) $givejob to frontend" >> $exehostlog
	    sleep 8
	fi
    done
    echo "givejob contents:" >> $exehostlog 2>> $exehostlog
    echo cat $givejob >> $exehostlog 2>> $exehostlog
    echo "givejob written, waiting for ${localjobname}.inputfiles_available" >> $exehostlog 2>> $exehostlog
    # IMPORTANT: leave local givejob file alone for LRMS submit error handling below!

    ### Sleep until inputfiles and jobscript are available
    loop_count=0
    sync_limit=5
    while [ 1 ]; do
	if [ $loop_count -gt $sync_limit ]; then
	    # Make sure file system gets synced
	    sync_complete ${localjobname}.inputfiles_available
	fi
	complete_file_available "${localjobname}.inputfiles_available" && break
	### Files not available yet
	echo "still waiting for ${localjobname}.inputfiles_available:" >> $exehostlog 2>> $exehostlog
	ls -l >> $exehostlog 2>> $exehostlog
	sleep 10
	loop_count=$((loop_count+1))
    done

    echo "inputfiles and job script available: ready to execute job" >> $exehostlog

    ### Execute script that sets environments and executes the commands from the mRSL file
    chmod +x ${localjobname}.job >> $exehostlog 2>> $exehostlog
    echo "Files available for job: " *  >> $exehostlog 2>> $exehostlog
    sync_complete ${localjobname}.job

    force_refresh .

    echo "Transferring requested nodes, time, etc to environment" >> $exehostlog
    reqnodecount=`awk '/^#MIG_JOBNODECOUNT/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ./${localjobname}.job`
    reqcpucount=`awk '/^#MIG_JOBCPUCOUNT/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ./${localjobname}.job`
    reqcputime=`awk '/^#MIG_JOBCPUTIME/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ./${localjobname}.job`
    reqmemory=`awk '/^#MIG_JOBMEMORY/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ./${localjobname}.job`
    reqdisk=`awk '/^#MIG_JOBDISK/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ./${localjobname}.job`
    reqjobid=`awk '/^#MIG_JOBID/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ./${localjobname}.job`
    export MIG_JOBNODES=$reqnodecount
    export MIG_JOBSECONDS=$reqcputime
    export MIG_JOBNODECOUNT=$reqnodecount
    export MIG_JOBCPUCOUNT=$reqcpucount
    export MIG_JOBCPUTIME=$reqcputime
    export MIG_JOBMEMORY=$reqmemory
    export MIG_JOBDISK=$reqdisk
    export MIG_JOBID=$reqjobid

    # Empty jobs should be handled differently on strict fill LRMS resources
    # Be careful in empty job detection to prevent potential abuse in crafted jobs
    grep "$empty_job_name" ${localjobname}.job > /dev/null 2> /dev/null
    empty_name=$?
    # Make sure that all 'EXECUTING: ' lines are pure sleeps
    grep 'EXECUTING: ' ${localjobname}.job | \
	grep -v "echo 'EXECUTING: sleep [0-9]\+'" > /dev/null 2> /dev/null
    real_cmds=$?
    if [ $empty_name -ne 0 -o $real_cmds -eq 0 ]; then 
	real_job=1
	touch "${execution_dir}/run_handle_updates.${localjobname}"
    else
	real_job=0
    fi

    command="./${localjobname}.job"
    # submit_job_command is only set for strict fill LRMS resources
    if [ ! -z "$submit_job_command" ]; then
	# Do not send empty jobs through LRMS - simply run them locally:
	# This can potentially allow DoS attacks with specially crafted jobs!
	if [ $real_job -eq 1 ]; then
	    # We can't expect LRMS resources to accept 
	    # 'submit prepend_execute job_file', so keep prepend_execute 
	    # in front of submit command
	    # Force MIG_X environment expansion in submit command 
	    command="`eval echo ${submit_job_command}` ${command}"
	    echo "MiG submit environment settings:" >> $exehostlog
	    env|grep -E '^MIG_' >> $exehostlog
	    # Mark job as locally queued to avoid problems with missing liveio
	    # These files will be truncated when job actually runs
	    echo '(No output yet: MiG job still waiting in LRMS)' > ${MIG_JOBID}.stdout
	    cat ${MIG_JOBID}.stdout > ${MIG_JOBID}.stderr
	else
	    echo "empty job: running ${command} locally" >> $exehostlog
	fi
    fi
    handle_update_loop $localjobname

    # LRMS submit with aggressive error handling:
    # Force immediate job failure on submit errors to give other 
    # resources a chance to execute the job instead of just waiting for
    # the potentially long job time out.
    #echo "run with job dir contents: `ls`" >> $exehostlog
    echo "`date`: ${prepend_execute} ${command}" >> $exehostlog
    ${prepend_execute} ${command} >> $joblog 2>> $joblog
    exec_ok=$?
    if [ $exec_ok -ne 0 ]; then
	echo "failure executing ${prepend_execute} ${command}" >> $exehostlog
	echo "requesting new job to force immediate job retry" >> $exehostlog
	$copy_command $givejob ${copy_frontend_prefix}${frontend_dir} >> $exehostlog 2>> $exehostlog
	# We will get a sleep job so we can just exit and let job time out
	# handling take care of restart and clean up after that one
	clean_and_exit $localjobname 1
    fi

    # Simple resources only get here after job is done, but strict fill
    # LRMS resources just submitted job here - must wait for job to finish
    if [ ! -z "$query_done_command" ]; then
	if [ $real_job -eq 1 ]; then
	    echo "waiting for job to finish" >> $exehostlog 2>> $exehostlog
	    # Many jobs fail within the first few seconds - catch them quickly
	    sleep 10
	    while [ 1 ]; do
		# Force MIG_X environment expansion in query command 
		command="`eval echo ${query_done_command}`"
		echo "$command" >> $exehostlog 2>> $exehostlog
		$command >> $exehostlog 2>> $exehostlog
		is_done=$?
		if [ $is_done -ne 0 ];  then 
		    echo "not yet done ($is_done)" >> $exehostlog 2>> $exehostlog
		    sleep 60
		else
		    break
		fi
	    done
	    echo "`date`: job finished" >> $exehostlog 2>> $exehostlog
	fi
    fi

    echo "removing .job file" >> $exehostlog 2>> $exehostlog
    $clean_command ${localjobname}.job
    sync_clean ${localjobname}.job

    # Transfer user outputfiles to frontend, files that do not exist are ignored.
    user_outputfiles=""
    for file in `cat ${localjobname}.user.outputfiles 2>> $exehostlog`; do
       if [ -e "$file" ]; then
	  user_outputfiles="$user_outputfiles $file"
       fi
    done   

    # Transfer system outputfiles to frontend.
    system_outputfiles=`cat ${localjobname}.system.outputfiles 2>> $exehostlog`
    echo "send output files (" $user_outputfiles $system_outputfiles ") to frontend" >> $exehostlog
    while [ 1 ]; do
       force_refresh $user_outputfiles $system_outputfiles
       echo "moving ($move_command) ($user_outputfiles $system_outputfiles) (${copy_frontend_prefix}${frontend_dir}/job-dir_${localjobname}/$i)" >> $exehostlog
       $move_command $user_outputfiles $system_outputfiles ${copy_frontend_prefix}${frontend_dir}/job-dir_${localjobname}/ >> $exehostlog 2>> $exehostlog
       retval=$?
       if [ $retval -eq 0 ]; then
	  break
       else
	  echo "ERROR ($retval) transfering system_outputfiles to frontend ${copy_frontend_prefix}${frontend_dir}/job-dir_${localjobname}/" >> $exehostlog
	  echo "DEBUG: dir contents: " * >> $exehostlog
	  sleep 9
       fi
    done

    echo "job_id $reqjobid" > ${localjobname}.jobdone
    echo "exeunit $exe" >> ${localjobname}.jobdone
    echo "cputime $cputime" >> ${localjobname}.jobdone
    echo "nodecount $nodecount" >> ${localjobname}.jobdone
    echo "localjobname $localjobname" >> ${localjobname}.jobdone
    echo "execution_user $execution_user" >> ${localjobname}.jobdone
    echo "execution_node $execution_node" >> ${localjobname}.jobdone
    echo "execution_dir $execution_dir" >> ${localjobname}.jobdone
    echo "copy_command $copy_command" >> ${localjobname}.jobdone
    echo "copy_frontend_prefix $copy_frontend_prefix" >> ${localjobname}.jobdone
    echo "copy_execution_prefix $copy_execution_prefix" >> ${localjobname}.jobdone
    echo "move_command $move_command" >> ${localjobname}.jobdone
    echo "execution_delay $execution_delay" >> ${localjobname}.jobdone
    echo "exe_pgid $pgid" >> ${localjobname}.jobdone
    echo "$end_marker" >> ${localjobname}.jobdone
    sync_complete ${localjobname}.jobdone
    echo "sending localjobname.jobdone to frontend" >> $exehostlog
    echo "content:" >> $exehostlog
    cat ${localjobname}.jobdone >> $exehostlog
    while [ 1 ]; do
	echo "$copy_command ${localjobname}.jobdone ${copy_frontend_prefix}${frontend_dir}" >> $exehostlog 2>> $exehostlog
	$copy_command ${localjobname}.jobdone ${copy_frontend_prefix}${frontend_dir} >> $exehostlog 2>> $exehostlog
	retval=$?
	if [ $retval -eq 0 ]; then
	    break
	else
	    echo "ERROR ($retval) copying jobdone to frontend" >> $exehostlog
	    sleep 10
	fi
    done

    clean_job $localjobname
}

stop_master() {
    if [ $# -lt 1 ]; then
        pgid=`cat $master_pgid`
    else
        pgid=$1
    fi
    echo "master node stopping pgid $pgid" >> $exehostlog
    kill -n 9 -- -$pgid
    ${clean_command} $master_pgid
    sync_clean $master_pgid
}

status_master() {
    if [ $# -lt 1 ]; then
        pgid=`cat $master_pgid`
    else
        pgid=$1
    fi
    ps -o pid= -g $pgid
}

clean_master() {
    stop_master $@
    script=`basename $0`
    echo "master node stopping all $script scripts" >> $exehostlog
    killall -9 -g -e "$script"
}

### Main ###
cd ${execution_dir}
echo "master node script: $@" >> $exehostlog
status=0
cmd="$1"
shift
case "$cmd" in
    start)
        start_master $@
        status=$?
        ;;
    stop)
        stop_master $@
        status=$?
        ;;
    restart)
        stop_master $@
        start_master $@
        status=$?
        ;;
    status)
        status_master $@
        status=$?
        ;;
    clean)
        clean_master $@
        status=$?
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|clean}" 
        status=1
            ;;
esac
exit $status
