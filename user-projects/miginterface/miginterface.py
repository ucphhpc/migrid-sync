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
The Python MiG Interface Module

A high-level library for writing python client applications for the Minimum intrusion Grid.

"""

import os
import time
import tarfile
import mrsl
import logging 
from migerror import *
import tempfile
import random
import sys
 
MIG_CONFIG = os.path.expanduser("~/.mig/miguser.conf")

LOG_FILE = os.path.join(tempfile.gettempdir(), "miginterface_log.txt")
DEBUG_MODE = False
LOCAL_MODE = False

if os.path.isfile(MIG_CONFIG):
    try:
        import miglib
    except ImportError, err:
        print "Could not import the miglib module : \n\t %s " % err
        print "Importing migliblocal module. miginterface operations will only run in local mode."
        import migliblocal as miglib
else:
    print "Could not find your MiG configuration file. It should be in %s." % MIG_CONFIG
    print "Importing migliblocal module. miginterface will only be able to run in local mode."
    import migliblocal as miglib


def create_job(exec_commands, input_files=[], output_files=[], executables=[], cached_files=[], resource_specifications={}, name=""):
    """
    Create and submit a grid job.
    Returns the job id given by the MiG server after a succesful submission.
    
    Generates an mRSL file, archives and uploads user input files and submits the job. 
    Files are placed in the working directory (/tmp on linux systems)
    
    exec_commands - a list of unix style shell commands.
    input_files (optional) - input files used in the grid job. They will be uploaded to the server.
    output_files (optional) - output files that will be transfered from resource to the server after a job. 
    executables (optional) - executable input files. Similar to input files, but will made executable (chmod).  
    cached_files (optional) - input files used in the job that are already present on the MiG server. They will not be uploaded. 
    resource_specs (optional) - a dictionary of additional resource specifications. Field names must match mRSL syntax. 
        Example : resource_specifications = {"ARCHITECTURE": "AMD64"}
    name (optional) - custom name for the mRSL file and folder.
    """
    
    if isinstance(input_files, str):
        input_files = [input_files]
        
    if isinstance(executables, str):
        executables = [executables]
        
    if isinstance(output_files, str):
        output_files = [output_files]
        
    # check if the files exist
    for f in input_files:
        if not os.path.exists(f):
            raise MigLocalError("Cannot find input file: "+f)
    
    for f in executables:
        if not os.path.exists(f):
            raise MigLocalError("Cannot find executable file: "+f)
            
    # name of the mrsl file and working directory
    if name == "":
        timestamp = int(time.time()*100)
        random.seed()
        r_num = random.randint(0, timestamp)
        name = "gridjob_"+str(timestamp)+str(r_num)
    mrsl_filename = name+".mRSL"
    #mig_job_directory = name 

    tmp_dir = tempfile.gettempdir() # /tmp/
    local_working_dir = os.path.join(tmp_dir, name)
    # creating local temporary working directory
    os.mkdir(local_working_dir) 
    # create job directory on MiG
    #mk_dir(mig_job_directory) 
    # the path of the mRSL file
    mrsl_path = os.path.join(local_working_dir, mrsl_filename) 
    
    # make a list with both input_files and cached_files
    all_input_files = []
    all_input_files.extend(input_files)
    all_input_files.extend(cached_files)
    
    # create the mRSL file
    mrsl.generate_mrsl(mrsl_path, exec_commands, all_input_files, output_files, executables=executables, resource_specifics=resource_specifications)
    
    # Gather all files we need to upload
    upload_files = []
    upload_files.append(mrsl_path)
    upload_files.extend(executables)
    upload_files.extend(input_files)
    
    tar_name = name+".tar.gz"
    # path to tarball
    tar_file = os.path.join(local_working_dir, tar_name) 
    __create_archive(tar_file, upload_files) 
    
    mig_tar_file_destination = tar_name # os.path.join(mig_job_directory, tar_name)
    # upload job archive and submit mrsl
    output = __miglib_function(miglib.submit_file, tar_file, mig_tar_file_destination, True, True) 
            
    __debug(output)
    
    __verify_submit(output)
        
    # extract the job id given by the server
    job_id = __extract_job_id(output)
    # remove the tarball that contained the uploaded files
    remove(mig_tar_file_destination)
    remove(os.path.basename(mrsl_path))
    
    # remove the unpacked input files from user home root.
    # CAUTION: input files must be available during queued status.
    #for uploaded_file in upload_files:
    #   remove(os.path.basename(uploaded_file))
    
    return job_id


def submit_job(mrsl_file, dest_dir=""):
    """
    Submits a MiG job using an mrsl_file. 
    Returns a job id given by the MiG server.
    
    NOTE: It is recommended to use create_job() instead.
    This will implicitly generate an mRSL file and submit the job.
    
    mrsl_file - path to an mrsl file containing the job configuration
    dest_dir (optional) - the target directory to put the mrsl file in the MiG user home. 
    """
    output = __miglib_function(miglib.submit_file, mrsl_file, dest_dir, True, False) 
    __debug(output)
    __verify_submit(output)
    job_id = __extract_job_id(output)
    
    return job_id


def upload_file(path, mig_path=""):
    """
    Upload a file to the MiG user home directory.  
    Returns the MiG relative path to the uploaded file.
    
    NOTE: For uploading input files to be used in a grid job use create_job() instead. 
    This will also upload the provided input files.
    
    path - local path to the file
    mig_path - path to the MiG destination relative to the MiG user home directory
    """
    if mig_path == "":
        mig_path = os.path.basename(path)
    submit = False
    extract = False
    output = __miglib_function(miglib.put_file, path, mig_path, submit, extract)
    return output


def mk_dir(dirname):
    """
    Create a directory in the MiG user home directory.
    Returns a path to the created dir.
    
    dirname - path to the directory relative to the MiG user home directory.
    """
    
    path_str = "path="+dirname

    return __miglib_function(miglib.mk_dir, path_str)

  
def ls(path):
    """
    List files in path. 
    Returns the files in a list.  
    
    path - path to a location in the MiG user home directory.
    """
    #path_str = "path="+path
    out = __miglib_function(miglib.ls_file, path) 
    files = map(lambda x : x.strip("\t\n"), out)
    return files 


def path_exists(path):
    """
    Check if the path exists. 
    Returns a boolean. True if path exists. 
    
    path - path to a file in the MiG user home directory.
    """
    path_str = "path="+path
    path_exists = True
    
    try: 
        __miglib_function(miglib.ls_file, path_str)
    
    except MigServerError, server_err : # catch the file not found exception raised
        if server_err.error_code == 105:
            path_exists = False
        else:
            raise server_err
    
    return path_exists
   

def get_file(filename, destination=""):
    """
    Download a file from the MiG server.
    Returns a path to the downloaded file.
    
    mig_file - path to the file from the MiG home user directory. "." is the user home root directory.
    destination (optional) - path to a target file on the local filesystem.
    """
    if not path_exists(filename):
        raise MigServerError("File %s not found in mig user home."%filename)
    
    if not destination:
        destination = filename
    else:
        if os.path.isdir(destination):
            destination = os.path.join(destination, filename)
    __miglib_function(miglib.get_file, filename, destination)
    return destination


def job_info(job_id):
    """
    Get job information for a submitted job.
    Returns a dictionary of job information.
    
    job_id - the job id given by the MiG server when the job was submitted (see create_job()).
    """
    job_id = [job_id] # only seems to work with lists
    job_data_list = __miglib_function(miglib.job_status, job_id, 1) # return a list of data for each job
    job_info_list = __parse_job_info(job_data_list)
    return job_info_list[0]


def jobs_info(job_ids):
    """
    Retrieve job information for list of submitted jobs. Like job_info() but for multiple jobs. 
    Returns a list of dictionaries containing information for each job.
    
    job_ids - a list of job ids.
    """
    
    job_data_list = __miglib_function(miglib.job_status, job_ids, 1000) # return a list of data for each job
    job_info_list = __parse_job_info( job_data_list)
    return job_info_list


def job_status(job_id):
    """
    Get the status of a submitted job.
    Returns a string implying the job status. Ex. "QUEUED", "EXECUTING", "FINISHED" etc.
    
    Job_id - the job id given by the MiG server (see create_job()).
    """
    job_info_dict = job_info(job_id)
    
    return job_info_dict["STATUS"]


def jobs_status(job_ids):
    """
    Get the status of a list of jobs. Like job_status() but for multiple jobs.
    Returns a list of status strings in the same order the jobs were listed as input. 
    
    job_ids - a list of job ids.
    """

    job_info_list = jobs_info(job_ids)
    job_status_list = [info["STATUS"] for info in job_info_list]
    return job_status_list


def job_finished(job_id):
    """
    Check if the job has finished executing. 
    Returns a boolean indicating whether or not the job is done.
    
    job_id - the job id given by the MiG server (see create_job()).
    """
    status = job_status(job_id)
    mig_finished_state = "FINISHED"
    return (status == mig_finished_state)


def cancel_job(job_id):
    """
    Cancel a submitted job.
    Returns a MiG server message. 
    
    job_id - the job id given by the MiG server (see create_job()).
    """
    
    out = __miglib_function(miglib.cancel_job, [job_id]) # miglib only takes a list at this point
    return out 


def cancel_jobs(job_ids):
    """
    Cancel a list of jobs.
    Returns a MiG server message. 
    
    job_ids - a list of job ids given by the MiG server (see create_job()).
    """
    
    out = __miglib_function(miglib.cancel_job, job_ids) # miglib only takes a list at this point
    return out 


def remove(path):
    """
    Delete one or more files from the MiG user home directory.
    Returns a MiG server message.
    
    path - path to the file to be deleted in the MiG user home directory. 
                Either as string to a single file or a list of strings to multiple files.
    """
    if not isinstance(path, list):
        path = [path]
    path_list = "path=%s" % ";path=".join(path) # necessary format for miglib.rm_file()
    return __miglib_function(miglib.rm_file, path_list)


def remove_dir(dirname):
    """
    Remove a directory from the MiG server.
    Returns a MiG server message.
    
    dirname - path to the directory from the MiG user home dir.
    """
    
    path_list = "path=%s" % ";path=".join([dirname]) # necessary format for miglib.rm_dir()
    return __miglib_function(miglib.rm_dir, path_list)


def job_output(job_id):
    """
    Get the standard out and standard error from the job. 
    Returns a string with the stdout and stderr.
    
    job_id - the job id
    """
    path_list = []
    path_list.append(os.path.join("job_output", job_id, job_id+".stderr"))
    path_list.append(os.path.join("job_output", job_id, job_id+".stdout")) 
    
    out = __miglib_function(miglib.cat_file, path_list)
    out_str = "\n".join(out)
    str_list = out_str.split("___CAT___") # filter out the information part
    if len(str_list) > 1 :
        str_list.pop(0)
    return "".join(str_list).strip()
    
def test_connection():
    """
    Test the connection to the MiG server.
    Returns a boolean indicating whether or not the user can execute MiG actions.
    """
    home_dir = "."
    success = path_exists(home_dir)
    
    return success


##############################################
############# MISC FUNCTIONS ######################
##############################################

def set_log_file(path):
    """
    Change the log file. 
    
    path - file path to the log file.
    """
    global LOG_FILE
    LOG_FILE = path


def debug_mode_on():
    """
    Enter debug mode. Enable screen debug print outs. 
    Otherwise they will be written to the log file.
    """
    
    global DEBUG_MODE
    DEBUG_MODE = True


def debug_mode_off():
    """
    Exit debug mode. Disable screen debug print outs. 
    Prints will be written in the log file LOG_FILE.
    """

    global DEBUG_MODE
    DEBUG_MODE = False


def local_mode_on():
    """
    Enter local mode execution. All execution is done on the local system by emulating MiG. 
    
    A new OS process is spawned for each created grid job. Useful for testing before submitting to 
    actual grid execution. Utilizes multi-processing.
   
    """
    global LOCAL_MODE
    LOCAL_MODE = True
    
    global miglib
    import migliblocal as miglib


def local_mode_off():
    """
    Go to grid execution (default).
    """
    
    global LOCAL_MODE
    LOCAL_MODE = False
    
    global miglib
    import miglib as miglib



    
##############################################
############# HELPER FUNCTIONS ####################
##############################################

def __verify_submit(server_output):
    """
    Checks the server message to verify that the submit was successful. Raises exception if an error is found.
    
    server_message - server output message from the job submission in a list. 
    """
    
    if len(server_output) > 1: # output should be of the format [exit_code, output_str]
        server_message = eval(server_output[1]) # get the server message
        if server_message[0].has_key('status'):
            if not server_message[0]['status']: # false on failure
                err_msg = "Submit status false. Server reported unsuccessful job submission : %s\n" % "".join(server_output)
                raise MigServerError(err_msg)
        
        else: # no 'status' key found
            err_msg = "Unexpected return message format. Could not find the status keyword in output : %s\n" % "".join(server_output)
            raise MigServerError(err_msg)
                
    else:
        err_msg = "Unexpected return message format. Could not find message from server : %s\n" % "".join( server_output)
        raise MigServerError(err_msg)
    
    __debug("Successful job submit.")

 
def __extract_job_id(output):
    """
    Parses the the output from the MiG server and extracts the job id.
    Returns the job id as a string. 
    
    output - the output given by the MiG server after a successful job submission.
    """
    job_id = ""
    
    if len(output) > 1: # output should be of the format <exit_code, output_str>
        server_output = eval(output[1]) # 
        
        if server_output[0].has_key("job_id"):
            job_id = server_output[0]["job_id"] # extract the job id given by the server
        
    if job_id == "":
        raise MigServerError("Unable to parse. Could not extract job id from : %s\n" % output)
    
    return job_id

   
def __create_archive(tar_path, input_files):
    """
    Creates a tar.gz archive containing the input files.
    Returns a path to the archive file.

    tar_path - path to the target tar.gz file
    input_files - a list of paths to files.
    """
    tar = tarfile.open(tar_path, "w:gz")
    for f in input_files:
        base_filename = os.path.basename(f) # strip the folders
        tar.add(f, base_filename) 
    tar.close()
    
    return tar_path


def __parse_job_info(status_list):
    """
    Parses a list of status messages from the MiG server..
    Returns a list of job info dictionaries in the same order as the input list.

    status_list - a list of status messages produced by the MiG server when using get_status().
    """
    status_str = "".join(status_list)
    job_info_str_list = status_str.split("Job ")[1:] # we don't need the preceding information
    job_info_list = []
    for ji in job_info_str_list:
        status = __parse_status(ji)
        job_info_list.append(status)
    return job_info_list


def __parse_status(status_msg):
    """
    Parses a MiG status message.
    Returns a dictionary containing the same info.
    
    status_msg - a status message by the MiG server.
    """

    status_msg_lines = status_msg.split("\n")
    job_info = {}
    for line in status_msg_lines:
        ls = line.split(": ")
        if len(ls) > 1:
            job_info[ls[0].upper()] = ls[1].strip() 
    return job_info


def __miglib_function(func, *args):
    """
    A wrapper function for calling the miglib functions.
    Returns the MiG server output  message.
    
    Throws an exception when there is an error. 
    
    func - a miglib function.
    *args - one or more arguments to the miglib function.
    """
    
    if not LOCAL_MODE:
        __check_configuration()
        
    local_exit_code, server_out = func(*args)
    
    __debug("function %s \n args: %s \n miglib exit code : %s\n server message : %s\n" % (func.__name__, str(args), str(local_exit_code), str(server_out)))
    
    if local_exit_code != 0:
        raise MigLocalError(str(func)+":"+str(args)+"\n"+"".join(server_out), local_exit_code)
    
    server_exit_code = __extract_exit_code(server_out)
    if server_exit_code != 0:
        msg = "In method call %s%s \nServer message:\n%s" % (func.__name__, args, "".join(server_out))
        if server_exit_code == 100:
            raise MigUnknownJobIdError(msg, server_exit_code)
        else:
            raise MigServerError(msg, server_exit_code)
    
    return server_out
    

def __extract_exit_code(output_lines): # get internal MiG server exit code
    """
    Extracts the MiG server exit code from the server output message.
    Returns the exit code as an integer.
    
    output_lines - a list of strings for each line in the server output message.
    """
    code = 0
        
    if len(output_lines) > 0:
        output_lines_str = " ".join(output_lines)
        if output_lines_str.find('Exit code: ') != -1:
            tail = output_lines_str.split('Exit code:')[1]
            tokens = tail.strip(" ").split()
            code = tokens[0]     
    else:
        __debug("Empty output message (Not an error).")
        
    return int(code)

def __debug(message):
    """
    Writes a log message either to LOG_FILE or std.out (if the DEBUG_MODE=True). 
    
    message - a debug message.
    """
    logger = logging.getLogger(time.asctime())
    if DEBUG_MODE:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.DEBUG, filename=LOG_FILE)
    
    logger.debug(message)


def __check_configuration():
    
    if not os.path.exists(MIG_CONFIG):
        raise MigLocalError("Cannot find mig configuration file miguser.conf. It should be located at %s."% MIG_CONFIG)
    try:
        sys.modules["miglib"]
    except KeyError:
        raise MigLocalError("Cannot find miglib module")
    
    