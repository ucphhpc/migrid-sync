#import MiGuserscriptsInterface as Mig
import os
import time 
import shutil 
from mylogger import log


class MigSession:
    def __init__(self, local_project_results_dir, logfile, local=False, debugging=False):
        self.debug_mode = debugging
        if local:
            import localinterface
            self.mig = localinterface
        else:
            #import MiGuserscriptsInterface as Mig
            import miginterface
            self.mig = miginterface
            self.check_connection()
            
        
        #self.workingDir = workingDir
        self.main_results_dir = local_project_results_dir #destDir+EpiConfig.resultsdirPrefixName+job["projectTag"]+"/"
        self.logfile = logfile
#self.Mig.makeDirTree(self.workingDir)
        self.jobs = []
        
        
    def get_time(self):
        return time.strftime('%d/%m/%Y %H:%M:%S')


###### CREATE JOB ###############

    def create_mig_job(self,job):
        self.validate_job(job)
        os.mkdir(job['job_dir'])
        input_files = self.copy_files_to_local_working_dir(job["input_files"], job["job_dir"])
        job_file = self.write_job_to_file(job, job["job_dir"])
        input_files.append(job_file)
        
        job["input_files"] = input_files
        #print input_files
        job["commands"].insert(0,"cd "+job["job_dir"])
        job["id"]= self.mig.create_job(exec_commands=job["commands"], input_files=job["input_files"], 
                                      executables=[], local_working_dir=job["job_dir"], mig_working_dir=job["job_dir"], 
                                      output_files=job["output_files"], static_files=[], 
                                      resource_specs=job["resource_specs"])
        job["started"] = self.get_time()
        log(self.logfile,"Job created. Id :"+job["id"])

    def create_mig_jobs(self,jobs, working_dir, deploy_multiple=False):
        log(self.logfile, "Creating "+str(len(jobs))+" jobs", self.debug_mode)
        
        if not self.mig.path_exists(working_dir):
            self.mig.mk_dir(working_dir)
            
        if not os.path.exists(working_dir):
            os.mkdir(working_dir)
               
        if deploy_multiple:
            prepared_jobs = []
            for job in jobs:
                #prepared_jobs.append(
                mrsl_file = self.mig.prepare_job(exec_commands=job["commands"], 
                                            input_files=job["input_files"], executables=[], 
                                            local_working_dir=job["job_dir"], mig_working_dir=job["job_dir"], 
                                            output_files=job["output_files"], static_files=[], 
                                                 resource_specs=job["resource_specs"], 
                                            args=[job])
                job["mrsl_file"] = mrsl_file
            self.submit_prepared_jobs(jobs)
        else:
            for j in jobs:
                self.create_mig_job(j)

        return jobs
   
    def submit_prepared_jobs(self,jobs):
        job_dirs = map(lambda x : x["job_dir"],jobs)
        #mrsl_files = map(lambda x : x["mrsl_file"],jobs)
        jobs_archive = self.archive_job_dirs(job_dirs)
        self.mig.upload_files([jobs_archive],"")
        #job_ids = self.mig.submit_prepared_jobs(prepared_jobs)
        for j in jobs:
            j["id"] = self.mig.submit_job(j["mrsl_file"], j["job_dir"])
                
        
    def archive_job_dirs(self,job_dirs):
        import tarfile
        tmp_dir = "/tmp/"
        timestamp = str(time.time())
        tar_name = "inputfiles"+timestamp+".tar.gz"
        tar_path = tmp_dir+tar_name
        tar = tarfile.open(tar_path,"w:gz")
    
        for j in job_dirs:
            #filename = j.split("/")[-1]
            tar.add(j, j) 
        tar.close()
        return tar_path
            

    def write_job_to_file(self,job, dest_dir):
        import pickle
        #num = 0
        filename = dest_dir+"job_file.pkl"#"job"+str(num)+".pkl"
        output = open(filename, 'w')
        pickle.dump(job, output)
        output.close()
        
        return filename#arg_files

    def copy_files_to_local_working_dir(self,input_files, dest_dir):
        files = []
        for f in input_files: 
            cp_filename = dest_dir+f.split("/")[-1]
            shutil.copyfile(f ,cp_filename)
            files.append(cp_filename)
        
        return files    
    

    ######## OUTPUT ##########

    def handle_output(self,job):
        #import resultHandle
        files = []
        for f in job["output_files"]:
            output_filename =  job["job_dir"]+f
            outputfile = self.mig.get_output(output_filename, job["job_dir"])
            log(self.logfile, "Retrieved output file for job "+job["id"],self.debug_mode)
              #print "opening ", destDir+filepath, "to", destDir
            files.append(outputfile)
        return files
            #job_results_dir = self.main_results_dir#+job["results_dir"]
            #if not os.path.exists(job_results_dir):
            #    os.mkdir(job_results_dir)
            #log(self.logfile,"Extracting job output "+job["id"]+") to "+job_results_dir, self.debug_mode)
            #self.extract_output(outputfile, job_results_dir) # extract the downloaded archive file
            #self.cleanUpJob(job) # delete job files locally and on the MiG server

      ####### UPDATE/STATUS #########
  
    def update_jobs(self,jobs):
        new_status = False
        job_ids = map(lambda x : x["id"], jobs)
        #for j in jobs:
            #print j["id"]if j
        #print job_ids
        job_info_list = self.mig.get_status(job_ids)
        for i in range(len(jobs)):
            jobs[i]["status"] = job_info_list[i]
            
            if jobs[i]["status"]['STATUS'] == 'FINISHED':
                jobs[i]["finished"] = self.get_time()
            
            #print jobs[i]["id"], job_info_list[i]["ID"]
        #        map(lambda x : x["id"]=)
        
       # if not j.has_key("status") or jobInfo["STATUS"] != j["status"]["STATUS"]:
       #         j["status"] = jobInfo
        #        newStatus=True
        #if newStatus:
        #    self.PrintStatus(jobs)
        return jobs

    def wait_for_jobs(self, jobs):
        done = False
        while not done: 
            time.sleep(5)
            self.update_jobs(jobs)
            done = True
            
            for j in jobs :
                print j["status"]['STATUS']
                new_state = j["status"]['STATUS'] == 'FINISHED'
                done = done and new_state 
        
    ########## STOP/CANCEL #########

    def cancel_jobs(self,jobs):
        for j in jobs:
            self.cancel_job(j)

    def cancel_job(self,job):
        success = self.mig.cancel_job(job["id"])
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
        #filepaths = []
        job_files = []
        job_files.extend(job["input_files"]) # r files
        if job["status"]["STATUS"] == "FINISHED":
            outputfile = job["job_dir"]+job["output_files"][0]
            job_files.append(outputfile)
        
        log(self.logfile, "Cleaning up for job (id:"+job["id"]+")")
        self.mig.remove_files(job_files)
        self.remove_local_files(job_files)
               
        # locally 
