import configuration as config
import logging, time, cPickle, os 


def get_process_data(name):
    job_data_dir = os.path.join(config.jobdata_directory, name)
    solver_data_path = os.path.join(job_data_dir, config.solver_data_file)
    data = read_pickle_file(solver_data_path)
    return data
        
        
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



def log(message):
    """
    Writes a log message either to LOG_FILE or std.out (if the DEBUG_MODE=True). 
    
    message - a debug message.
    """
    LOG_FILE = config.log_file
    
    logger = logging.getLogger(time.asctime())
    logging.basicConfig(level=logging.DEBUG, filename=LOG_FILE)
    
    logger.debug(message)