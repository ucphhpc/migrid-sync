#!/usr/python

"""
Example script for running a MiG job using the python miginterface module.
"""

import miginterface as mig
import time
import os


def main():
    """
    Executes the bash file test_executable.sh in a grid job. 
    Afterwards, the result is downloaded and printed to screen.
    """

    # Dissable verbose print outs
    mig.set_debug_mode(False)

    # Check if we can connect to the MiG server
    if not mig.mig_test_connection():
        print "Connection error."
        exit(1)

    # The program we want to execute on the grid
    bash_file = "test_executable.sh"
    # The shell command to execute on the grid resource
    cmd = "./test_executable.sh > out.txt"

    # Create and submit the grid job
    job_id = mig.mig_create_job(cmd, output_files=["out.txt"], executables=[bash_file])
    print "\nJob (ID : %s) submitted. \n\n" % job_id

    # Wait for the job to finish while monitoring the status
    polling_frequency = 10 # seconds
    while not mig.mig_job_finished(job_id):
        job_info = mig.mig_job_info(job_id) # get an info dictionary
        print 'Grid job : %(ID)s \t %(STATUS)s ' % job_info
        time.sleep(polling_frequency) # wait a while before polling again

    # Download the result file and print
    output_file = mig.mig_get_file("out.txt")
    f = open(output_file)
    print "Output file (%s) contains :\n %s \n\n" % (output_file, str(f.readlines()))
    f.close()

    # Clean up
    os.remove(output_file) # remove locally
    mig.mig_remove(output_file) # remove on the MiG server
    print "Output ("+output_file+") deleted."

if __name__ == "__main__":
    main()
