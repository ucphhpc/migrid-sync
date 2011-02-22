#!/usr/bin/python 

"""
An example script for running an MPI grid job using the mig interface module.
"""

import miginterface as mig
import time, sys

def main():
    """
    Run an mpi job on a grid resource. To run in local mode please install mpi.
    """

    # mig.debug_mode_on() # uncomment to enable debug print outs
    # mig.local_mode_on() # uncomment to enable local mode execution
     
    mig.test_connection() # Check if we can connect to the MiG server
    mpi_file = "example.c" # mpi program source file
    
    # The shell command to execute on the grid resource using 4 processes. We need to it compile on the resource first.
    cmds = ["mpicc -O2 example.c -o example", "$MPI_WRAP mpirun -np 4 ./example Hello"]

    # specify that we need require MPI as a runtime env and use the DIKU vgrid cluster
    specifications = {"RUNTIMEENVIRONMENT":"MPI-WRAP-2.0", "VGRID":"DIKU"}
    # Create and submit the grid job
    job_id = mig.create_job(cmds, input_files=mpi_file, resource_specifications=specifications)
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
