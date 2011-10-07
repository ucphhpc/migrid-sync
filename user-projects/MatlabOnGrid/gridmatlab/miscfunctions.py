import configuration as config
import logging, time, cPickle, os
import miginterface as mig
import fcntl


        
def read_pickle_file(path):
    f = open(path)
    data = cPickle.load(f)
    f.close()
    return data



def upload_file(file_item, path):
    
    msg = ""
    returncode = 0
    try:
        upload_fd = open(path, 'wb')
        while True:
            chunk = file_item.file.read()
            if not chunk:
                break
            upload_fd.write(chunk)
        upload_fd.close()
        log('Wrote %s' % path)
        msg = "Wrote file "+ path
    except Exception, exc:
        msg = "Error: %s" % str(exc)
        returncode = 1
         # TODO : correct this
        # Don't give away information about actual fs layout

    return returncode, msg


def update_solver_data(name, status="", state=""):
    """
    Write the current status to the status file. 
    """
    
    job_data_dir = os.path.join(config.jobdata_directory, name)
    solver_data_path = os.path.join(job_data_dir, config.solver_data_file)
    data_file = open(solver_data_path)
    
    fcntl.flock(data_file, fcntl.LOCK_EX)  # lock the file while updating
    
    solver_data = cPickle.load(data_file)
    data_file.close()
    
    
    if solver_data.has_key("grid_enabled") and not solver_data["grid_enabled"]:
        mig.local_mode_on()
    for job in solver_data["timesteps"][-1]["jobs"]: # Go through the jobs in the current time step (indexed last: -1)
        job_info = mig.job_info(job["job_id"])

        for (key, value) in job_info.items():
            job_info.pop(key)
            job_info[key.lower()] = value
        
        
        job.update(job_info)
    
    if status:
        solver_data["timesteps"][-1]["status"] = status
   
    if state: 
        solver_data["state"] = state
    
    fh = open(solver_data_path, "w")
    cPickle.dump(solver_data, fh)
    fcntl.flock(fh, fcntl.LOCK_UN) # unlock again
    
    fh.close()
    
    
    
def save_solver_data(name, solver_data):
    solver_data_path = os.path.join(config.jobdata_directory, name, config.solver_data_file)
    fh = open(solver_data_path, "w")
    
    fcntl.flock(fh, fcntl.LOCK_EX)
    cPickle.dump(solver_data, fh)
    fcntl.flock(fh, fcntl.LOCK_UN)
    
    fh.close()

def load_solver_data(name):
    job_data_dir = os.path.join(config.jobdata_directory, name)
    solver_data_path = os.path.join(job_data_dir, config.solver_data_file)
    data_file = open(solver_data_path)
    
    fcntl.flock(data_file, fcntl.LOCK_SH)
    data_dict = cPickle.load(data_file)
    fcntl.flock(data_file, fcntl.LOCK_UN)
    
    data_file.close()
    return data_dict
    
    

def log(message):
    """
    Writes a log message either to LOG_FILE or std.out (if the DEBUG_MODE=True). 
    
    message - a debug message.
    """
    LOG_FILE = config.log_file
    
    logger = logging.getLogger(time.asctime())
    print_format = '%(asctime)s %(message)s'

    
    logging.basicConfig(level=logging.DEBUG, filename=LOG_FILE, format=print_format)
    
    logger.debug(message)