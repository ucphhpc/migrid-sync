#!/usr/python

"""
Example script for running multiple MiG jobs using the python miginterface module.
"""

import miginterface as mig
import time, os, sys


def main():
    """
    Run five grid jobs executing the bash file parameter_sweet_script.sh with different input arguments.
    When a job has finished executing, the corresponding output file is downloaded.
    Finally, the output contents are printed.
    """
    
    # mig.debug_mode_on() # uncomment to enable debug print outs
    # mig.local_mode_on() # uncomment to enable local mode execution
    mig.test_connection() # Check if we can connect to the MiG server
    
    input_values = range(5) # Input parameters
    # The program we want to execute on grid resources
    executable_file = "parameter_sweep_script.sh"

    print "\nStarting grid jobs:\n"

    jobs = []
    for i in input_values:     # Start a job for each input
        output_file = "output%s.txt" % i # The output file name
        # The shell command to start the script on the resource
        cmd = "./parameter_sweep_script.sh %i > %s" % (i, output_file)
        # Run the job resources on any vgrid 
        resource_requirements = {"VGRID":"ANY", "JOBTYPE": "ARC"}
        # Start the grid job
        job_id = mig.create_job(cmd, output_files=[output_file], executables=[executable_file], resource_specifications=resource_requirements)
        jobs.append((job_id, output_file))
        print "Job (ID : %s) submitted." % job_id
    print "\n\n"

    print "Monitor job status...\n" # Now we wait for results

    finished_jobs = []
    while len(finished_jobs) < len(jobs):
        for id, output_file in jobs:
            job_info = mig.job_info(id) # get an info dictionary
            print 'Grid job : %(ID)s \t %(STATUS)s ' % job_info
            if mig.job_finished(id) and id not in finished_jobs:
                # Download the output file from the server
                mig.get_file(output_file)
                finished_jobs.append(id)
                mig.remove(output_file) # clean up the result file on the server

        time.sleep(10) # Wait a few seconds before trying again
        print "\n\n"

    print "All jobs finished."
    # Clean up the result files and print out the contents
    print "Cleaning up."
    output_lines = []
    for _, output_file in jobs:
        fh = open(output_file)
        output_lines.append(" ".join(fh.readlines()))
        fh.close()
        os.remove(output_file)
        print "Output file ("+output_file+") deleted."

    print "\n\nOutput contents : \n\n%s\n" % "\n".join(output_lines)

if __name__ == "__main__":
    if "-l" in sys.argv:
        mig.local_mode_on() 
    if "-d" in sys.argv:
        mig.debug_mode_on()
    
    main()
