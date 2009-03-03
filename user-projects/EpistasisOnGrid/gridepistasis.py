import time

import os
import sys

sys.path.append("Configuration/")
import epistasisconfiguration as epistasis_configuration
sys.path.append("Gridinterface/")
import migsession

class GridEpistasis: 
    def __init__(self, local=False):
        self.jobs_done = []
        self.epistasis_jobs = []
        self.all_jobs = []
        self.epistasis_status = "idle"
        self.local_mode = local
        self.mig_session = migsession.MigSession(epistasis_configuration.main_results_dir, local)
               
########### UPDATE / STATUS ############### 

    def get_job_status(self):
        self.mig_session.updateJobs(self.epistasis_jobs)
        for j in self.epistasis_jobs:
            if j["status"]["STATUS"] == "FINISHED":
                self.jobs_done.append(j)
                self.epistasis_jobs.remove(j)
                self.mig_session.handleOutput(j)
                
        if self.num_jobs == len(self.jobs_done):
                    #mylogger.logprint(logfile, "All jobs completed")
            print "all jobs completed"
            self.epistasis_status = "finished"
        
        progress_str = str(len(self.jobs_done))+"/"+str(self.num_jobs) 
        status_lines = self.create_status_feed(self.epistasis_jobs)
        status_lines.extend(self.create_status_feed(self.jobs_done))
        status = ""
        for l in status_lines:
            status += l +"\n"
        return status, progress_str

    def create_status_feed(self,jobs):
        feed = []
        for j in jobs:
            line = self.create_status_str(j)
            feed.append(line)
        return feed

    def create_status_str(self,job):
        status_str = "Epistasis for class "
        for c in job["class"]: 
            status_str += str(c)+" "#+ str(job["class"])+"  :   " #(selection variable: "+str(job["selectionVariable"])+")"
        status_str += "\t"+"\t"+job["status"]["STATUS"]
        return status_str

    def monitor_epistasis(self):
        jobs_done = []
        jobs = self.epistasis_jobs
    #mylogger.logprint(logfile, "Started monitoring")
        while (True):
            try:
                self.mig_session.update_jobs(jobs)
                #print jobs
                for j in jobs:
                    if j["status"]["STATUS"] == "FINISHED":
                        self.mig_session.handle_output(j)
                        jobs_done.append(j)
                        jobs.remove(j)
                    #mylogger.logprint(logfile, "Job "+j["id"]+" done. Ligands: "+ str(j["ligands"]))
                        print  "Job "+j["id"]+" done."
                        
                    
                if jobs == []:
                #mylogger.logprint(logfile, "All jobs completed")
                    self.print_status(jobs_done)
                    print "all jobs completed"
                    return
                self.print_status(jobs)
                self.print_status(jobs_done)
                time.sleep(epistasis_configuration.monitor_polling_frequency)
            except KeyboardInterrupt:
                print "User initiated cancellation of jobs"
                self.mig_session.cancel_jobs(jobs)
                return
            """except:
                self.mig_session.cancelJobs(jobs)
                print "There was an error. Cancelling jobs...", sys.exc_info()[0] 
                return
                """
        return jobs_done

########## START EPISTASIS ############

    def start_epistasis(self,c1=0,c2=0,g1=74,g2=75,t1=7,t2=8,select_variable=2,df=epistasis_configuration.data_file,output_dir=epistasis_configuration.default_user_output_dir):#,local=self.local_mode):
        print g1
        print "start epistasis ", g1,g2,t1,t2,select_variable,df,output_dir

        print "SV: " +str(select_variable)
        selection_variable_index = str(select_variable)
        if c2 == 0:
            selection_variable_values = epistasis_configuration.selection_variable_range[selection_variable_index]
        else:
            selection_variable_values = range(int(c1),int(c2)+1,1)
        job_size = 1#len(selection_variable_values)
        print "SVvals: " +str(selection_variable_values)
        print "JS: "+str(job_size)
        #if self.local_mode:
         #   import localinterface as mig_interface
        
        epi_jobs = create_epistasis_jobs(job_size,  g1=g1, g2=g2, t1=t1, t2=t2,selection_var=select_variable,vals=selection_variable_values, data_file=df, output_dir=output_dir, local=self.local_mode)
        
        self.print_jobs(epi_jobs)
        
        self.mig_session.create_mig_jobs(epi_jobs)
        self.epistasis_jobs.extend(epi_jobs)
        self.all_jobs.extend(epi_jobs) 
        self.num_jobs = len(epi_jobs)
        #return epijobs
        #self.mig_session.epiMonitor(epijobs)

