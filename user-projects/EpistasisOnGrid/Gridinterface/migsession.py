#import MiGuserscriptsInterface as Mig
import os

class MigSession:
    def __init__(self, results_dir, local=False):
        if local:
            import localinterface as mig
        else:
            #import MiGuserscriptsInterface as Mig
            import miginterface as mig
        self.mig = mig
        #self.workingDir = workingDir
        self.main_results_dir = results_dir #destDir+EpiConfig.resultsdirPrefixName+job["projectTag"]+"/"
        #self.Mig.makeDirTree(self.workingDir)
        self.jobs = []

###### CREATE JOB ###############

    def create_mig_job(self,job):
        job["id"]= self.mig.create_job(exec_commands=job["commands"], input_files=job["input_files"], 
                                      executables=[], local_working_dir=job["job_dir"], mig_working_dir=job["job_dir"], 
                                      output_files=job["output_files"], static_files=[], vgrid=job["vgrid"], 
                                      resource_specs=job["resource_specs"], args=[job])
        #return jobid 

    def create_mig_jobs(self,jobs, deploy_multiple=False):
        if deploy_multiple:
            prepared_jobs = []
            for job in jobs:
                #prepared_jobs.append(
                mrsl_file = self.mig.prepare_job(exec_commands=job["commands"], 
                                            input_files=job["input_files"], executables=[], 
                                            local_working_dir=job["job_dir"], mig_working_dir=job["job_dir"], 
                                            output_files=job["output_files"], static_files=[], 
                                            vgrid=job["vgrid"], resource_specs=job["resource_specs"], 
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
        import time 
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
            
    ######## OUTPUT ##########

    def handle_output(self,job):
        #import resultHandle
        for f in job["output_files"]:
            output_filename =  job["job_dir"]+f
            outputfile = self.mig.get_output(output_filename, job["job_dir"])
        #mylogger.logprint(logfile, "Retrieved output file for job "+job["id"])
              #print "opening ", destDir+filepath, "to", destDir
        
            job_results_dir = self.main_results_dir+job["results_dir"]
            if not os.path.exists(job_results_dir):
                os.mkdir(job_results_dir)
            self.extract_output(outputfile, job_results_dir) # extract the downloaded archive file
            #self.cleanUpJob(job) # delete job files locally and on the MiG server

    def extract_output(self,file_path, dest_dir):
        import tarfile
        new_dir = dest_dir+file_path.split("/")[-1][:-7]
        if not os.path.exists(new_dir):
            os.mkdir(new_dir)
        prog_files = tarfile.open(file_path, "r")

        prog_files.extractall(path=new_dir)
        prog_files.close()

    ####### UPDATE/STATUS #########
  
    def update_jobs(self,jobs):
        new_status = False
        job_ids = map(lambda x : x["id"], jobs)
        #for j in jobs:
            #print j["id"]if j
        print job_ids
        job_info_list = self.mig.get_status(job_ids)
        for i in range(len(jobs)):
            jobs[i]["status"] = job_info_list[i]
            #print jobs[i]["id"], job_info_list[i]["ID"]
        #        map(lambda x : x["id"]=)
        
       # if not j.has_key("status") or jobInfo["STATUS"] != j["status"]["STATUS"]:
       #         j["status"] = jobInfo
        #        newStatus=True
        #if newStatus:
        #    self.PrintStatus(jobs)
        return jobs

    ########## STOP/CANCEL #########

    def cancel_jobs(self,jobs):
        for j in jobs:
            self.cancel_job(j)

    def cancel_job(self,job):
        success = self.mig.cancel_job(job["id"])
        if success: 
            print "Cancelled job : "+job["id"]
            #mylogger.logprint(logfile,"Cancelled job : "+job["id"])
        else:
            print "Unsuccesful cancellation of job :"+job["id"]
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
        job_files.append("arg0.pkl") #r arguments file
        job_files.extend(job["output_files"])  # output
        job_files = map(lambda x : job["job_dir"]+x.split("/")[-1], job_files)
       
        self.mig.remove_files(job_files)
        self.mig.remove_dir(job["job_dir"]) # directory

        # locally
        for f in job_files:
            try:
                os.remove(f)
            except OSError:
                print "Could not delete file : "+f
            except IOError:
                print "Could not delete file : "+f

        try:
            os.rmdir(job["job_dir"])
        except OSError:
            print "Could not delete dir : "+job["job_dir"]
        except IOError:
                print "Could not delete file : "+f
