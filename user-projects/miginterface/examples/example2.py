#!/usr/bin/python 

"""
Example script for running a MiG job using the python miginterface module.
"""

import miginterface as mig
import time, os, sys

def main():
    """
    Executes the bash file test_executable.sh in a grid job. 
    Afterwards, the result is downloaded and printed to screen.
    """

    # mig.debug_mode_on() # uncomment to enable debug print outs
    # mig.local_mode_on() # uncomment to enable local mode execution
    
    mig.test_connection() # Check if we can connect to the MiG server

    # The program we want to execute on the grid
    executable_file = "test_executable.sh"
    # The shell command to execute on the grid resource
    cmd = "./test_executable.sh > out.txt"
    # Create and submit the grid job
    job_id = mig.create_job(cmd, output_files=["out.txt"], executables=[executable_file])
    print "\nJob (ID : %s) submitted. \n\n" % job_id
    
    # Wait for the job to finish while monitoring the status
    polling_frequency = 10 # seconds
    while not mig.job_finished(job_id):
        job_info = mig.job_info(job_id) # get an info dictionary
        print 'Grid job : %(ID)s \t %(STATUS)s ' % job_info
        time.sleep(polling_frequency) # wait a while before polling again

    # Download the result file and print
    output_file = mig.get_file("out.txt")
    f = open(output_file)
    print "Output file (%s) contains :\n %s \n\n" % (output_file, str(f.readlines()))
    f.close()

    # Clean up
    os.remove(output_file) # remove locally
    mig.remove(output_file) # remove on the MiG server
    print "Output ("+output_file+") deleted."

if __name__ == "__main__":
    if "-l" in sys.argv:
        mig.local_mode_on()
    if "-d" in sys.argv:
        mig.debug_mode_on()
        
    main()
