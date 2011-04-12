#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# migliblocal - a part of the MiG interface module
# Copyright (C) 2004-2010  MiG Core Developers lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
from migerror import MigLocalError

"""
This is the MiG lib local module. It aims to emulate the behavior of the miglib.py api module by generating output similar to MiG, but
it performs all execution on the local system. It is useful for developing and debugging MiG client applications.
It should not be imported directly, but by enabling local mode execution in the miginterface.py module. 
"""

import sys
import os
import subprocess
import tarfile
import shutil
import tempfile
from multiprocessing import Process, active_children
import time

# the path to the fake local mig home directory
user = os.getlogin()
MIG_HOME = os.path.join(tempfile.gettempdir(), user+"_mig_home")

if not os.path.exists(MIG_HOME):
    job_status_files_dir = "job_output"
    os.makedirs(os.path.join(MIG_HOME, job_status_files_dir))


def job_status(job_ids, max_job_count):
    """
    Get the job status of the jobs with the listed ids. 

    job_ids - list of job ids
    max_job_count - max number of jobs to list
    """

    job_info_list = []
    status = "FINISHED"
    
    for job_id in job_ids:
        procs = active_children()
        for p in procs:
            if p.pid == int(job_id):
                status = "EXECUTING"
                

        job_info = ["Job Id: "+job_id+"\n", "Status: "+status+"\n"] # we need the newlines for parsing in miginterface- same as mig outputs
        job_info_list.extend(job_info)
        
        if len(job_info_list) == max_job_count:
            break
        
        
    # example mig output format to emulate : 
    #   (0, ['Exit code: 0 Description OK\n', 'Title: jobstatus\n', '\n', '___MIG UNSORTED  JOB STATUS___\n', '\n', 
    #       'Only showing first 1 of the 11686 matching jobs as requested\n', 
    #       'Job Id: 349459_9_29_2008__20_42_37_mig-1.imada.sdu.dk.0\n', 'Status: FINISHED\n', 
    #       'Received: Mon Sep 29 20:42:37 2008\n', 'Queued: Mon Sep 29 20:42:38 2008\n', 
    #       'Executing: Mon Sep 29 20:47:03 2008\n', 'Finished: Mon Sep 29 20:49:25 2008\n', '\n'])
    exit_code = 0
    server_out = __server_output_msg(exit_code,job_info_list)
    return (exit_code, server_out)


def submit_file(src_path, dst_path, submit_mrsl, extract_package):
    """
    Submit an emulated grid job to the local system. The job will start in a new process.
    
    src_path - the local file system path to an input file.
    dst_path - the path to put the src_path file in the fake mig home dir.
    submit_mrsl (not used) - the mrsl file is always submitted in local mode
    extract_package - this must be true when submitting a job through an archive
    """
    
    working_dir = os.path.dirname(src_path)
    
    start_of_suffix = os.path.basename(src_path).find(".") 
    job_name = src_path[:start_of_suffix]
    
    exec_dir = os.path.join(tempfile.gettempdir(), job_name+"_localexec")
    if os.path.exists(exec_dir): # create unique folder name
        timestamp = int(time.time()*100)
        exec_dir += "_"+str(timestamp) 
    os.mkdir(exec_dir)
    
    # copy the file to fake mig home
    shutil.copy(src_path, os.path.join(MIG_HOME,dst_path))
    mrsl_file = ""
    
    if extract_package :
        # unpack the input files
        tar_file = tarfile.open(os.path.join(MIG_HOME,dst_path), "r")
        tar_file.extractall(MIG_HOME)
        prog_files = tar_file.getnames()
        tar_file.close()
        
        for f in prog_files:
            if f.find(".mRSL") != -1:
                mrsl_file = f
    
    else:
        if os.path.basename(src_path.lower()).find(".mrsl") == -1:
            raise MigLocalError("Must submit an mRSL file")
        
        
        mrsl_file = dst_path
    
    mrsl_entries = __parse_mrsl(os.path.join(MIG_HOME, mrsl_file))
    all_input_files = []
    if mrsl_entries.has_key("INPUTFILES"):
        all_input_files.extend(mrsl_entries["INPUTFILES"])

    if mrsl_entries.has_key("EXECUTABLES"):
        all_input_files.extend(mrsl_entries["EXECUTABLES"])
    
    all_input_files.append(mrsl_file)
    
    # stage the input files by copying from mig home to execution dir
    for f in all_input_files:
        paths = f.split()
        src = paths[0]
        dest = paths[0]
        if len(paths) > 1: # user provided a destination preference
            dest = paths[1]
            directory = os.path.join(exec_dir, os.path.dirname(dest)) # destination dir
            if not os.path.exists(directory):
                os.makedirs(directory) 
        shutil.copy(os.path.join(MIG_HOME, src), os.path.join(exec_dir, dest))
                
    # start a new process
    proc = Process(target=__job_process, args=(mrsl_file, exec_dir,)) # the comma is not a typo
    proc.start()
    exit_code = 0
    server_out = ["0"]
    job_id = str(proc.pid)
    server_out.append(str([{"job_id": job_id, "status": True}]))
    # example mig output format we want to emulate : 
    #   (0, ['0\n', "[{'status': True, 'object_type': 'submitstatus', 'name': '/gridjob_128989893464.mRSL', 
    #       'job_id': '334719_11_16_2010__12_20_54_dk.migrid.org.0'}]\n"])

    return (exit_code, server_out)

