echo "`date`: starting" >> $frontendlog

# Make sure sandboxes use the current MiG server when booted next time.
# This is a workaround after our server migration, so that existing 
# images can continue working as long as we redirect or proxy sandboxes 
# to the new server at least once.

if [ $sandbox -eq 1 ]; then
    echo $migserver > /opt/mig/etc/serverfile
fi

# $Revision: 2580 $

clean_command="rm -f"
# We don't want recursive clean up to delete mounted file systems
clean_recursive="$clean_command -r --one-file-system"
# if changing end_marker string, remember to change in the other scripts
# (master_node_script and cgi-scripts on MiG server)
end_marker="### END OF SCRIPT ###"
# Don't run expensive clean up to often - interval is number of loops (> 1s each)
clean_up_counter=0
# Clean up after this many loops (with 2 second idle sleep this is less than once a day)
clean_up_interval=43200
# Timeout for sandboxes is checked by frontend
# Don't check for timeout to often - interval is number of loops (> 1s each)
# The initial value is 60 for responsiveness, but as sandbox resources increase 
# in numbers the timeout_interval should be increased.
sandbox_timeout_counter=0
sandbox_timeout_interval=60

send_pgid() {
    type=$1
    pgid=$2
    contimeout=20
    
    # TODO: can we supply ca-cert to avoid insecure here?
    command="curl --location --insecure --stderr $curllog --connect-timeout $contimeout -m $contimeout $migserver/cgi-sid/put_resource_pgid?type=$type&amp;unique_resource_name=${unique_resource_name}&amp;pgid=$pgid"
    
    if [ "$type" = "EXE" ]; then
        exe=$3
        command="$command&amp;exe_name=$exe"
    fi
    
    echo $command >> $frontendlog
    status=`$command`
    retval=$?
    echo "" >> $frontendlog
    echo "send_pgid result: $status ($retval)" >> $frontendlog
    
    # return only exit_code
    return ${status:0:1}
}

#echo is one of the least portable commands on Unix.
#On every POSIX system, you'll find a "printf" command (often
#builtin) that's supposed to replace echo.
#http://www.issociate.de/board/post/169622/Bash_echo_issues.html

