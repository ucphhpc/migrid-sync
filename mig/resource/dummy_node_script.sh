
# $Revision: 2326 $

clean_command="$debug rm -f"
# We don't want recursive clean up to delete mounted file systems
clean_recursive="${clean_command} -r --one-file-system"
end_marker="### END OF SCRIPT ###"

start_dummy() {
    #jobname is full date (DateMonthYear-HourMinuteSecond) with .PID appended. In that way it should be both portable and unique :)
    localjobname=`date +%d%m%y-%H%M%S`.$$

    echo "dummy node requesting local job name: ${localjobname}" >> $exehostlog
    echo "localjobname $localjobname" > $exe.dummyrunning
    echo "$end_marker" >> $exe.dummyrunning

    dummyrequest=${exe}.dummyrequest
    echo "exeunit $exe" > $dummyrequest &&\
        echo "cputime $cputime" >> $dummyrequest &&\
        echo "nodecount $nodecount" >> $dummyrequest &&\
        echo "execution_precondition $execution_precondition" >> $dummyrequest &&\
        echo "prepend_execute $prepend_execute" >> $dummyrequest &&\
        echo "execution_user $execution_user" >> $dummyrequest &&\
        echo "execution_node $execution_node" >> $dummyrequest &&\
        echo "execution_dir $execution_dir" >> $dummyrequest &&\
        echo "localjobname $localjobname" >> $dummyrequest &&\
        echo "admin_email $admin_email" >> $dummyrequest &&\
        echo "$end_marker" >> $dummyrequest
    cd
}

stop_dummy() {
    # Kill running jobs
    dummywaitjob="${exe}.dummywaitjob"
    dummywaitdone="${exe}.dummywaitdone"
    if [ -e "$dummywaitjob" ]; then
        exe_pid=`awk '/exe_pid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`
        exe_pgid=`awk '/exe_pgid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`
        localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob` 
        real_job=`awk '/real_job/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitjob`
        echo "dummy node removing $dummywaitjob" >> $exehostlog
        ${clean_command} $dummywaitjob
    fi
    if [ -e "$dummywaitdone" ]; then
        # dummywaitdone contains all job settings but we only need the request 
        # specific ones because the remaining ones are automatically added to 
        # the top of this script
        nodecount=`awk '/nodecount/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        cputime=`awk '/cputime/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone`
        localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummywaitdone` 
        # Export variables for LRMS commands to use at will
        export MIG_MAXNODES=$nodecount
        export MIG_MAXSECONDS=$cputime
        export MIG_USER=$execution_user
        export MIG_JOBDIR="$execution_dir/job-dir_$localjobname"
        echo "dummy node removing waitdone for ${localjobname}" >> $exehostlog
        ${clean_command} $dummywaitdone
    fi

    # The remaining variables are always automatically inserted by the MiG server
    export MIG_SUBMITUSER=$execution_user
    export MIG_EXEUNIT=$exe
    export MIG_EXENODE=$execution_node
    export MIG_JOBNAME="MiG_$exe"
    export MIG_ADMINEMAIL="$admin_email"
    export MIG_LOCALJOBNAME=$localjobname

    
    if [ -z "$real_job" ]; then
        echo "dummy node ignoring job without real_job value" >> $exehostlog
    elif [ $real_job -eq 0 ]; then
        echo "dummy node ignoring empty job ${localjobname}" >> $exehostlog
    elif [ ! -z "$remove_job_command" ]; then
        echo "dummy node removing job ${localjobname} with $remove_job_command" >> $exehostlog
        # Force MIG_X environment expansion in remove command 
        command="`eval echo ${remove_job_command}`"
        echo "$command" >> $exehostlog 2>> $exehostlog
        echo "MiG environment settings:" >> $exehostlog
        env|grep -E '^MIG_' >> $exehostlog
        $command >> $exehostlog 2>> $exehostlog
    elif [ ! -z "$exe_pgid" ]; then
        echo "dummy node killing job ${localjobname} with pgid $exe_pgid" >> $exehostlog
        kill -9 -$exe_pgid
    else
        echo "Warning: unexpected situation: missing job information" >> $exehostlog
        env >> $exehostlog
    fi

    dummyrunning="${exe}.dummyrunning"
    localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $dummyrunning`
    echo "dummy node cleaning up after job ${localjobname}" >> $exehostlog
    ${clean_command} $dummyrunning
    ${clean_command} run_handle_updates.${localjobname}
    ${clean_recursive} job-dir_${localjobname}
    # Remove all dummy files for this exe unit
    ${clean_command} $exe.dummy*
}

status_dummy() {
    if [ -e $exe.dummyrunning ]; then
        return 0
    else
        return 1
    fi
}

clean_dummy() {
    stop_dummy
}


### Main ###
work_dir=`dirname $0`
cd $work_dir
echo "$exe dummy node script: $@" >> $exehostlog
status=0
cmd="$1"
shift
case "$cmd" in
    start)
        start_dummy $@
        status=$?
        ;;
    stop)
        stop_dummy $@
        status=$?
        ;;
    restart)
        stop_dummy $@
        start_dummy $@
        status=$?
        ;;
    status)
        status_dummy $@
        status=$?
        ;;
    clean)
        clean_dummy $@
        status=$?
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|clean}" 
        status=1
            ;;
esac
exit $status