def get_file(src_path, dst_path):
    """
    Copy the file from the emulated mig home directory.
    
    src_path - path to the file relative to the mig home directory.
    dst_path - path to target file on the local system.
    """
    # get the file from the fake mig home dir
    shutil.copy(os.path.join(MIG_HOME, src_path), dst_path)
    server_out = __server_output_msg(0,"")
    exit_code = 0
    return (exit_code, server_out)


def ls_file(path):
    """
    List the contents of the directory from the fake mig home dir. 

    path - path to file from fake mig home.
    """
    
    path = os.path.join(MIG_HOME, path.replace("path=", ""))
    server_out = []
    if os.path.exists(path):
        if os.path.isfile(path):
            files = [os.path.basename(path)]
        else: 
            files = os.listdir(os.path.join(MIG_HOME, path))
        server_out = __server_output_msg(0, files)
    else:
        server_out = __server_output_msg(105, "file not found")
        
    exit_code = 0

    return (exit_code, server_out)


def mk_dir(path):
    """
    Make a directory in the fake mig home dir.

    path - path to directory relative to the mig home dir.
    """

    path = os.path.join(MIG_HOME, path.replace("path=", ""))
    server_out = []
    if not os.path.exists(path):
        os.mkdir(path)
    
    server_out = __server_output_msg(0,"")
    exit_code = 0

    return (exit_code, server_out)


def cancel_job(job_ids):
    if isinstance(job_ids, str):
        job_ids = [job_ids]
    out = []
    exit_code = 0
    procs = active_children()
    try :
        for job_id in job_ids: 
            for p in procs:
                if int(job_id) == p.pid :
                    p.terminate()
                    out.append("Cancelled job %s." % job_id)
        out.insert(0, "Exit code: 0")
    except OSError, e :
        out.append("Error cancelling job %s." % job_id)
        out.insert(0, "Exit code: 1")
    return (exit_code, out)


def rm_file(path_list):
    out = []
    server_exit_code = 0
    exit_code = 0
    for p in path_list.split(";"):
        path = os.path.join(MIG_HOME, p.replace("path=", ""))
        if os.path.exists(path):
            os.remove(path)
            out.append("Removed %s" % path)
        else: 
            out.append("File not found %s" % path)
            server_exit_code = 105
    server_out = __server_output_msg(server_exit_code, out)
    return (exit_code, server_out)

def put_file(src_path, dst_path, submit_mrsl, extract_package):
    mig_home_target = os.path.join(MIG_HOME, dst_path)
    shutil.copy(src_path, mig_home_target)
    server_out = __server_output_msg(0, "uploaded file %s"%src_path)
    exit_code = 0
    return (exit_code, server_out)

def cat_file(path_list):
    exit_code = 0    
    server_exit_code = 0
    concat_str = ""
    for path in path_list:
        abs_path = os.path.join(MIG_HOME, path)
        contents = "cat: %s: No such file or directory" % abs_path 
        if os.path.exists(abs_path):
            f = open(abs_path)
            contents = f.read()
            f.close()
        else: 
            server_exit_code = 105
        concat_str += contents + "\n"
    out = [concat_str]      
    server_out = __server_output_msg(server_exit_code, out)

    return (exit_code, server_out)

def rm_dir(path_list):
    out = []
    for path in path_list:
        abs_path = os.path.join(MIG_HOME, path)
        os.rmdir(path)
    
    server_out = __server_output_msg(0, out)
    exit_code = 0
    
    return (exit_code, server_out)



def expand_name(path_list, server_flags, destinations):
# not implemented yet
    
    return (exit_code, out)


def show_doc(search, show):
# not implemented yet
    
    return (exit_code, out)

def head_file(lines, path_list):
# not implemented yet
    
    return (exit_code, out)


def job_action(action, job_list):
# not implemented yet
    
    return (exit_code, out)


def job_liveio(action, job_id, src_list, dst):
# not implemented yet
    
    return (exit_code, out)

def job_mqueue(action, queue, msg):
# not implemented yet
    
    return (exit_code, out)


def mv_file(src_list, dst):
# not implemented yet
    
    return (exit_code, out)


def read_file(first, last, src_path, dst_path):
# not implemented yet
    
    return (exit_code, out)


def stat_file(path_list):
# not implemented yet
    
    return (exit_code, out)


def resubmit_job(job_list):
# not implemented yet
    
    return (exit_code, out)


