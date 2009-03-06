import os
import sys
import tarfile
#R CMD BATCH [options] my_script.R [outfile]

def main():
#    args = sys.argv[1:]
    job = load_job_data()
    run_epistasis_job(job)

# this method is intended to be called from a CSP process
def run_epistasis_job(job):
    #path = "/home/benjamin/Dokumenter/CSPBuilder/myCSPBuilderPrj/epistatis/Epistasis/"
#    datafile = "Inter99All290606.sav"
    print "run epi ", job
    
    #createDir(job["workingDir"]+job["outputDir"]) # create and enter output dir
    #print os.listdir(os.curdir)
    #extractjobfiles(job["jobfilesArchive"], job["workingDir"]) # extract program files 
    #os.chdir(job["workingDir"])
    #createDir(job["workingDir"]+job["outputDir"], enterDirectory=True) # create and enter output dir
    print "before create : ", os.listdir(os.curdir)
    create_dir(job["output_dir"], True) # create and enter output dir
    
    rfiles = job["r_files"] 
    argstr = generate_args(job, data_file_dir="../") # generate an argument string
    execute_epistasis(rfiles, "../", argstr, job["r_bin"]) # execute program
    archive_name = job["output_files"][0]#epifiles.tar.gz" 
    
    
    #archiveOutput(job["workingDir"]+job["outputDir"], job["workingDir"]+archiveName) # achive output dir
    os.chdir("../")
    archive_output(target_dir=job["output_dir"], dest_dir="./",arc_name=archive_name) # archive output dir
    print "Done executing job ", job
    clean_up_epistasis(job["output_dir"], [archive_name, job["main_script"]]) # delete all excess files


def extract_job_files(filepath, dest_dir):
    print "opening ", dest_dir+filepath, "to", dest_dir
    
    prog_files = tarfile.open(dest_dir+filepath, "r")
    print "efter open"
    print "tarmembers" , prog_files.getmembers()
    prog_files.extractall(path=dest_dir)
    prog_files.close()

def create_dir(dir_path, enter_directory=False):
    if os.path.exists(dir_path):
        if enter_directory :
            os.chdir(dir_path)
    else: 
        os.mkdir(dir_path)
        if enter_directory:
            os.chdir(dir_path)

def archive_output(target_dir, arc_name, dest_dir):
    output_files = tarfile.open(dest_dir+arc_name, 'w:gz')
    output_files.add(target_dir, arcname="")
    output_files.close()

def clean_up_epistasis(working_dir_path, exceptions_list):    
    for root, dirs, files in  os.walk(working_dir_path, topdown=False):
        for f in files: 
            if f[-6:] != ".tar.gz" and not f in exceptions_list :
                fil = os.path.join(root,f)
                os.remove(fil)
                print "removed "+fil
        if dirs != [] :
            direct = os.path.join(root,dirs[0])
            os.rmdir(direct)
            print "removed "+direct
        
    os.rmdir(working_dir_path)
                    
def execute_epistasis(r_files, path, arg_str, r_bin): 
    # go to working dir
    #outputdir = "epifiles"
    #os.chdir(path+outputdir)
    #rbin = "$R_HOME/bin/R" 
   # rbin = "R"
#cmdbegin = "R --save CMD BATCH "
    cmd_begin = r_bin+" --save CMD BATCH "
    
    try:
        for f in r_files:
            cmd = cmd_begin+path+f
            print "Running "+cmd
            proc=os.popen(cmd, "w")
            proc.close()
            
    # run program
    #        runcmd = "R --save <"+path+"EpiMain.R" +" --args "+argstr
        run_cmd = r_bin+" --save <"+path+"EpiMain.R" +" --args "+arg_str
        print run_cmd
        prc= os.popen(run_cmd, "w")
        prc.close()
    except:
        print "error in executeEpistasis()"
        
def generate_args(job, data_file_dir):
     # data source
    arg_str = data_file_dir+job["data_file"] + " "

    # genes
    arg_str += str(job["gene_index_1"]) + " "+ str(job["gene_index_2"]) +" "
    
    # traits
    arg_str += str(job["trait_index_1"]) + " "+ str(job["trait_index_2"]) + " "
 
     # selection variable & name
    arg_str += str(job["selection_variable"]) + " "#+ job["selectionVariableName"] + " "
     
     # range
    class_values = job["class"]
    arg_str += str(class_values[0])
    for i in range(1,len(class_values)):
        arg_str += " "+str(class_values[i] )
 
    return arg_str

def load_job_data():
    import pickle
    
    pkl_file = open('job_file.pkl', 'rb')
    data1 = pickle.load(pkl_file)
     #pprint.pprint(data1)
    
    pkl_file.close()
    print "loaded job data: ", data1
    return data1
     #pickle.load(job, pickledfile)
       
if __name__ == "__main__":
    main()
