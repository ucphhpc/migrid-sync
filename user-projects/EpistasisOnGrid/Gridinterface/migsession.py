import os
import time 
import shutil 
from mylogger import log
import miginterface as mig

class Migsession:
    def __init__(self, local_project_results_dir, logfile, local=False, debugging=False):
        self.debug_mode = debugging
        
        if local:
            mig.local_mode_on()
        
        self.main_results_dir = local_project_results_dir 
        self.logfile = logfile
        self.jobs = []
        
        
    def get_time(self):
        return time.strftime('%d/%m/%Y %H:%M:%S')

###### CREATE JOB ###############

    def create_mig_job(self,job):
        self.validate_job(job)

        job["id"]= mig.create_job(exec_commands=job["commands"], input_files=job["input_files"],                                     
                                      output_files=job["output_files"],
                                      resource_specifications=job["resource_specs"])
        job["started"] = self.get_time()
        log(self.logfile,"Job created. Id :"+job["id"])

    def create_mig_jobs(self,jobs):
        log(self.logfile, "Creating "+str(len(jobs))+" jobs", self.debug_mode)
             
        for j in jobs:
            self.create_mig_job(j)
            print "migsession: mig job created"
        return jobs
   
    ######## OUTPUT ##########

    def handle_output(self,job):
        #import resultHandle
        files = []
        for f in job["output_files"]:
            output_filename =  f
            outputfile = mig.get_file(output_filename, f)
            log(self.logfile, "Retrieved output file for job "+job["id"],self.debug_mode)
              #print "opening ", destDir+filepath, "to", destDir
            files.append(outputfile)
        return files
   
      ####### UPDATE/STATUS #########
  
    def update_jobs(self,jobs):
        new_status = False
        job_ids = map(lambda x : x["id"], jobs)
        job_info_list = mig.jobs_status(job_ids)
        if len(job_info_list) != len(job_ids):
            print str(job_info_list)
            print str(jobs)
            raise Exception("Critical job management error.  Job list lengths.")

        for i in range(len(jobs)):
            jobs[i]["status"] = job_info_list[i]

            if mig.job_finished(jobs[i]["id"]):
                jobs[i]["finished"] = self.get_time()
        
        print "update jobs", jobs
        
        return jobs

    ########## STOP/CANCEL #########

    def cancel_jobs(self,jobs):
        for j in jobs:
            self.cancel_job(j)

    def cancel_job(self,job):
        success = mig.cancel_job(job["id"])
        if success: 
            #print "Cancelled job : "+job["id"]
            log(self.logfile,"Cancelled job : "+job["id"],self.debug_mode)
        else:
            log(self.logfile,"Unsuccesful cancellation of job :"+job["id"],self.debug_mode)
            #mylogger.logprint(logfile,"Unsuccesful cancellation of job :"+job["id"])
        #self.cleanUpJob(job)

    ###### CLEAN UP/DELETE ###########

    def clean_up(self,jobs):
        for j in jobs:
            self.clean_up_job(j)

    def clean_up_job(self,job):
        job_files = []
        job_files.extend(job["input_files"]) # r files
        if job["status"]["STATUS"] == "FINISHED":
            outputfile = job["job_dir"]+job["output_files"][0]
            job_files.append(outputfile)
        
        log(self.logfile, "Cleaning up for job (id:"+job["id"]+")")
        mig.remove_files(job_files)
        self.remove_local_files(job_files)
               
        #mig.remove_dir(job["job_dir"]) # directory
        #os.rmdir(job["job_dir"])
        
        
    def remove_local_files(self,files):
      #clean up
        for f in files:
            #try: 
            os.remove(f)
            
        log(self.logfile, "Removed files locally : "+str(files), self.debug_mode)
                 
    def validate_job(self,job):
        required_keys = ["input_files", "output_files", "commands", "results_dir"]
        for key in required_keys:
            if not key in job.keys():
                raise Exception("Job error. MiG job dictionary must contain key "+key)
        

    def check_connection(self):
        success = mig.test_connection()
        if not success:
            raise Exception("MiG connection error. Could not execute remote test command :"+str(func)+". You are propably not connected to MiG.")
