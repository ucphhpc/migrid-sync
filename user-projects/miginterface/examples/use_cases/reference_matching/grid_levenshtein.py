"""
Script for running reference matching on grid using the python miginterface module.
"""

import miginterface as mig
import time, os, sys


def create_blocks(reference_file, block_size):
    """
    create block files of block_size lines
    """

    block_num = 0
    
    ref_file = open(reference_file)
    block_files = []    
    
    while True:       
        block_filename = "block%i.txt" % block_num
        block_num += 1
        
        block = []
        for l in range(block_size):
            line = ref_file.readline()
            if not line:
                break
            block.append(line)
        
        if not block:  
            break
        block_file = open(block_filename, "w")
        block_file.writelines(block)
        block_file.close()
        block_files.append(block_filename)
        
    ref_file.close()
    return block_files
    


def main():
    """
    Find edit distance value between entries in a reference file. First, divide the file into smaller blocks 
    and create a grid job for each. levenshtein.py is used to process each input block.
    When a job has finished executing, the corresponding output file is downloaded.
    """
    
    # mig.debug_mode_on() # uncomment to enable debug print outs
    # mig.local_mode_on() # uncomment to enable local mode execution 

    reference_file = "ref1000.txt"
    # The reference blocks. One for each job we want to run.
    block_files = create_blocks(reference_file, block_size=200)
    
    # These are static input files for each job. 
    levenshtein_files = ["Levenshtein_ucs4.so", "Levenshtein_ucs2.so", "levenshtein.py", "Levenshtein_i686.so"]
        
    resource_requirements = {}
    resource_requirements["RUNTIMEENVIRONMENT"] = "PYTHON-2" # we need python on the resource
    resource_requirements["VGRID"] = "ANY"
    
    jobs = []
    
    # Start a grid job for each block file
    for block_file in block_files:
        output_file = block_file.strip(".txt")+"_output.txt"
        cmd = "$PYTHON levenshtein.py %s > %s" % (block_file, output_file)
        input_files = []
        input_files.extend(levenshtein_files)
        input_files.append(block_file)
        job_id = mig.create_job(cmd, input_files=input_files, output_files=output_file,resource_specifications=resource_requirements)
        jobs.append((job_id, output_file))
        print "started job %s" % job_id
    
    jobs_done = 0
    # now wait for the results 
    while len(jobs):
        print "Checking job status. jobs done : %i." % jobs_done 
        try:  
            for job_id, result_file in jobs:
                print "Checking job %s." % job_id
                if mig.job_finished(job_id):
                    if not os.path.exists("output"):
                        os.mkdir("output")
                    mig.get_file(result_file, "output/"+result_file)
                    jobs.remove((job_id, result_file))
                    jobs_done += 1
                    
                    print "Job done. Downloaded result file %s." % result_file
                    
    
            time.sleep(10) # wait a little before polling
        except KeyboardInterrupt:
            job_ids = [x[0] for x in jobs]
            mig.cancel_jobs(job_ids)
            print "Cancelled jobs."
            break

if __name__ == "__main__":
    if "-l" in sys.argv:
        mig.local_mode_on() 
        if not os.getenv("PYTHON"):
            os.putenv("PYTHON", "/usr/bin/python")
    if "-d" in sys.argv:
        mig.debug_mode_on()
    
    main()