#        if job["status"]["STATUS"] == "FINISHED":
 #           os.remove(job["output_files"][0])
        
        self.mig.remove_dir(job["job_dir"]) # directory
        os.rmdir(job["job_dir"])
        
        
    def remove_local_files(self,files):
      #clean up
        for f in files:
            #try: 
            os.remove(f)
            
        log(self.logfile, "Removed files locally : "+str(files), self.debug_mode)
 #except OSError:
             #   print "Can't delete : "+f
                
    def validate_job(self,job):
        required_keys = ["input_files", "output_files", "commands", "job_dir", "results_dir"]
        for key in required_keys:
            if not key in job.keys():
                raise Exception("Job error. MiG job dictionary must contain key "+key)
        

    def check_connection(self):
        success, func = self.mig.command_test()
        if not success:
            raise Exception("MiG connection error. Could not execute remote test command :"+str(func)+". You are propably not connected to MiG.")
    


        # locally
   #     for f in job_files:
    #        try:
    #            os.remove(f)
     #       except OSError:
      #          print "Could not delete file : "+f
       #     except IOError:
       #         print "Could not delete file : "+f

#        try:
#            os.rmdir(job["job_dir"])
#        except OSError:
#            print "Could not delete dir : "+job["job_dir"]
#        except IOError:
#            print "Could not delete file :"


