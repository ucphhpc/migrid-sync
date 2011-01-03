#! /usr/bin/python

import time
import os
import sys
import cPickle

import Configuration.epistasisconfiguration as configuration
import Gridinterface.migsession as migsession
from Gridinterface.mylogger import log
from misc.jobfragmentation import fragment_epistasis, get_job_specs, create_epistasis_jobs

########### UPDATE / STATUS ###############

def get_epistasis_status(epistasis_jobs):
    """Return the status of the jobs and a progress indicator to be displayed in GUI."""
    mig_session.update_jobs(epistasis_jobs)
    jobs_done = []

    for j in epistasis_jobs:
        if j["status"] == "FINISHED":
            jobs_done.append(j)
            output_files = mig_session.handle_output(j)
            for f in output_files:
                result_dir = os.path.join(configuration.output_dir,j['results_dir'])
                extract_output(f, result_dir)

    if len(epistasis_jobs) == len(jobs_done):
        log(logfile, 'All jobs completed', debug)
        epistasis_status = 'finished'

    progress_str = str(len(jobs_done)) + '/'\
         + str(len(epistasis_jobs))
    status_lines = create_status_feed(epistasis_jobs)
    status_lines.extend(create_status_feed(jobs_done))
    status = ""
    for line in status_lines:
        status += line + '\n'
    return status, progress_str


def download_output(j):
    output_files = mig_session.handle_output(j)
    for f in output_files:
        result_dir = os.path.join(configuration.output_dir,j['results_dir'])
        extract_output(f, result_dir)

########### UPDATE / STATUS ###############


def update_epistasis(epistasis_jobs):
    mig_session.update_jobs(epistasis_jobs)
    return epistasis_jobs

def create_status_feed(jobs):
    """Return a status string for each job"""
    feed = []
    for j in jobs:
        line = create_status_str(j)
        feed.append(line)
    return feed

def create_status_str(job):
    """Return a status string for a job"""
    status_str = 'Epistasis \t - class '
    for val in job['class']:
        status_str += str(val) + ' '
    status_str += '-'+ '\t' + job['status']
    if job['status'] != "EXECUTING":
        status_str += "\t"
    status_str += ' \t started:'+job["started"]+'\t \t ended:'+job["finished"]
    return status_str


def extract_output(tar_file_path, dest_dir):
    import tarfile

    new_dir = os.path.join(dest_dir,os.path.basename(tar_file_path).strip(".tar.gz"))
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
    prog_files = tarfile.open(tar_file_path, "r")

    prog_files.extractall(path=new_dir)
    

    prog_files.close()
    print "Extracted %s to %s ." % (tar_file_path, new_dir)
 
# ######### START EPISTASIS ############

def start_epistasis(
    selection_variable_values = configuration.default_variable_values,
    genelist=configuration.default_gene_list,
    traitlist=configuration.default_trait_list,
    selection_variable=configuration.default_selection_variable_index,
    data=configuration.data_file,
    output_dir=configuration.output_dir,
    job_size=configuration.default_job_size,
    local_mode=False,
    ):
    """Start the epistasis procedure."""

    time_list = time.localtime(time.time())
    project_tag = str(time_list[2]) + '_' + str(time_list[1]) + '_'\
     + str(time_list[0]) + '_' + str(time_list[3])\
     + str(time_list[4]) + str(time_list[5])
    
    # create the epistastis jobs
    epi_jobs, project_dir = create_epistasis_jobs(
        job_size,
        genelist=genelist,
        traitlist=traitlist,
        selection_var=selection_variable,
        variable_values=selection_variable_values,
        data_file=data,
        output_dir=output_dir,
        project_tag=project_tag,
        run_local=local_mode,
        )
    main_output_dir = output_dir

    # make an output dir
    proj_output_dir = os.path.join(output_dir,project_dir)
    os.mkdir(proj_output_dir)
    
    # create and submit the epistasis jobs
    migjobs = mig_session.create_mig_jobs(epi_jobs)
    
    # create a status file
    pklfile_path = os.path.join(configuration.running_jobs_dir, project_tag)+".pkl"
    # create a status file dir
    if not os.path.exists(configuration.running_jobs_dir):
        os.mkdir(configuration.running_jobs_dir)
    # save the file
    f = open(pklfile_path, "w")
    cPickle.dump(epi_jobs, f)
    f.close()
    print "The gridepistasis has been started. Use \n python gridepistasis.py -u %s \n to get an update of the job." % pklfile_path
    
    return migjobs

########## STOP /CANCEL ##############

def stop_epistasis(jobs):
    """Stop the epistasis procedure."""
    mig_session.cancel_jobs(jobs)

###### PRINT ###########

def print_jobs(self, jobs):
    """Print jobs."""
    for i in range(len(jobs)):
        print 'job ' + str(i) + ' : ' + str(jobs[i])

def print_status(self, jobs):
    """Print job status."""
    full_str = []
    for j in jobs:
        status_str = 'Job : ' + j['id'] + '\t' + j['status'
                ]['STATUS']
        print status_str
        full_str.append(status_str)
    return full_str

# ### CLEAN UP ########

def clean_up_epistasis(jobs):
    """Delete files used in the epistasis procedure that are no longer needed."""
    mig_session.clean_up(jobs)

###### MAIN ###############

# Arguments are entered in the order: selectionvariableindex jobsize

local = False
debug = False

if '-local' in sys.argv or '-l' in sys.argv:
        local = True
        # set up the needed mig job runtime environment
        os.putenv("PYTHON", "/usr/bin/python")
        os.putenv("R_HOME", "/usr/lib/R")
if '-debug' in sys.argv or '-d' in sys.argv:
        debug = True
logfile = configuration.output_dir+configuration.logfile_name
mig_session = migsession.Migsession(configuration.output_dir, logfile, local, debug)

if __name__ == '__main__':
    if '-u' in sys.argv :
        i = sys.argv.index("-u")
        pkl_file = open(sys.argv[i+1], "r+")
        jobs = cPickle.load(pkl_file)
        print get_epistasis_status(jobs)
        cPickle.dump(jobs, pkl_file)
        pkl_file.close()
        
    else:
        start_epistasis(local_mode=local)
