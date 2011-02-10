#!/usr/python
"""
Example script for running a MiG job using the python miginterface module.
"""

import miginterface as mig
import time, sys

def main():
    """
    Execute a simple grid job and print the output.
    """
    
    # mig.debug_mode_on() # uncomment to enable debug print outs
    # mig.local_mode_on() # uncomment to enable local mode execution

    # Check if we can connect to the MiG server
    mig.test_connection()

    # Create and submit the grid job
    job_id = mig.create_job("echo HELLO GRID")
    print "\nJob (ID : %s) submitted. \n\n" % job_id

    # Wait for the job to finish while monitoring the status
    polling_frequency = 10 # seconds
    while not mig.job_finished(job_id):
        job_info = mig.job_info(job_id) # get an info dictionary
        print 'Grid job : %(ID)s \t %(STATUS)s ' % job_info
        time.sleep(polling_frequency) # wait a while before polling again
    
    print mig.job_output(job_id)
    
if __name__ == "__main__":
    if "-l" in sys.argv:
        mig.local_mode_on()
    if "-d" in sys.argv:
        mig.debug_mode_on()
        
    main()
