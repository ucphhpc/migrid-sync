#!/usr/bin/python 

"""
An example script for running an MPI grid job using the mig interface module.
"""

import miginterface as mig
import time, sys


def main():
    """
    Run an pvm job on a grid resource. To run in local mode please install pvm
    """

    # mig.debug_mode_on() # uncomment to enable debug print outs
    # mig.local_mode_on() # uncomment to enable local mode execution
    
    
    mig.test_connection() # Check if we can connect to the MiG server
    
    pvm_program = "example" # The PVM executable
    cmd = "$PVM_WRAP ./example 4 Hello" # The shell command to execute on the grid resource

    # specify to the job that we want PVM as RTE and we want to use the DIKU VGRID
    specifications = {"RUNTIMEENVIRONMENT":"PVM-WRAP-1.0", "VGRID":"DIKU"}
    
    # Create and submit the grid job
    job_id = mig.create_job(cmd, executables=pvm_program, resource_specifications=specifications)
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