########## STOP /CANCEL ##############

    def stop_epistasis(self):
      #  if self.status == "executing":
        #    print "stopping epistasis"
        self.mig_session.cancel_jobs(self.epistasis_jobs)
            #epiCleanUp(self.epistasis_jobs)
       #     self.status="cancelled"
       # else: 
       #     print "Not executing..."



###### PRINT ###########

    def print_jobs(self,jobs):
    #num= 0
        for i in range(len(jobs)):
            print "job "+str(i)+" : "+str(jobs[i])


    def print_status(self,jobs):
        full_str = []
        for j in jobs:
            status_str = "Job : "+j["id"]+"\t"+j["status"]["STATUS"]
            print status_str
            full_str.append(status_str)
        return full_str

#### CLEAN UP ########

    def clean_up_epistasis(self):
        self.mig_session.clean_up(self.all_jobs)

###### CREATE JOBS#############

# fragments the epistasis procedure into jobs of classes
def fragment_epistasis(job_size, values):
       #levelsInVariable = len(values)
    #num_jobs = levelsInVariable / jobsize
    value_range = []
    current_size = 0
    job_classes = []
    for i in range(len(values)):
        value_range.append(values[i])
        current_size += 1
        if current_size == job_size:
            job_classes.append(value_range)
            value_range = []
            current_size = 0
    if value_range != []: 
        job_classes.append(value_range)
    print job_classes
    
    return job_classes


def create_epistasis_jobs(js, g1=epistasis_configuration.gene_first_index, g2=epistasis_configuration.gene_last_index, t1=epistasis_configuration.trait_first_index, t2=epistasis_configuration. trait_last_index,selection_var=2,vals=[1,2], data_file=epistasis_configuration.data_file, output_dir=epistasis_configuration.output_dir, local=False):

    job_classes = fragment_epistasis(js, vals)
    print "classes " +str(job_classes), js, vals
    jobs = []
    ser_number = 1
   
    time_list = time.localtime(time.time())
    project_tag = str(time_list[2])+"_"+str(time_list[1])+"_"+str(time_list[0])+"_"+str(time_list[3])+str(time_list[4])+str(time_list[5])

    for j in job_classes:
        job = create_init_job()
        job["project_tag"] = project_tag
        job["class"] = j
        job["gene_index_1"] = g1 
        job["gene_index_2"] = g2
        job["trait_index_1"] = t1
        job["trait_index_2"] = t2
        
        job["user_output_dir"] = output_dir
        job["data_file"] = data_file.split("/")[-1]
        job["selection_variable"] = selection_var
        job["selection_var_values"] = vals 
        output_filename = "epifiles"+str(ser_number)+".tar.gz"
        job_directory = epistasis_configuration.tmp_local_job_dir+str(ser_number)+"_"+project_tag+"/"
        job["job_dir"] = epistasis_configuration.Epistasis_working_dir+job_directory
        job["output_files"] = [output_filename]
        job["results_dir"]  = epistasis_configuration.resultsdir_prefix_name+project_tag+"/"
        
        job_cmds = ["cd "+job["job_dir"], "python "+job["main_script"]]
        
        # mig settings
        job["commands"]=job_cmds
        input_files = list(epistasis_configuration.program_files)
        input_files.append(data_file)
        job["input_files"] = input_files 
        job["vgrid"]=epistasis_configuration.vgrid
        job["resource_specs"] = epistasis_configuration.resource_specs
        

        os.mkdir(job["job_dir"])
        if local:
            job["r_bin"] = "R"
        else:
            job["r_bin"] = "$R_HOME/bin/R"
 
        print(job)
        jobs.append(job)
        ser_number += 1
    return jobs


def create_init_job():
    init_job = {}
    init_job["r_files"] =epistasis_configuration.r_files
    init_job["main_script"] = epistasis_configuration.main_script
    init_job["output_dir"] = epistasis_configuration.output_dir

    return init_job


###### MAIN ###############


    # Arguments are entered in the order: selectionvariableindex jobsize
if __name__ == "__main__":
    local = False
    if "-local" in sys.argv or "-l" in sys.argv:
        local = True
#print "Incorrect number of arguments... usage: <selection var> <jobsize>"
    #else:
    
    new_epistasis = GridEpistasis(local)
    new_epistasis.start_epistasis()
    new_epistasis.monitor_epistasis()
    new_epistasis.clean_up_epistasis()
        

