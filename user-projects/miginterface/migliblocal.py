#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# miglib - a part of the MiG scripts
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
This is the MiG lib local module. It aimes to emulate the behavior of the miglib api module, while
performing all execution on the local system. Useful for developing and debugging MiG client applications.
Should not be imported directly. It will be used when enabling local mode execution in the miginterface.py module. 
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
MIG_HOME = os.path.join(tempfile.gettempdir(), "mig_home")

if not os.path.exists(MIG_HOME):
    os.mkdir(MIG_HOME)


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
        
        
    # example mig job output to emulate : 
    #   (0, ['Exit code: 0 Description OK\n', 'Title: jobstatus\n', '\n', '___MIG UNSORTED  JOB STATUS___\n', '\n', 
    #       'Only showing first 1 of the 11686 matching jobs as requested\n', 
    #       'Job Id: 349459_9_29_2008__20_42_37_mig-1.imada.sdu.dk.0\n', 'Status: FINISHED\n', 
    #       'Received: Mon Sep 29 20:42:37 2008\n', 'Queued: Mon Sep 29 20:42:38 2008\n', 
    #       'Executing: Mon Sep 29 20:47:03 2008\n', 'Finished: Mon Sep 29 20:49:25 2008\n', '\n'])
    exit_code = 0
    server_out = ["Exit code: 0"]
    server_out.extend(job_info_list)
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
    server_out.append(str([{"job_id": str(proc.pid), "status": True}]))
    # example mig out we want to emulate : 
    #   (0, ['0\n', "[{'status': True, 'object_type': 'submitstatus', 'name': '/gridjob_128989893464.mRSL', 
    #       'job_id': '334719_11_16_2010__12_20_54_dk.migrid.org.0'}]\n"])

    return (exit_code, server_out)

def get_file(src_path, dst_path):
    """
    Copy the file from the emulated mig home directory.
    
    src_path - path to the file relative to the mig home directory.
    dst_path - path to target file on the local system.
    """
    
    shutil.copy(os.path.join(MIG_HOME, src_path), dst_path) # get the file from out fake mig home dir
    server_out = ["Exit code: 0"]
    exit_code = 0
    return (exit_code, server_out)


def ls_file(path):
    """
    List the contents of the directory from the fake mig home dir. 

    path - path to file from fake mig home.
    """
    
    path = os.path.join(MIG_HOME, path.strip("path="))
    server_out = []
    if os.path.exists(path):
        files = os.listdir(os.path.join(MIG_HOME, path))
        server_out = ["Exit code: 0"]
        server_out.extend(files) # mig outputs (<local exit code>, [<Server exit code>, ...])
    else:
        server_out = ["Exit code: 105"] # file not found error
        
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
    
    server_out = ["Exit code : 0"]
    exit_code = 0

    return (exit_code, server_out)


def __job_process(input, working_dir):
    """
    Method for emulating a grid job. Will be run in a new process.

    input - input files for the job
    working_dir - the directory where the execution commands will be executed.
    """

    os.chdir(working_dir)
    tar_path = input
    # extract input files
    tar_file = tarfile.open(tar_path, "r")
    tar_file.extractall(working_dir)
    prog_files = tar_file.getnames()
    tar_file.close()

    mrsl_file = ""
    # find mRSL file
    for f in prog_files:
        if f.find(".mRSL") != -1:
            mrsl_file = f
    
    f = open(os.path.join(working_dir,mrsl_file))
    lines = f.readlines()
    
    first_cmd = lines.index("::EXECUTE::\n")+1
    commands = []
    for line in lines[first_cmd:]:
        if line.find("::") != -1:
            break
        if line.strip() != "":
            commands.append(line.strip())
    
    first_outputfile = lines.index("::OUTPUTFILES::\n")+1
    outputfiles = []
    for line in lines[first_outputfile:]:
        if line.find("::") != -1:
            break
        if line.strip() != "":
            outputfiles.append(line.strip())
        
    for cmd in commands:
        proc = subprocess.Popen(cmd, shell=True, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        #proc = subprocess.Popen(cmd, shell=True)
        proc.wait()
        
    
    for f in outputfiles:
        filepath = f.strip().split()
        src_path = filepath[0]
        dest_path = filepath[0]
        
        # if there are two file names, we are using the mig format of <resource_scr mig_home_dest>
        if len(filepath) > 1:
            dest_path = filepath[1]
        #proc = subprocess.Popen(cmd, shell=True, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        shutil.copy(os.path.join(working_dir, src_path), os.path.join(MIG_HOME, dest_path))
        #print "copied output file "+f+" to "+ os.path.join(mig_home, dest_path)

def cancel_job(job_list):
    
    return (exit_code, out)


def rm_file(path_list):
    
    exit_code = 0
    out = ["Exit code: 0"]
    
    return (exit_code, out)

def put_file(src_path, dst_path, submit_mrsl, extract_package):

    return (exit_code, out)

def expand_name(path_list, server_flags, destinations):

    return (exit_code, out)

def cat_file(path_list):

    return (exit_code, out)


def show_doc(search, show):

    return (exit_code, out)

def head_file(lines, path_list):

    return (exit_code, out)


def job_action(action, job_list):

    return (exit_code, out)


def job_liveio(action, job_id, src_list, dst):

    return (exit_code, out)

def job_mqueue(action, queue, msg):

    return (exit_code, out)


def mv_file(src_list, dst):

    return (exit_code, out)




def read_file(first, last, src_path, dst_path):

    return (exit_code, out)




def rm_dir(path_list):

    return (exit_code, out)


def stat_file(path_list):

    return (exit_code, out)


def resubmit_job(job_list):

    return (exit_code, out)


def tail_file(lines, path_list):

    return (exit_code, out)


def touch_file(path_list):

    return (exit_code, out)


def truncate_file(size, path_list):

    return (exit_code, out)


def unzip_file(src_list, dst):

    return (exit_code, out)


def wc_file(path_list):

    return (exit_code, out)


def write_file(first, last, src_path, dst_path):

    return (exit_code, out)


def zip_file(current_dir, src_list, dst):

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