"""
matlab on grid
"""

import miginterface as mig
import time, logging, os, sys, shutil
import cPickle
import configuration as config
from miscfunctions import log 
import subprocess


def create_grid_execution_dir(name):
    if os.path.exists(os.path.join(config.jobdata_directory, name)):
        timestamp = str(time.time())
        name += timestamp
    new_dir = os.path.join(config.jobdata_directory, name) 
    os.mkdir(new_dir)
    return new_dir

def prepare_execution(name, files):
    """
    Stage files for execution. Create a working directory for the process and copy all needed file here. 
    """
    
    exec_dir = create_grid_execution_dir(name)
    
    files.append(config.postprocessing_code) # copy the summarize file to job dir 
    
    for f in files:
        shutil.copy(f, os.path.join(exec_dir,  os.path.basename(f)))
    
    os.chdir(exec_dir) # jump to the jobs own execution dir


def dump_data(data, filename):
    fh = open(filename, "w")
    cPickle.dump(data, fh)
    fh.close()


def update_solver_data(utility_file="", status=""):
    """
    Write the current status to the status file. 
    """
    timestep_data = solver_data["timesteps"][-1] # get the last element
        
    for job in timestep_data["jobs"]: #= mig.jobs_info(job_ids)
        job["status"] = mig.job_status(job["job_id"])
    
    if utility_file:
        timestep_data["utility_file"] = utility_file
    
    if status:
        timestep_data["status"] = status
   
    global solver_data_file
    dump_data(solver_data, solver_data_file)


def submit_job(exec_sh, exec_bin, files, output, argstr):
    """
    start a grid job that runs the matlab code
    """

    matlab_RTE = config.matlab_rte
    execute_cmd = "./%s %s %s" % (exec_sh, matlab_RTE, argstr)
    job_id = mig.create_job(execute_cmd, executables=[exec_sh, exec_bin], input_files=files, output_files=output, resource_specifications={"VGRID":"DIKU", "RUNTIMEENVIRONMENT":"MATLAB_MCR", "MEMORY":"2000"})
    
    return job_id
    
def submit_jobs(exec_sh, exec_bin, input_files, numjobs, timestep):
    """
    Start the grid jobs
    """
    
    job_nr = 0
    job_ids = []
    jobs = []
    print input_files
    for i in range(1, numjobs+1):
        output = ["value_rent_index_job"+str(i)+".txt", "policy_rent_index_job"+str(i)+".txt"]
        
        jid = submit_job(exec_sh, exec_bin, input_files, output, argstr="%s %s" % (i, timestep))
        job = {"job_id" : jid, "result_files" : output, "status":"submitted", "worker_index": i }
        jobs.append(job)
        job_nr += 1
    
    return jobs
    
    
def clean_up(files):
    """
    delete the files
    """
    for f in [os.path.basename(f) for f in files]:
        mig.remove(f)
    
    uploaded_files = os.listdir(config.upload_directory)
    for f in uploaded_files:
        os.remove(os.path.join(config.upload_directory, f))


def download_result(job):
    dl_files = []
    result_files = job["result_files"]
    for f in result_files: 
        if mig.path_exists(f):
            dl = mig.get_file(f)
            dl_files.append(dl)
        else:
            return []
            
    return dl_files

# monitor jobs

def monitor_timestep(jobs):
    SLEEP_INTERVAL = 5

    while True:
        finished = [] 
        for j in jobs:
            
            if mig.job_finished(j["job_id"]):
                if not download_result(j):
                    update_solver_data(status="Error: Could not find result")
                    return 1 # error
                finished.append(j)
            
        update_solver_data(status="waiting for jobs")
        if len(jobs) == len(finished):
            update_solver_data(status="iteration finished")
            return 0 # success
        time.sleep(SLEEP_INTERVAL)
    
       
def postprocess():
    """
    run this code between each iterations. Merges the results using matlab code.
    """
    cmd = "matlab -nodesktop -nojvm -r '%s(%i);quit();'" % (os.path.basename(config.postprocessing_code)[:-2], num_jobs)
    log("Post processing...." )
    print cmd
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    #if err:
    log(" ".join([out, err]))


def main_solver(matlab_sh, matlab_bin, files, number_of_jobs, timesteps=80):
    """
    The main solver file start grid jobs for every timestep.
    """

    final_step = 20
    solver_data["timesteps"] = []
    for t in range(timesteps, final_step, -1): # decending from timesteps         print "starting new time step: ",t
        global timestep
        timestep = str(t)#solver_data["timestep"] = t
        solver_data["pid"] = os.getpid()
        
        grid_jobs = submit_jobs(matlab_sh, matlab_bin, files, number_of_jobs, timestep)
        timestep_data = {"jobs" : grid_jobs, "timestep" : timestep}
        solver_data["timesteps"].append(timestep_data)
       
        update_solver_data(status="starting iteration")
        exit_code = monitor_timestep(grid_jobs) # returns when jobs are done
        
        if exit_code:
            print "Monitor error."
            return
        
        postprocess()
        
        log(timestep+" done. starting next")
        
    update_solver_data(status="grid execution completed")
    
    clean_up(files)
    return
    

matlab_exec_sh = config.matlab_executable
matlab_files = config.upload_directory

#mig.debug_mode_on()
#mig.local_mode_on()

solver_data = {}
solver_data_file = config.solver_data_file
INIT_TIMESTEP = config.INIT_TIMESTEP
timestep = str(INIT_TIMESTEP)
input_files = []
num_jobs = 2

if len(sys.argv) > 1:
    proc_name = sys.argv[1]
    matlab_exec_sh = sys.argv[2]
    matlab_exec_bin = sys.argv[3]
    
    if "-n" in sys.argv:
        pos = sys.argv.index("-n")
        num_jobs = int(sys.argv[pos+1])

    if "-l" in sys.argv:
        mig.local_mode_on()
        if not os.getenv("MATLAB_MCR"):
            os.putenv("MATLAB_MCR", config.MCR_path)
        
    if "-i" in sys.argv:
        pos = sys.argv.index("-i")
        input_files.extend(sys.argv[pos+1:])
    
else:
    print "USAGE : %s NAME EXECUTABLES -n NUM_JOBS -i INPUTFILE_0 INPUTFILE_N" % sys.argv[0]
    exit(0)

input_files.append(matlab_exec_sh)
input_files.append(matlab_exec_bin)

prepare_execution(proc_name, input_files) # copy all files to execution directory
files = [os.path.basename(f) for f in input_files]

main_solver(os.path.basename(matlab_exec_sh), os.path.basename(matlab_exec_bin), files, num_jobs, INIT_TIMESTEP)