def tail_file(lines, path_list):
# not implemented yet
    
    return (exit_code, out)


def touch_file(path_list):
# not implemented yet
    
    return (exit_code, out)


def truncate_file(size, path_list):
# not implemented yet
    
    return (exit_code, out)


def unzip_file(src_list, dst):
# not implemented yet
    
    return (exit_code, out)


def wc_file(path_list):
# not implemented yet
    
    return (exit_code, out)


def write_file(first, last, src_path, dst_path):
# not implemented yet
    
    return (exit_code, out)


def zip_file(current_dir, src_list, dst):
# not implemented yet
    
    return (exit_code, out)


def version():
    """Show version details"""
    print 'MiG User Scripts: $Revision: 1251 $,$Revision: 1251 $'

def check_var(name, var):
    """Check that conf variable, name, is set"""

    if not var:
        print "Error: Variable %s not set!" % name
        print "Please set in configuration file or through the command line"
        sys.exit(1)



def read_conf(conf, option):
    """Extract a value from the user conf file: format is KEY and VALUE
    separated by whitespace"""

    try:
        conf_file = open(conf, 'r')
        for line in conf_file:
            line = line.strip()
            # split on any whitespace and assure at least two parts
            parts = line.split() + ['', '']
            opt, val = parts[0], parts[1]
            if opt == option:
                return val
        conf_file.close()
    except Exception:
        return ''
    
    
def __server_output_msg(exit_code, output):
    """
    Format the message so it looks like a message from the mig server
    
    exit_code - the exit code of some action
    output - the output message 
    """
    if not isinstance(output, list):
        output = list(str(output))
        
    server_out = ["Exit code: %s " % str(exit_code)]
    server_out.extend(output)
    return server_out


def __parse_mrsl(path):
    #mrsl_fields = ["EXECUTE", "INPUTFILES", "EXECUTABLES", "OUTPUTFILES"]
    mrsl_dict = {}
    
    # parse the mRSL file
    f = open(path)
    lines = f.readlines()
    f.close()
    key = "MISSINGFIELDNAME"
    for l in lines:
        if l.find("::") != -1:
            key = l.replace("::", "").strip()
            mrsl_dict[key] = []
        else:
            value = l.strip()
            if value:
                mrsl_dict[key].append(value)    
                 
    return mrsl_dict
    

def __job_process(mrsl_file, working_dir):
    """
    Method for emulating a grid job. Will be run in a new process.

    input - input files for the job
    working_dir - the directory where the execution commands will be executed.
    """

    os.chdir(working_dir)
    # parse the mRSL file
    mrsl_entries = __parse_mrsl(os.path.join(working_dir,mrsl_file))

    job_id = str(os.getpid())
    
    status_files_directory = os.path.join(MIG_HOME, "job_output", job_id)
    os.makedirs(status_files_directory)
    
    stdout_path = os.path.join(status_files_directory, job_id+".stdout")
    stderr_path = os.path.join(status_files_directory, job_id+".stderr")
    

    
    # run the commands
    try :
        
        stdout_file = open(stdout_path, "w")
        stderr_file = open(stderr_path, "w")
        
        for cmd in mrsl_entries["EXECUTE"]:
            __check_rte_vars(cmd)
            
            proc = subprocess.Popen(cmd, shell=True, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            out, err = proc.communicate()
            if err : 
                print "WARNING: Local grid job process wrote to standard error:\n", err
            
            stdout_file.write(out)
            stderr_file.write(err)
            
        stdout_file.close()
        stderr_file.close()
    except Exception, e:
        print "Process error : Terminating.", e
    except KeyboardInterrupt :
        print "Keyboard interrupt. Terminating."
        return
        
    if mrsl_entries.has_key("OUTPUTFILES"):
        # copy output files from mig home dir
        for f in mrsl_entries["OUTPUTFILES"]:
            filepath = f.strip().split()
            src_path = filepath[0]
            dest_path = filepath[0]
            
            # if there are two file names, we are using the mig format of <path_on_resource path_on_mig_home>
            if len(filepath) > 1:
                dest_path = filepath[1]
                dest_directory = os.path.join(MIG_HOME, os.path.dirname(dest_path))
                if not os.path.exists(dest_directory):
                    os.makedirs(dest_directory)
            if os.path.exists(os.path.join(working_dir, src_path)):
                shutil.copy(os.path.join(working_dir, src_path), os.path.join(MIG_HOME, dest_path))
            else:
                print "WARNING: Missing output file.",src_path
            
            
def __check_rte_vars(cmd):
    """
    Searches for alias variables in the commands cmd and checks if they are in the local os environment. 
    Fx "$PYTHON" 
    
    cmd - a string format shell command
    """
    tokens = cmd.split()
    for t in tokens:
        if t.find("$") != -1:
            rte_var = t
            if not os.getenv(rte_var.lstrip("$")):
                print "WARNING: found undefined runtime environment variable ", rte_var
            
    