"""
matlab on grid
"""

import miginterface as mig
import migerror
import time, logging, os, sys, shutil
import cPickle
import configuration as config
from miscfunctions import log, load_solver_data, update_solver_data, save_solver_data
import subprocess


# process states
STATE_RUNNING = "Running"
STATE_CANCELLED = "Cancelled"
STATE_FINISHED = "Finished"
STATE_FAILED = "Failed"


def update(status,state):
    update_solver_data(proc_name, status=status, state=state)

#def save(status="",state=""):
#    u_solver_data(proc_name, status, state)

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


def submit_job(exec_sh, exec_bin, files, output, argstr):
    """
    start a grid job that runs the matlab code
    """

    matlab_RTE = config.matlab_rte
    execute_cmd = "./%s %s %s" % (exec_sh, matlab_RTE, argstr)
    job_id = mig.create_job(execute_cmd, executables=[exec_sh, exec_bin], input_files=files, output_files=output, resource_specifications=config.mig_specifications)
    
    return job_id
    
def submit_jobs(exec_sh, exec_bin, input_files, numjobs, timestep):
    """
    Start the grid jobs
    """
    
    job_nr = 0
    jobs = []
    print input_files
    for i in range(1, numjobs+1):
        
        # these names must match the ones in the matlab executable
        output1 = "value_rent_index_job"+str(i)+".txt"
        output2 = "policy_rent_index_job"+str(i)+".txt"
        
        output = [output1, output2]
        
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
  
    while True:
        finished = [] 
        for j in jobs:
            
           
            try: 
                j_done = mig.job_finished(j["job_id"])
            
            except migerror.MigInterfaceError, e:
                log(str(e))
                j_done = False
                
            if j_done:
                if not download_result(j):
                    update(status="Error: Could not find result", state=STATE_FAILED)
                    return 1 # error
                finished.append(j)
            
                
            
        update(status="waiting for jobs", state=STATE_RUNNING)
        if len(jobs) == len(finished):
            update(status="iteration finished", state=STATE_RUNNING)
            return 0 # success
        time.sleep(config.POLLING_INTERVAL)
    
       
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

    final_step = config.FINAL_TIMESTEP
    solver_data = {}
    solver_data["timesteps"] = []
    solver_data["pid"] = os.getpid()
    solver_data["name"] = proc_name
    solver_data["total_timesteps"] = timesteps
    solver_data["grid_enabled"] = grid_enabled
    
    save_solver_data(proc_name, solver_data)
    for t in range(timesteps, final_step, -1): # decending from timesteps         print "starting new time step: ",t
        global timestep
        timestep = str(t)#solver_data["timestep"] = t
        
        
        grid_jobs = submit_jobs(matlab_sh, matlab_bin, files, number_of_jobs, timestep)
        timestep_data = {"jobs" : grid_jobs, "timestep" : timestep}
        solver_data = load_solver_data(proc_name)
        solver_data["timesteps"].append(timestep_data)
        
        save_solver_data(proc_name, solver_data)
        
        update(status="starting iteration", state=STATE_RUNNING)
        exit_code = monitor_timestep(grid_jobs) # returns when jobs are done
        
        if exit_code:
            print "Monitor error."
            return 1
        
        postprocess()
        
        log(timestep+" done. starting next")
        
    
    clean_up(files)
    return 0
    

matlab_exec_sh = config.matlab_executable
matlab_files = config.upload_directory

#mig.debug_mode_on()
#mig.local_mode_on()

timestep = str(config.INIT_TIMESTEP)
input_files = []
num_jobs = 2
proc_name = None
grid_enabled = True

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
            grid_enabled = False
        print "Local mode!"
        
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

try :

    exit_code = main_solver(os.path.basename(matlab_exec_sh), os.path.basename(matlab_exec_bin), files, num_jobs, config.INIT_TIMESTEP)

except Exception, e:
    log(str(e))
    exit_code = 2
    
if not exit_code:
    update(state=STATE_FAILED, status="An error execution occurred.")
else :
    update(status="grid execution completed", state=STATE_FINISHED)
    