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

"""
This is the MiG lib local module. It aims to emulate the behavior of the miglib.py api module by generating output similar to MiG, but
it performs all execution on the local system. It is useful for developing and debugging MiG client applications.
It should not be imported directly, but by enabling local mode execution in the miginterface.py module. 
"""

import sys
import os
import getopt
import subprocess
import StringIO
import tarfile
import shutil
import tempfile
from multiprocessing import Process
from multiprocessing.sharedctypes import Value, Array
import signal

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
        # use the unix os process monitor to watch the process.
        out = subprocess.Popen("ps axo pid,stat | grep %s" % job_id, shell=True, stdout=subprocess.PIPE).communicate()[0]
        ps_info = out.strip().split()
        
        if ps_info != []:
            # check if the process is in zombie state. This means that it has terminated.
            if ps_info[1].find("Z") == -1:
                status = "EXECUTING"
            else: 
                os.kill(int(job_id), signal.SIGTERM)

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
    server_out = __server_output_msg(0,job_info_list)
    return (exit_code, server_out)


def submit_file(src_path, dst_path, submit_mrsl, extract_package):
    """
    Submit an emulated grid job to the local system. The job will start in a new process.
    
    src_path - the local file system path to an input file.
    dst_path (not used) - not relevant for local execution. Only there to match miglib.
    submit_mrsl (not used) - not relevant for local execution. Only there to match miglib.
    extract_package (not used) - not relevant for local execution. Only there to match miglib.
    """
    
    working_dir = os.path.dirname(src_path)
    # start a new process
    proc = Process(target=__job_process, args=(src_path, working_dir,)) # the comma is not a typo
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
    
    path = os.path.join(MIG_HOME, path.lstrip("path="))
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

    path = os.path.join(MIG_HOME, path.strip("path="))
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
    try :
        for j in job_ids:
            os.kill(int(j), signal.SIGTERM)
            out.append("Cancelled job %s." % j)
        out.insert(0, "Exit code: 0")
    except OSError, e :
        out.append("Error cancelling job %s." % j)
        out.insert(0, "Exit code: 1")
    return (exit_code, out)


def rm_file(path_list):
    out = []
    for p in path_list.split(";"):
        path = os.path.join(MIG_HOME, p.strip("path="))
        if os.path.exists(path):
            os.remove(path)
            out.append("Removed %s" % path)
        else: 
            out.append("File not found %s" % path)
    exit_code = 0
    server_out = __server_output_msg(0, out)
    
    return (exit_code, server_out)

def put_file(src_path, dst_path, submit_mrsl, extract_package):
    mig_home_target = os.path.join(MIG_HOME, dst_path)
    shutil.copy(src_path, mig_home_target)
    server_out = __server_output_msg(0, "uploaded file %s"%src_path)
    exit_code = 0
    return (exit_code, server_out)

def cat_file(path_list):
    out = []
    for path in path_list:
        abs_path = os.path.join(MIG_HOME, path)
        cmd = "cat "+abs_path
        p = subprocess.Popen(cmd, shell=True, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out.append(p.communicate()[0])
        
    server_out = __server_output_msg(0, out)
    exit_code = 0
    return (exit_code, server_out)

def rm_dir(path_list):
    out = []
    for path in path_list:
        abs_path = os.path.join(MIG_HOME, path)
        cmd = "rmdir "+abs_path
        p = subprocess.Popen(cmd, shell=True, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out.append(p.communicate()[0])
    
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


def __job_process(input, working_dir):
    """
    Method for emulating a grid job. Will be run in a new process.

    input - input files for the job
    working_dir - the directory where the execution commands will be executed.
    """

    os.chdir(working_dir)
    tar_path = input
    # unpack the input files
    tar_file = tarfile.open(tar_path, "r")
    tar_file.extractall(working_dir)
    prog_files = tar_file.getnames()
    tar_file.close()

    mrsl_file = ""
    # locate the .mRSL file
    for f in prog_files:
        if f.find(".mRSL") != -1:
            mrsl_file = f
    
    
    # parse the mRSL file
    f = open(os.path.join(working_dir,mrsl_file))
    lines = f.readlines()
    
    # extract commands
    first_cmd = lines.index("::EXECUTE::\n")+1
    commands = []
    for line in lines[first_cmd:]:
        if line.find("::") != -1:
            break
        if line.strip() != "":
            commands.append(line.strip())
    
    # extract output files
    first_outputfile = lines.index("::OUTPUTFILES::\n")+1
    outputfiles = []
    for line in lines[first_outputfile:]:
        if line.find("::") != -1:
            break
        if line.strip() != "":
            outputfiles.append(line.strip())
    
    
    job_id = str(os.getpid())
    
    status_files_directory = os.path.join(MIG_HOME, "job_output", job_id)
    os.makedirs(status_files_directory)
    
    stdout_path = os.path.join(status_files_directory, job_id+".stdout")
    stderr_path = os.path.join(status_files_directory, job_id+".stderr")
    
    stdout_file = open(stdout_path, "w")
    stderr_file = open(stderr_path, "w")
    
    # run the commands
    try :
        for cmd in commands:
            proc = subprocess.Popen(cmd, shell=True, bufsize=0, stdout=stdout_file, stderr=stderr_file, close_fds=True)
            proc.wait()
    
    except Exception, e:
        "Process error : %s. Terminating.", e.err()
    except KeyboardInterrupt :
        print "Keyboard interrupt. Terminating."
        return
        
    # copy output files from mig home dir
    for f in outputfiles:
        filepath = f.strip().split()
        src_path = filepath[0]
        dest_path = filepath[0]
        
        # if there are two file names, we are using the mig format of <path_on_resource path_on_mig_home>
        if len(filepath) > 1:
            dest_path = filepath[1]
        shutil.copy(os.path.join(working_dir, src_path), os.path.join(MIG_HOME, dest_path))