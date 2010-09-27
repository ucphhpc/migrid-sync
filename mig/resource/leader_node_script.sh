
# $Revision: 2326 $

debug="echo"
# Uncomment next line to enable debugging
debug=""

copy_command="$debug ${copy_command}"
move_command="$debug ${move_command}"
clean_command="$debug rm -f"
clean_recursive="${clean_command} -r"
file_move="$debug mv -f"
end_marker="### END OF SCRIPT ###"
leader_pgid="$exe.leader_pgid"
# Global work dir used by most functions
script_dir=$(dirname $0)
work_dir=$(cd $script_dir ; pwd)
empty_sleep=80

complete_file_available() {
    # a file is complete when the last line contains $end_marker .
    # this function tests whether that is the case: 
    # returns zero on success and non-zero on failure
    file="$1"
    [ -f "$file" ] || return 255
    grep "$end_marker" "$file" > /dev/null 2> /dev/null
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

clean_job() {
    localjobname="$1"
    echo "deleting .jobdone " 1>> $exehostlog 2>> $exehostlog
    $clean_command ${localjobname}.jobdone 1>> $exehostlog 2>> $exehostlog
    sync_clean ${localjobname}.jobdone
    
    echo "deleting recursive job-dir_${localjobname}" 1>> $exehostlog 2>> $exehostlog
    $clean_recursive ${work_dir}/job-dir_${localjobname} 1>> $exehostlog 2>> $exehostlog
    sync_clean ${work_dir}/job-dir_${localjobname}
    
    echo "deleting run_handle_updates.${localjobname}" 1>> $exehostlog 2>> $exehostlog
    $clean_command ${work_dir}/run_handle_updates.${localjobname} 1>> $exehostlog 2>> $exehostlog
    sync_clean ${work_dir}/run_handle_updates.${localjobname}
}

control_requests() {
    for dummyrequest in *.dummyrequest; do
        complete_file_available "$dummyrequest" || continue
      
        exe=`awk '/exeunit/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest`
        nodecount=`awk '/nodecount/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest`
        cputime=`awk '/cputime/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest`
        execution_precondition=`awk '/execution_precondition/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest`
        prepend_execute=`awk '/prepend_execute/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest`
        execution_user=`awk '/execution_user/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest`
        localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest` 
        admin_email=`awk '/admin_email/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrequest` 
        
        [ -z "$localjobname" ] && continue

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
        #echo "MiG environment settings:" >> $exehostlog
        #env|grep -E '^MIG_' >> $exehostlog

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
            #echo "testing execution delay: MIG_MAXNODES=$nodecount MIG_MAXSECONDS=$cputime MIG_SUBMITUSER=$execution_user $execution_delay_command" >> $exehostlog
            command="`eval echo ${execution_delay_command}`"
            #echo "$command" >> $exehostlog 2>> $exehostlog
            execution_delay=`$command` 2>> $exehostlog
            echo "execution delay is $execution_delay s" >> $exehostlog
        fi

        givejob=${localjobname}.givejob
        # Use dummy pgid as we do not have a pgid for the exe node yet and do not 
        # want to use leader pgid - job timeout results in a pgid kill
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
            echo "exe_pgid 0" >> $givejob &&\
            echo "$end_marker" >> $givejob
        retval=$?

        # Should this be looped ?
        if [ ! $retval -eq 0 ]; then
            echo "Writing .givejob file returned: $retval, nothing we can do, cleanup and exit 1" 1>> $exehostlog 2>> $exehostlog
            clean_job $localjobname
            cd ${work_dir}
            continue
        fi
        
        #echo "$copy_command $givejob ${copy_frontend_prefix}${frontend_dir}" >> $exehostlog
        $copy_command $givejob ${copy_frontend_prefix}${frontend_dir} >> $exehostlog 2>> $exehostlog
        retval=$?
        if [ $retval -ne 0 ]; then
            echo "ERROR copying ($retval) $givejob to frontend" >> $exehostlog
            clean_job $localjobname
            cd ${work_dir}
            continue
        fi

        cd ${work_dir}
        #echo "givejob written, wait for ${localjobname}.inputfiles_available" >> $exehostlog 2>> $exehostlog
        dummywaitinput="$exe.dummywaitinput"
        cp $dummyrequest $dummywaitinput && \
            $clean_command $dummyrequest
    done
}

control_submit() {
    for dummywaitinput in *.dummywaitinput; do
        complete_file_available "$dummywaitinput" || continue
        
        exe=`awk '/exeunit/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput`
        nodecount=`awk '/nodecount/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput`
        cputime=`awk '/cputime/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput`
        execution_precondition=`awk '/execution_precondition/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput`
        prepend_execute=`awk '/prepend_execute/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput`
        execution_user=`awk '/execution_user/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput`
        localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput` 
        admin_email=`awk '/admin_email/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitinput` 
        
        [ -z "$localjobname" ] && continue

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

        #complete_file_available "job-dir_${localjobname}/${localjobname}.inputfiles_available" || echo "$exe: $localjobname input not yet available" >> $exehostlog
        complete_file_available "job-dir_${localjobname}/${localjobname}.inputfiles_available" || continue

        force_refresh job-dir_${localjobname}

        # Now start job handling
        cd job-dir_${localjobname}

        echo "$exe: inputfiles and job script available: run job" >> $exehostlog

        # Execute script that sets environments and executes the commands from the mRSL file
        chmod +x ${localjobname}.job
        sync_complete ${localjobname}.job

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

        # Empty jobs are handled differently
        # Be careful in empty job detection to prevent potential abuse in crafted jobs
        grep "$empty_job_name" ${localjobname}.job > /dev/null 2> /dev/null
        empty_name=$?
        # Make sure that all 'EXECUTING: ' lines are pure sleeps
        grep 'EXECUTING: ' ${localjobname}.job | \
            grep -v "echo 'EXECUTING: sleep [0-9]\+'" > /dev/null 2> /dev/null
        real_cmds=$?
        if [ $empty_name -ne 0 -o $real_cmds -eq 0 ]; then 
            real_job=1
        else
            real_job=0
        fi
        #echo "DEBUG: empty job detection for $localjobname: $empty_name $real_cmds $real_job" >> $exehostlog

        command="./${localjobname}.job"
        background=0
        finish_time=0
        exe_pid=0
        exe_pgid=0
        background=1
        if [ $real_job -eq 0 ]; then
            # Do not send empty jobs through LRMS - simply run locally
            now=`date +'%s'`
            # Sleep jobs specify some slack cputime - use two thirds as a good estimate
            finish_time=$((now+2*reqcputime/3))
            echo "empty job $localjobname - just fake it (finish after $finish_time)" >> $exehostlog
        elif [ ! -z "$submit_job_command" ]; then
            # submit_job_command is only set for strict fill LRMS resources
            # We can't expect LRMS resources to accept 
            # 'submit prepend_execute job_file', so keep prepend_execute 
            # in front of submit command
            # Force MIG_X environment expansion in submit command 
            background=0
            command="`eval echo ${submit_job_command}` ${command}"
            echo "MiG submit environment settings:" >> $exehostlog
            env|grep -E '^MIG_' >> $exehostlog
            #echo "MiG submit command: $command" >> $exehostlog
            # Mark job as locally queued to avoid problems with missing liveio
            # These files will be truncated when job actually runs
            echo '(No output yet: MiG job still waiting in LRMS)' > ${MIG_JOBID}.stdout
            cat ${MIG_JOBID}.stdout > ${MIG_JOBID}.stderr
        else
            echo "run real job $localjobname in the background" >> $exehostlog
        fi
        echo "`date`: ${prepend_execute} ${command}" >> $exehostlog
        
        if [ $background -eq 1 ]; then
            # Use new subshell with redirection to limit side effects.
            # It is necessary to temporarily enable monitor mode (job control) to get
            # get a new unique PGID for the job.
            set -m
            (${prepend_execute} ${command} < /dev/null >> $joblog 2>> $joblog) &
            exe_pid=$!
            exe_pgid=`ps -o pgid= -p $exe_pid`
            # disable monitor mode again
            set +m
        else
            # LRMS submit with aggressive error handling:
            # Force immediate job failure on submit errors to give other 
            # resources a chance to execute the job instead of just waiting for
            # the potentially long job time out.
            ${prepend_execute} ${command} >> $joblog 2>> $joblog
            exec_ok=$?
            if [ $exec_ok -ne 0 ]; then
                echo "failure executing ${prepend_execute} ${command}" >> $exehostlog
                
                # clean up the job cruft and go on
                cd ${work_dir}
                clean_job $localjobname

                # request a new job right-away 
                # (will make this job fail at the server)
                $file_move "$dummywaitinput" "${exe}.dummyrequest"

                continue
            fi
        fi

        cd ${work_dir}
        
        dummywaitjob="${exe}.dummywaitjob"
        echo "localjobname $localjobname" > $dummywaitjob
        # finish time for empty jobs
        echo "finish_time $finish_time" >> $dummywaitjob
        # job PID and PGID here for fork monitor and kill support
        echo "exe_pid $exe_pid" >> $dummywaitjob
        echo "exe_pgid $exe_pgid" >> $dummywaitjob
        echo "real_job $real_job" >> $dummywaitjob
        echo "$end_marker" >> $dummywaitjob
        
        [ $real_job -eq 0 ] || touch run_handle_updates.${localjobname}

        dummywaitdone="$exe.dummywaitdone"
        echo "job_id $reqjobid" > $dummywaitdone
        cat $dummywaitinput >> $dummywaitdone && \
            $clean_command $dummywaitinput
    done
}

control_finished() {
    for dummywaitdone in *.dummywaitdone; do
        complete_file_available "$dummywaitdone" || continue
        exe=${dummywaitdone%\.dummywaitdone}
        dummywaitjob="${exe}.dummywaitjob"
        complete_file_available "$dummywaitjob" || continue
        
        exe=`awk '/exeunit/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        nodecount=`awk '/nodecount/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        cputime=`awk '/cputime/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        execution_precondition=`awk '/execution_precondition/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        prepend_execute=`awk '/prepend_execute/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        execution_user=`awk '/execution_user/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone` 
        job_id=`awk '/job_id/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone` 
        admin_email=`awk '/admin_email/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone` 

        exe_pid=`awk '/exe_pid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`
        exe_pgid=`awk '/exe_pgid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`
        real_job=`awk '/real_job/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`
        finish_time=`awk '/finish_time/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`
        
        [ -z "$localjobname" ] && continue

        # Export variables for LRMS commands to use at will
        export MIG_MAXNODES=$nodecount
        export MIG_MAXSECONDS=$cputime
        export MIG_USER=$execution_user
        export MIG_SUBMITUSER=$MIG_USER
        export MIG_EXEUNIT=$exe
        export MIG_JOBNAME="MiG_$exe"
        export MIG_LOCALJOBNAME=$localjobname
        export MIG_JOBID=$job_id
        export MIG_JOBDIR="$execution_dir/job-dir_$localjobname"
        export MIG_EXENODE=$execution_node
        export MIG_ADMINEMAIL="$admin_email"

        # Now start job monitoring
        cd job-dir_${localjobname}

        if [ $exe_pgid -gt 0 ]; then
            now=`date +'%s'`
            # echo "check if sleep job can be done using time stamp ($finish_time vs $now)" >> $exehostlog 2>> $exehostlog
            if [ $real_job -eq 0 -a $finish_time -gt $now ]; then
                # echo "don't check sleep job $localjobname yet" >> $exehostlog 2>> $exehostlog
                cd ${work_dir}
                continue
            fi
            # echo "check if background job is finished with ps" >> $exehostlog 2>> $exehostlog
            # ps does not allow PGID search - only PID or SID. 
            # Avoid prefix/suffix grep.
            proc_count=`ps -o pgid= x | awk '{ print $1; }' | egrep "^${exe_pgid}$" | wc -l`
            if [ $proc_count -gt 0 ]; then
                echo "job $localjobname not yet done ($exe_pgid: $proc_count procs)" >> $exehostlog 2>> $exehostlog
                cd ${work_dir}
                continue
            fi
        elif [ ! -z "$query_done_command" ]; then
            #echo "check if job is finished with:" >> $exehostlog 2>> $exehostlog
            # Force MIG_X environment expansion in query command 
            command="`eval echo ${query_done_command}`"
            #echo "$command" >> $exehostlog 2>> $exehostlog
            $command >> $exehostlog 2>> $exehostlog
            is_done=$?
            if [ $is_done -ne 0 ];  then 
                echo "job $localjobname not yet done ($is_done)" >> $exehostlog 2>> $exehostlog
                cd ${work_dir}
                continue
            fi
        else
            echo "unexpected job state for $localjobname in control_finished" >> $exehostlog 2>> $exehostlog
            cd ${work_dir}
            continue
        fi
        echo "`date`: job $localjobname finished" >> $exehostlog 2>> $exehostlog
        
        #echo "removing .job file" >> $exehostlog 2>> $exehostlog
        $clean_command ${localjobname}.job
        sync_clean ${localjobname}.job
        
        #echo "creating .done file" >> $exehostlog 2>> $exehostlog
        touch ${localjobname}.done

        cd ${work_dir}

        # remove dummywaitjob from work_dir
        #echo "removing waitjob file" >> $exehostlog 2>> $exehostlog
        $clean_command $dummywaitjob
        sync_clean $dummywaitjob

        dummysend="$exe.dummysend"
        cp $dummywaitdone $dummysend && \
            $clean_command $dummywaitdone
    done
}

control_results() {
    for dummysend in *.dummysend; do
        complete_file_available "$dummysend" || continue
        
        exe=`awk '/exeunit/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend`
        nodecount=`awk '/nodecount/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend`
        cputime=`awk '/cputime/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend`
        execution_precondition=`awk '/execution_precondition/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend`
        prepend_execute=`awk '/prepend_execute/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend`
        execution_user=`awk '/execution_user/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend`
        localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend` 
        job_id=`awk '/job_id/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend` 
        admin_email=`awk '/admin_email/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummysend` 

        [ -z "$localjobname" ] && continue

        # Export variables for LRMS commands to use at will
        export MIG_MAXNODES=$nodecount
        export MIG_MAXSECONDS=$cputime
        export MIG_USER=$execution_user
        export MIG_SUBMITUSER=$MIG_USER
        export MIG_EXEUNIT=$exe
        export MIG_JOBNAME="MiG_$exe"
        export MIG_LOCALJOBNAME=$localjobname
        export MIG_JOBID=$job_id
        export MIG_JOBDIR="$execution_dir/job-dir_$localjobname"
        export MIG_EXENODE=$execution_node
        export MIG_ADMINEMAIL="$admin_email"

        # Now start job handling
        cd job-dir_${localjobname}

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
        for i in 1 2 3; do
            force_refresh $user_outputfiles $system_outputfiles
            #echo "moving ($move_command) ($user_outputfiles $system_outputfiles) (${copy_frontend_prefix}${frontend_dir}/job-dir_${localjobname}/$i)" >> $exehostlog
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

        echo "job_id $job_id" > ${localjobname}.jobdone
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

        echo "sending ${localjobname}.jobdone to frontend" >> $exehostlog
        #echo "content:" >> $exehostlog
        #cat ${localjobname}.jobdone >> $exehostlog
        for i in 1 2 3; do
            #echo "$copy_command ${localjobname}.jobdone ${copy_frontend_prefix}${frontend_dir}" >> $exehostlog 2>> $exehostlog
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

        cd ${work_dir}
        $clean_command $dummysend
    done
}

control_updates() {
    for dummywaitdone in *.dummywaitdone; do
        complete_file_available "$dummywaitdone" || continue
        exe=${dummywaitdone%\.dummywaitdone}
        dummywaitjob="${exe}.dummywaitjob"
        complete_file_available "$dummywaitjob" || continue
        
        exe=`awk '/exeunit/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        nodecount=`awk '/nodecount/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        cputime=`awk '/cputime/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        execution_precondition=`awk '/execution_precondition/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        prepend_execute=`awk '/prepend_execute/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        execution_user=`awk '/execution_user/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone` 
        admin_email=`awk '/admin_email/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone` 
        
        exe_pid=`awk '/exe_pid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`
        exe_pgid=`awk '/exe_pgid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`
        real_job=`awk '/real_job/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`

        [ -z "$localjobname" ] && continue
        [ $real_job -eq 0 ] && continue
        
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

        if [ ! -f run_handle_updates.${localjobname} ]; then
            echo "updates disabled for $localjobname" 1>> $exehostlog 2>> $exehostlog
            continue
        fi

        # Now launch single update run
        cd job-dir_${localjobname}
        handle_update $localjobname
        cd ${work_dir}
    done
}


start_leader() {
    # Copy EXE_name.PGID file to frontend
    pid=$$
    pgid=`ps -o pgid= -p $pid`

    if [ -z "$pgid" -o $pgid -lt 1 ]; then
        pgid=0
    fi

    echo "exe $exe" > $leader_pgid
    echo "leader_pgid $pgid" >> $leader_pgid
    echo $end_marker >> $leader_pgid
    
    while [ 1 ]; do
        echo "$copy_command $leader_pgid ${copy_frontend_prefix}${frontend_dir}" >> $exehostlog
        $copy_command $leader_pgid ${copy_frontend_prefix}${frontend_dir} >> $exehostlog 2>> $exehostlog
        retval=$?
        if [ $retval -eq 0 ]; then
            break
        else
            echo "ERROR copying ($retval) $leader_pgid to frontend" >> $exehostlog
            sleep 8
        fi
    done
    echo "leader_pgid sent to front end" >> $exehostlog 2>> $exehostlog
    
    while [ 1 ]; do
        cd ${work_dir}
        control_finished
        sleep 1
        cd ${work_dir}
        control_results
        sleep 1
        cd ${work_dir}
        control_updates
        sleep 1
        cd ${work_dir}
        control_requests
        sleep 1
        cd ${work_dir}
        control_submit
        sleep 1
        # echo "cwd is `pwd`" >> $exehostlog
        # slow down
        sleep 15
    done
}

stop_leader() {
    if [ $# -lt 1 ]; then
        pgid=`awk '/leader_pgid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $leader_pgid`
    else
        pgid=$1
    fi
    echo "leader node stopping pgid $pgid" >> $exehostlog
    kill -n 9 -- -$pgid
    ${clean_command} $leader_pgid
    sync_clean $leader_pgid
}

status_leader() {
    if [ $# -lt 1 ]; then
        pgid=`awk '/leader_pgid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $leader_pgid`
    else
        pgid=$1
    fi
    ps -o pid= -g $pgid
}

clean_leader() {
    stop_leader $@
    script=`basename $0`
    echo "leader node stopping all $script scripts" >> $exehostlog
    killall -9 -g -e "$script"
}

### Main ###
cd ${work_dir}
echo "leader node script: $@" >> $exehostlog
status=0
cmd="$1"
shift
case "$cmd" in
    start)
        start_leader $@
        status=$?
        ;;
    stop)
        stop_leader $@
        status=$?
        ;;
    restart)
        stop_leader $@
        start_leader $@
        status=$?
        ;;
    status)
        status_leader $@
        status=$?
        ;;
    clean)
        clean_leader $@
        status=$?
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|clean}" 
        status=1
            ;;
esac
exit $status