echo() {
    [ $# -gt 0 ] && printf "%b" "$1"
    shift
    while [ "$#" -gt 0 ]; do
        printf " %b" "$1";
        shift;
    done
    printf '\n'
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

execute_transfer_files_script(){
    localjobname=$1
    filesuffix=$2
    shift; shift
    
    if [ ! -f ${localjobname}.${filesuffix} ]; then
        echo "${localjobname}.${filesuffix} not found!"
        return
    fi
    
    echo "Transfer files for ${localjobname} ${filesuffix}:" * 1>> $frontendlog 2>> $frontendlog
    chmod +x ${localjobname}.${filesuffix} 1>> $frontendlog 2>> $frontendlog
    
    # Retries kept low due to automatic retry later
    sendoutput_tries=3
    sent_output=0
    for i in `seq 1 $sendoutput_tries`; do
        # execute $localjobname$.{filesuffix}
        echo "executing ${localjobname}.${filesuffix} $@" 1>> $frontendlog 2>> $frontendlog
        
        ./${localjobname}.${filesuffix} $@ 1>> $frontendlog 2>> $frontendlog
        
        send_ret=$?
        if [ $send_ret -eq 0 ]; then
            echo "${filesuffix} for $localjobname ok ($send_ret)" 1>> $frontendlog 2>> $frontendlog
            sent_output=1
            break
        else
            # try again later
            echo "${filesuffix} RETURNED NON-SUCCESFUL ($send_ret)" 1>> $frontendlog 2>> $frontendlog
            sleep 7
        fi
    done

    if [ $sent_output -eq 0 ]; then
        echo "ERROR: ${filesuffix} failed: saving sendoutput for debugging" 1>> $frontendlog 2>> $frontendlog
        cp -dpR ${localjobname}.${filesuffix} ../${localjobname}.${filesuffix}.FAILED 1>> $frontendlog 2>> $frontendlog
    fi
}

complete_file_available() {
    # a file is complete when the last line contains $end_marker .
    # this function tests whether that is the case: 
    # returns zero on success and non-zero on failure
    path="$1"
    [ -f "$path" ] || return 255
    grep "$end_marker" "$path" > /dev/null 2> /dev/null
    return $?
}

file_gone() {
    path="$1"
    [ ! -e "$path" ]
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
        echo "`date`: forcing cache update to complete $path" >> $frontendlog
        force_refresh "$path"
        complete_file_available "$path" && return 0
    done
    echo "`date`: forcing disk sync to complete $path!" >> $frontendlog
    sync_disk $frontendlog
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
        echo "`date`: forcing cache update to clean $path" >> $frontendlog
        force_refresh "$path"
        file_gone "$path" && return 0
    done
    echo "`date`: forcing disk sync to clean $path!" >> $frontendlog
    sync_disk $frontendlog
    file_gone "$path" && return 0
    return 1
}

request_job() {
    sleepsuntilrerequest=25
    sync_freq=6
    contimeout=20
    
    exe="$1"
    nodecount="$2"
    cputime="$3"
    localjobname="$4"
    execution_delay="$5"
    exe_pgid="$6"
    
    # if sandbox also send sandboxkey
    #sandboxkey_string=""
    #if [ $sandbox -eq 1 ]; then
      #sandboxkey_string="\&amp\;sandboxkey=${sandboxkey}"
    #fi
    
    # request a new job, and check a number of times if it is received. If not a
    # request is sent again
    retry_counter=0
    max_retries=5
    while [ 1 ]; do
        retry_counter=$((retry_counter+1))
        # TODO: can we supply ca-cert to avoid insecure here?
        curl --location --insecure --stderr $curllog --connect-timeout $contimeout -m $contimeout $migserver/cgi-sid/requestnewjob?exe=${exe}\&amp\;unique_resource_name=${unique_resource_name}\&amp\;cputime=${cputime}\&amp\;nodecount=${nodecount}\&amp\;sandboxkey=${sandboxkey}\&amp\;localjobname=${localjobname}\&amp\;execution_delay=${execution_delay}\&amp\;exe_pgid=${exe_pgid} 1>> $frontendlog 2>> $frontendlog
        retval=$?
        echo "a new job ${exe} ${nodecount} ${cputime} ${localjobname} ${execution_delay} ${exe_pgid} was requested ($retval)" 1>> $frontendlog 2>> $frontendlog
        
        if [ $sandbox -eq 1 ]; then
            getinputfiles_retry=0
            getinputfiles_max_retries=5
            while [ ! -f ${localjobname}.getinputfiles ] && \
                [ $getinputfiles_retry -lt $getinputfiles_max_retries ]; do
                curl --location --fail --insecure --stderr $curllog --connect-timeout $contimeout -m $contimeout $migserver/sid_redirect/${localjobname}.getinputfiles -o ${localjobname}.getinputfiles 1>> $frontendlog 2>> $frontendlog
                retval=$?
                # Loop until .getinputfiles is ready, curl returns 0,
                # --fail must be set on curl command to do this, see 
                # man curl
                if [ "$retval" -ne "0" ]; then
                    getinputfiles_retry=$((getinputfiles_retry+1))
                    ${clean_command} ${localjobname}.getinputfiles
                    echo ".getinputfiles script _NOT_ received yet ($retval)! (${getinputfiles_retry}/${getinputfiles_max_retries})" 1>> $frontendlog 2>> $frontendlog
                    sleep 5
                fi
            done
            if [ $getinputfiles_retry -eq $getinputfiles_max_retries ]; then
                echo "No more request retries left!" 1>> $frontendlog 2>> $frontendlog
                return 1
            fi
        fi
        
        # loop until new job exists or timeout is reached
        counter=0
        while [ 1 ]; do
            counter=$((counter+1))
            complete_file_available ${localjobname}.getinputfiles && return 0
            echo "file ${localjobname}.getinputfiles not (fully?) received yet - sleeping" 1>> $frontendlog 2>> $frontendlog
            # Increase sleep length with each try
            sleep $counter
            if [ $counter -eq $sleepsuntilrerequest ]; then
                echo `date` "REREQUESTING! " 1>> $frontendlog 2>> $frontendlog
                break
            fi
            # Sync every sync_freq'th time we get here
            if [ $((counter%sync_freq)) -eq 0 ]; then
                # make sure that server scp of files gets written
                echo "waiting for ${localjobname}.getinputfiles to settle ($counter)" 1>> $frontendlog 2>> $frontendlog
                sync_complete ${localjobname}.getinputfiles
            fi
        done
        
        if [ $retry_counter -eq $max_retries ]; then
            echo "No more request retries left!" 1>> $frontendlog 2>> $frontendlog
            return 1
        fi
    done
    return 0
}

sandbox_stop_exe() {
    # Find newest job_dir, and generete list of old job_dirs
    # NOTE: Sandboxes only has one executionnode, if that's changed,
    #       we must find and check a newest jobdir for each executionnode
    newest_job_dir=""
    job_clean_list=""
    for job_dir in job-dir_*; do
        if [ -z $newest_job_dir ] || [ $job_dir -nt $newest_job_dir ]; then
            newest_job_dir=$job_dir
            job_clean_list="$job_clean_list $job_dir"
        fi
    done
    
    localjobname=${newest_job_dir#job-dir_}
    if [ ! -f ${localjobname}.jobdone ] && \
        [ -f ${newest_job_dir}/${localjobname}.iosessionid ] && \
        [ -f ${newest_job_dir}/${localjobname}.executionnode ]; then
        iosessionid=`cat ${newest_job_dir}/${localjobname}.iosessionid  2>> $frontendlog`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ${newest_job_dir}/${localjobname}.executionnode`
        
        # Check if newest_job is still active, if not issue the stop command returned by the MiG server
        command="curl --location --insecure --stderr $curllog --connect-timeout 10 -m 10 $migserver/cgi-sid/isjobactive.py"
        command="${command}?iosessionid=${iosessionid}&sandboxkey=${sandboxkey}&exe_name=${execution_node}"
        status=`$command  2>> $frontendlog`
        retval=$?
        if [ $retval -eq 0 ] &&\
            [ ${status:0:1} -eq 1 ]; then
            stop_command=`echo ${status:2} | awk -F'stop_command: ' '{print $2}'`
            if [ ! -z "$stop_command" ]; then
                # Execute stop command                  
                $stop_command 1>> $frontendlog 2>> $frontendlog
                retval=$?
                echo "sandbox_stop_exe: (${stop_command}) of job ($localjobname) returned (${retval})" 1>> $frontendlog 2>> $frontendlog
                
                # Cleanup files for the killed job and jobs older than the killed job
                if [ $retval -eq 0 ]; then
                    for job_dir_clean in $job_clean_list; do
                        localjobname_clean=${job_dir_clean#job-dir_}
                        
                        # Remove EXE jobdir 
                        ${clean_recursive} ${copy_execution_prefix}${execution_dir}/${job_dir_clean} 1>> $frontendlog 2>> $frontendlog
                        
                        # Remove run_handle_updates
                        $clean_command ${copy_execution_prefix}${execution_dir}/run_handle_updates.${localjobname_clean}\
                            1>> $frontendlog 2>> $frontendlog 
                        
                        # Remove FE jobdir
                        ${clean_recursive} $job_dir_clean 1>> $frontendlog 2>> $frontendlog
                        
                        # Remove jobdone, we can't trust it at this stage
                        ${clean_command} ${localjobname_clean}.jobdone 1>> $frontendlog 2>> $frontendlog
                        
                        echo "sandbox_stop_exe: Job ($localjobname_clean) was cleand up" 1>> $frontendlog 2>> $frontendlog
                        sync_clean ${localjobname_clean}.jobdone
                    done
                fi
            fi
        fi
    fi
}

### MAIN ###

# Send the frontend ProcessGroupID to the MiG server.
pid=$$
pgid=`ps -o pgid= -p $pid`
# Sandboxes don't send pgid
if [ $sandbox -eq 0 ]; then
    send_pgid "FE" $pgid
    retval=$?
    if [ $retval -ne 0 ]; then
        exit 1
    fi
fi

# Loop through job handling forever
while [ 1 ]; do
    # Send leader PGIDs (leaders don't request jobs, so no givejob)
    for pgidfile in *.leader_pgid; do
        # No matching expansion results in raw pattern value - just 
        # ignore
        if [ "$pgidfile" = '*.leader_pgid' ]; then
            continue
        fi
        
        # Now make sure file was fully transferred
        complete_file_available "$pgidfile" || continue
        
        exe=`awk '/exe/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $pgidfile`
        leader_pgid=`awk '/leader_pgid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $pgidfile`
        send_pgid "EXE" $leader_pgid $exe
        ${clean_command} $pgidfile
        sync_clean $pgidfile
    done
    
    # SEND OUTPUTFILES
    for jobdone in *.jobdone; do
        # No matching expansion results in raw pattern value - just 
        # ignore
        if [ "$jobdone" = '*.jobdone' ]; then
            continue
        fi
        
        # Now make sure file was fully transferred
        complete_file_available "$jobdone" || continue
        
        # Try to force disk flush - outputfiles *must* be written 
        # before jobname.sendoutput is executed
        force_refresh "job-dir_${localjobname}"
        
        # localjobname is filename without .done
        localjobname=${jobdone%\.jobdone}
        
        echo "Sending outputfiles for job with localjobname: $localjobname" 1>> $frontendlog 2>> $frontendlog 
        if [ -d job-dir_${localjobname} ]; then
            cd job-dir_${localjobname} 1>> $frontendlog 2>> $frontendlog
            
            reqjobid=`awk '/job_id/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' ../${localjobname}.jobdone`
            reqtarget="result"
            reqsrc="${reqjobid}.stdout ${reqjobid}.stderr"
            reqdst="/job_output/${reqjobid}"

            execute_transfer_files_script $localjobname "sendoutputfiles" $reqtarget $reqsrc $reqdst
            
            #echo "removing ${localjobname}.sendoutputfiles" 1>> $frontendlog 2>> $frontendlog
            $clean_command ${localjobname}.sendoutputfiles
            sync_clean ${localjobname}.sendoutputfiles
            #echo "removing ${localjobname}.sendupdatefiles" 1>> $frontendlog 2>> $frontendlog
            $clean_command ${localjobname}.sendupdatefiles
            sync_clean ${localjobname}.sendupdatefiles
            cd ..
        else
            echo "dir job-dir_${localjobname} containing ${localjobname}.sendoutputfiles does not exists!"
        fi
        
        #echo "deleting file ${localjobname}.jobdone and directory job-dir_${localjobname}" >> $frontendlog
        $clean_command ${localjobname}.jobdone 
        $clean_recursive job-dir_${localjobname}
        sync_clean ${localjobname}.jobdone
        sync_clean job-dir_${localjobname}
    done
    
    # Send updatefiles
    for runrequest in *.runsendupdate; do
        # No matching expansion results in raw pattern value - just 
        # ignore
        if [ "$runrequest" = '*.runsendupdate' ]; then
            continue
        fi
        
        # Now make sure file was fully transferred
        complete_file_available "$runrequest" || continue
        
        # Try to force disk flush - updatefiles *must* be written 
        # before jobname.sendupdatefiles is executed
        force_refresh "job-dir_${localjobname}"
        
        # localjobname is filename without extension
        localjobname=${runrequest%\.runsendupdate}
        execution_user=`awk '/execution_user/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        exe_copy_command=`awk '/copy_command/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        exe_copy_execution_prefix=`awk '/copy_execution_prefix/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        exe_move_command=`awk '/move_command/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        echo "from $runrequest read values $localjobname $execution_user $execution_node $execution_dir $exe_copy_command $exe_copy_execution_prefix $exe_move_command" 1>> $frontendlog 2>> $frontendlog
        # Override copy command and exe prefix if specified by exehost
        if [ -z "$exe_copy_command" ]; then
            # Fallback to legacy setup
            copy_command="scp -B"
            copy_execution_prefix="${execution_user}@${execution_node}:"
        else
            copy_command="$exe_copy_command"
            copy_execution_prefix="$exe_copy_execution_prefix"
        fi
        reqjobid=`awk '/job_id/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        reqtarget=`awk '/target/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        reqsrc=`awk '/source/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        reqdst=`awk '/destination/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        if [ -z "$reqtarget" ]; then
            reqtarget="liveio"
        fi
        if [ "$reqtarget" = 'liveio' ]; then
            if [ -z "$reqsrc" ]; then
		reqsrc="${reqjobid}.stdout ${reqjobid}.stderr ${reqjobid}.io-status"
            fi
            if [ -z "$reqdst" ]; then
                reqdst="/job_output/${reqjobid}"
            fi
        fi
        
        requestdone="${localjobname}.sendupdatedone"

        echo "Executing sendupdatefiles for job with localjobname: $localjobname" 1>> $frontendlog 2>> $frontendlog
        
        if [ -d job-dir_${localjobname} ]; then
            cd job-dir_${localjobname} 1>> $frontendlog 2>> $frontendlog
            execute_transfer_files_script $localjobname "sendupdatefiles" $reqtarget $reqsrc $reqdst
            cd ..
            echo "forwarding $runrequest done signal to exe" 1>> $frontendlog 2>> $frontendlog
            $copy_command $runrequest ${copy_execution_prefix}${execution_dir}/job-dir_${localjobname}/$requestdone 1>> $frontendlog 2>> $frontendlog
            available_ret=$?
            if [ $available_ret -ne 0 ]; then
                echo "send of $requestdone signal failed ($available_ret)" 1>> $frontendlog 2>> $frontendlog
            fi
        else
            echo "dir job-dir_${localjobname} containing ${localjobname}.sendupdatefiles does not exists!"
        fi

        #echo "deleting file $runrequest" >> $frontendlog
        $clean_command $runrequest
        sync_clean $runrequest
    done
    
    # Get updatefiles
    for runrequest in *.rungetupdate; do
        # No matching expansion results in raw pattern value - just 
        # ignore
        if [ "$runrequest" = '*.rungetupdate' ]; then
            continue
        fi
        
        # Now make sure file was fully transferred
        complete_file_available "$runrequest" || continue
        
        localjobname=${runrequest%\.rungetupdate}
        execution_user=`awk '/execution_user/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        exe_copy_command=`awk '/copy_command/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        exe_copy_execution_prefix=`awk '/copy_execution_prefix/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        exe_move_command=`awk '/move_command/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        echo "from $runrequest read values $localjobname $execution_user $execution_node $execution_dir $exe_copy_command $exe_copy_execution_prefix $exe_move_command" 1>> $frontendlog 2>> $frontendlog
        # Override copy command and exe prefix if specified by exehost
        if [ -z "$exe_copy_command" ]; then
            # Fallback to legacy setup
            copy_command="scp -B"
            copy_execution_prefix="${execution_user}@${execution_node}:"
        else
            copy_command="$exe_copy_command"
            copy_execution_prefix="$exe_copy_execution_prefix"
        fi
        # Override move command and exe prefix if specified by exehost
        if [ -z "$exe_move_command" ]; then
            # Fallback to legacy setup
            move_command="scp -B -r"
        else
            move_command="$exe_move_command"
        fi

        reqtarget=`awk '/target/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        reqsrc=`awk '/source/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        reqdst=`awk '/destination/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $runrequest`
        if [ -z "$reqtarget" ]; then
            reqtarget="liveio"
        fi
        requestdone="${localjobname}.getupdatedone"

        echo "Executing getupdatefiles for job with localjobname: $localjobname" 1>> $frontendlog 2>> $frontendlog
        
        if [ -d job-dir_${localjobname} ]; then
            cd job-dir_${localjobname} 1>> $frontendlog 2>> $frontendlog
            tmpbase="updatetmp"
            tmpdst="$tmpbase/$reqdst"
            mkdir -p "$tmpdst"
            execute_transfer_files_script $localjobname "getupdatefiles" $reqtarget $reqsrc $tmpdst

            # Try to force disk flush - updatefiles *must* be written 
            # before forwarding to exe
            force_refresh $tmpdst

            echo "moving getupdate files to exe" 1>> $frontendlog 2>> $frontendlog
            cd $tmpbase
            $move_command * ${copy_execution_prefix}${execution_dir}/job-dir_${localjobname}/ 1>> $frontendlog 2>> $frontendlog
            available_ret=$?
            if [ $available_ret -ne 0 ]; then
                echo "copy of $runrequest files failed ($available_ret)" 1>> $frontendlog 2>> $frontendlog
            fi
            cd ..
            $clean_recursive $tmpbase
            sync_clean $tmpbase
            cd ..
            echo "forwarding $runrequest done signal to exe" 1>> $frontendlog 2>> $frontendlog
            $copy_command $runrequest ${copy_execution_prefix}${execution_dir}/job-dir_${localjobname}/$requestdone 1>> $frontendlog 2>> $frontendlog
            available_ret=$?
            if [ $available_ret -ne 0 ]; then
                echo "send of $requestdone signal failed ($available_ret)" 1>> $frontendlog 2>> $frontendlog
            fi
        else
            echo "dir job-dir_${localjobname} containing ${localjobname}.getupdatefiles does not exists!"
        fi

        #echo "deleting file $runrequest" >> $frontendlog
        $clean_command $runrequest
        sync_clean $runrequest
    done
    
    # Forward update requests to exe
    for updaterequest in *.sendupdate *.getupdate; do
        # No matching expansion results in raw pattern value - just 
        # ignore
        if [ "$updaterequest" = '*.sendupdate' -o "$updaterequest" = '*.getupdate' ]; then
            continue
        fi
        # ignore partial update requests
        complete_file_available $updaterequest || continue
        echo "update found $updaterequest" 1>> $frontendlog 2>> $frontendlog
        
        job_id=`awk '/job_id/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $updaterequest`
        localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $updaterequest`
        execution_user=`awk '/execution_user/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $updaterequest`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $updaterequest`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $updaterequest`
        exe_copy_command=`awk '/copy_command/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $updaterequest`
        exe_copy_execution_prefix=`awk '/copy_execution_prefix/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $updaterequest`
        echo "from $updaterequest read values $job_id $localjobname $execution_user $execution_node $execution_dir $exe_copy_command $exe_copy_execution_prefix" 1>> $frontendlog 2>> $frontendlog
        # Override copy command and exe prefix if specified by exehost
        if [ -z "$exe_copy_command" ]; then
            # Fallback to legacy setup
            copy_command="scp -B"
            copy_execution_prefix="${execution_user}@${execution_node}:"
        else
            copy_command="$exe_copy_command"
            copy_execution_prefix="$exe_copy_execution_prefix"
        fi
        echo "forwarding $updaterequest signal to exe" 1>> $frontendlog 2>> $frontendlog
        while [ 1 ]; do 
            $copy_command $updaterequest ${copy_execution_prefix}${execution_dir}/job-dir_${localjobname} 1>> $frontendlog 2>> $frontendlog
            available_ret=$?
            if [ $available_ret -eq 0 ]; then
                #echo "copy of $updaterequest went ok ($available_ret)" 1>> $frontendlog 2>> $frontendlog
                break
            else
                # continue until succesful
                echo "copy of $updaterequest failed ($available_ret)" 1>> $frontendlog 2>> $frontendlog
                sleep 13
            fi
        done
        #echo "deleting $updaterequest" 1>> $frontendlog 2>> $frontendlog
        $clean_command $updaterequest
        sync_clean $updaterequest
    done
    
    ### REQUEST A NEW JOB ###
    # if givejob exists, we must request a new job (and delete 
    # "givejob")
    for givejobrequest in *.givejob; do
        # No matching expansion results in raw pattern value - just 
        # ignore
        if [ "$givejobrequest" = '*.givejob' ]; then
            continue
        fi
        
        # ignore partial job requests
        complete_file_available $givejobrequest || continue
        #echo "givejob found $givejobrequest" 1>> $frontendlog 2>> $frontendlog
        
        exe=`awk '/exeunit/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        nodecount=`awk '/nodecount/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        cputime=`awk '/cputime/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        localjobname=`awk '/localjobname/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest` 
        execution_user=`awk '/execution_user/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        execution_node=`awk '/execution_node/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        execution_dir=`awk '/execution_dir/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        exe_copy_command=`awk '/copy_command/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        exe_copy_frontend_prefix=`awk '/copy_frontend_prefix/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        exe_copy_execution_prefix=`awk '/copy_execution_prefix/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        exe_move_command=`awk '/move_command/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        execution_delay=`awk '/execution_delay/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        exe_pgid=`awk '/exe_pgid/ {ORS=" " ; for(field=2;field<NF;++field) print $field; ORS=""; print $field}' $givejobrequest`
        
        
        echo "$givejobrequest values: $exe $nodecount $cputime $localjobname $execution_user $execution_node $execution_dir $exe_copy_command $exe_copy_frontend_prefix $exe_copy_execution_prefix $exe_move_command $execution_delay $exe_pgid" 1>> $frontendlog 2>> $frontendlog
        
        
        # Override copy command and exe prefix if specified by exehost
        if [ -z "$exe_copy_command" ]; then
            # Fallback to legacy setup
            copy_command="scp -B"
            copy_execution_prefix="${execution_user}@${execution_node}:"
        else
            copy_command="$exe_copy_command"
            copy_execution_prefix="$exe_copy_execution_prefix"
        fi
        
        # Override move command and exe prefix if specified by exehost
        if [ -z "$exe_move_command" ]; then
            # Fallback to legacy setup
            move_command="scp -B -r"
        else
            move_command="$exe_move_command"
        fi
        
        echo `date` "requesting job ($localjobname) from MiG server" 1>> $frontendlog 2>> $frontendlog
        request_job "$exe" "$nodecount" "$cputime" "$localjobname" "$execution_delay" "$exe_pgid"
        got_job=$?
        if [ $got_job -ne 0 ]; then
            echo `date` "request job failed for $localjobname - delay handling of job" 1>> $frontendlog 2>> $frontendlog
            sleep 2
            continue
        fi
        
        # job has arrived: $localjobname.getinputfiles file is available
        #echo "making directory job-dir_$localjobname" 1>> $frontendlog 2>> $frontendlog
        mkdir job-dir_$localjobname 1>> $frontendlog 2>> $frontendlog
        
        # Write execution_node to job_dir (This used by sandbox timeout/kill)
        echo "execution_node ${execution_node}" 1> job-dir_${localjobname}/${localjobname}.executionnode 2>> $frontendlog
        echo "$end_marker" >> job-dir_${localjobname}/${localjobname}.executionnode
        sync_complete job-dir_${localjobname}/${localjobname}.executionnode
        echo "moving ${localjobname}.getinputfiles to job-dir_$localjobname" 1>> $frontendlog 2>> $frontendlog
        # try to avoid Text-file busy error, by doing a cp instead of mv
        # http://uwsg.iu.edu/hypermail/linux/net/9611.3/0052.html
        
        chmod +x ${localjobname}.getinputfiles 1>> $frontendlog 2>> $frontendlog
        cp -dpR ${localjobname}.getinputfiles job-dir_$localjobname/ 1>> $frontendlog 2>> $frontendlog

        # Make sure cp finished before deleting source file
        sync_complete job-dir_$localjobname/${localjobname}.getinputfiles

        $clean_command ${localjobname}.getinputfiles 1>> $frontendlog 2>> $frontendlog
        sync_clean ${localjobname}.getinputfiles
        
        force_refresh "job-dir_${localjobname}"

        echo "cd to job-dir_$localjobname" 1>> $frontendlog 2>> $frontendlog
        cd job-dir_$localjobname 1>> $frontendlog 2>> $frontendlog
        
        # Write exe
        
        # Request job from MiG server. Loop until it has arrived
        # execute $localjobname.getfiles. This downloads all needed 
        # inputfiles, $localjobname.job and 
        # $localjobname.sendoutputfiles
        
        # Debug
        complete_file_available ${localjobname}.getinputfiles || \
            echo "ERROR: getinputfiles is only partial after move!!" 1>> $frontendlog 2>> $frontendlog
        
        getinput_tries=5
        got_input=0
        for i in `seq 1 $getinput_tries`; do
            
            echo "executing ${localjobname}.getinputfiles ($i/$getinput_tries)" 1>> $frontendlog 2>> $frontendlog
            ./${localjobname}.getinputfiles 1>> $frontendlog 2>> $frontendlog
            getinput_ret=$?
            if [ $getinput_ret -eq 0 ]; then
                #echo ".getinputfiles for $localjobname ok ($getinput_ret)" 1>> $frontendlog 2>> $frontendlog
                got_input=1
                break
            else
                # try again later
                echo ".getinputfiles RETURNED NON-SUCCESFUL ($getinput_ret)" 1>> $frontendlog 2>> $frontendlog
                sleep 13
            fi
        done
        if [ $got_input -eq 0 ]; then
            # We don't know if errors came from missing user files or
            # network errors: thus we must continue and leave error
            # handling to MiG job failure retries
            echo "ERROR: .getinputfiles failed: keeping .getinput script to allow copy to continue" 1>> $frontendlog 2>> $frontendlog
            cp -dpR ${localjobname}.getinputfiles ../${localjobname}.getinputfiles.FAILED
            # We used to clean up jobdir here in order to get automatic 
            # retry from scratch later. 
            # That is now disabled due to the reasons explained above.
            #cd ..
            #$clean_recursive job-dir_${localjobname}
            sync_complete ../${localjobname}.getinputfiles.FAILED
            #continue
        else
            #echo "removing ${localjobname}.getinputfiles" 1>> $frontendlog 2>> $frontendlog
            $clean_command ${localjobname}.getinputfiles
            sync_clean ${localjobname}.getinputfiles
        fi
        
        # trying to fix the resource hanging where the master_node 
        # waits for the inputfiles_available signal therefore code is 
        # modified to send inputfiles and signal in two iterations and 
        # instead of just touching the .inputfiles_available file, 
        # there is put a litte content into it.
        # touch ${localjobname}.inputfiles_available
        inputfiles=`cat ${localjobname}.inputfiles 2>> $frontendlog`
        echo "moving ($move_command) ($inputfiles) to execution node (${copy_execution_prefix}${execution_dir}/job-dir_${localjobname}) and signal that inputfiles are available" 1>> $frontendlog 2>> $frontendlog
        while [ ! -z "$inputfiles" ]; do
            force_refresh $inputfiles
            $move_command $inputfiles ${copy_execution_prefix}${execution_dir}/job-dir_${localjobname} 1>> $frontendlog 2>> $frontendlog
            retval=$?
            if [ $retval -eq 0 ]; then
                #echo "move ($move_command) ($inputfiles) to (${copy_execution_prefix}${execution_dir}/job-dir_${localjobname}) went ok " 1>> $frontendlog 2>> $frontendlog
                
                # Remove inputfiles (this is to free space when $move_command is not deleting files etc. scp)
                $clean_recursive $inputfiles 1>> $frontendlog 2>> $frontendlog
                for i in "$inputfiles"; do
                    sync_clean $i
                done
                if [ $sandbox -eq 1 ]; then
                    chown -R ${execution_user}:${execution_user} ${execution_dir}/job-dir_${localjobname}
                    chown_ret=$?
                    if [ $chown_ret -ne 0 ]; then
                        echo "chown failed" 1>> $frontendlog 2>> $frontendlog
                    fi
                fi
                break
            else
                # continue until succesful
                echo "move ($move_command $inputfiles to (${copy_execution_prefix}${execution_dir}/job-dir_${localjobname}) failed ($retval)" 1>> $frontendlog 2>> $frontendlog
                
                # moving of inputfiles failed, check whether they exist or not
                new_inputfiles=""
                for file in $inputfiles; do
                    if [ -f $file ]; then
                        new_inputfiles="$new_inputfileS $file"
                    fi 
                done
                #echo "move inputfiles modified from ($inputfiles) to ($new_inputfiles)" 1>> $frontendlog 2>> $frontendlog
                inputfiles="$new_input_files"
                sleep 7
            fi
        done
        
        echo "sending ${localjobname}.inputfiles_available signal " 1>> $frontendlog 2>> $frontendlog
        #echo "creating inputfiles_available file" 1>> $frontendlog 2>> $frontendlog
        echo "file used to signal that inputfiles are available" > ${localjobname}.inputfiles_available
        echo "$end_marker" >> ${localjobname}.inputfiles_available
        while [ 1 ]; do 
            complete_file_available ${localjobname}.inputfiles_available || sleep 1
            complete_file_available ${localjobname}.inputfiles_available || continue
            echo "files before copy inputfiles_available: " * 1>> $frontendlog 2>> $frontendlog
            $copy_command ${localjobname}.inputfiles_available ${copy_execution_prefix}${execution_dir}/job-dir_${localjobname} 1>> $frontendlog 2>> $frontendlog
            available_ret=$?
            if [ $available_ret -eq 0 ]; then
                #echo "copy of ${localjobname}.inputfiles_available went ok ($available_ret)" 1>> $frontendlog 2>> $frontendlog
                # TMP! do we need this sync?
                #sync_disk $frontendlog
                break
            else
              # continue until succesful
                echo "copy of ${localjobname}.inputfiles_available failed ($available_ret)" 1>> $frontendlog 2>> $frontendlog
                sleep 13
            fi
        done    
        
        #echo "Deleting local ${localjobname}.inputfiles_available" 1>> $frontendlog 2>> $frontendlog
        $clean_command ${localjobname}.inputfiles_available 1>> $frontendlog 2>> $frontendlog
        sync_clean ${localjobname}.inputfiles_available
        #echo "After deleting ${localjobname}.inputfiles_available" 1>> $frontendlog 2>> $frontendlog
        cd ..      
        
        # values have been read and used, file can be deleted
        #echo "deleting $givejobrequest" 1>> $frontendlog 2>> $frontendlog
        $clean_command $givejobrequest
        # sync disk, otherwise the same givejobrequest file may be found again!
        sync_clean $givejobrequest
    done
    
    if [ $clean_up_counter -gt $clean_up_interval ]; then
        # Age clean up internal files after 30 days to avoid errors piling up.
        # This should never replace server initiated job clean up with privacy in mind.
        # NB: We must use "find -mtime" here for sandbox resource to work.
        echo "cleaning up old files" 1>> $frontendlog 2>> $frontendlog
        for extension in givejob inputfiles_available getinputfiles sendoutputfiles job jobdone FAILED; do
            for old_file in `find . -name "*.${extension}" -mtime +30| xargs`; do
                # No matching expansion results in no loop because of 'find' 
                # execution so no need to check for raw pattern 
                $clean_command "${old_file}"
            done
        done
        echo "rotating any big logs" 1>> $frontendlog 2>> $frontendlog
        for log_file in `find . -name "$(basename frontendlog)" -size +32M| xargs`; do
            # No matching expansion results in no loop because of 'find' 
            # execution so no need to check for raw pattern 
            echo "rotating $log_file" 1>> $frontendlog 2>> $frontendlog
            for i in `seq 7 -1 0`; do
                [ -e "$log_file.$i" ] && mv "$log_file.$i" "$log_file.$((i+1))"
            done
            mv "${log_file}" "${log_file}.0";
        done
        echo "finished clean up" 1>> $frontendlog 2>> $frontendlog
        clean_up_counter=0
    else
        clean_up_counter=$((clean_up_counter+1))
    fi
    
    # Sandbox job cancel/timeout
    if [ $sandbox -eq 1 ]; then
        if [ $sandbox_timeout_counter -gt $sandbox_timeout_interval ]; then
            sandbox_stop_exe
            sandbox_timeout_counter=0
        else
            sandbox_timeout_counter=$((sandbox_timeout_counter+1))
        fi
    fi

    # Slow down
    sleep 4
    
    # Background the while loop, this is done instead of backgrounding 
    # 'shared.ssh.executeRemoteSSH' which call's this scipt.
    # This gives the possibility to receive the status of the script instead
    # status of the SSH command.
done &
