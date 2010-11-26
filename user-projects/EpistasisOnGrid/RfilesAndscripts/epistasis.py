import os, sys
import tarfile
import subprocess
import pickle

def main():
    job = load_job_data()
    run_epistasis_job(job)

def run_epistasis_job(job):
    create_dir(job["output_dir"], enter_directory=True) # create and enter output dir
    
    job_args_file = "job_arguments.dat"
    gene_list = map(str,job["gene_list"])
    trait_list = map(str,job["trait_list"])
    select_var = str(job["selection_variable"])
    create_job_arguments_file(filename=job_args_file, selection_variable=select_var, sel_variable_values= job["class"], genes=gene_list, traits=trait_list)
    argstr = "../"+job["data_file"]+" "+job_args_file
    execute_epistasis(job["r_files"], "../", argstr, job["r_bin"], job["main_r_file"]) # execute program
    archive_name = os.path.basename(job["output_files"][0]) # epifilesN.tar.gz
    os.chdir("../") # go to back to original working dir
    archive_output(target_dir=job["output_dir"], dest_dir="./",arc_name=archive_name) # archive output dir

def extract_job_files(filepath, dest_dir):
    prog_files = tarfile.open(dest_dir+filepath, "r")
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
    print "archiving"
    output_files = tarfile.open(os.path.join(dest_dir,arc_name), 'w:gz')
    
    output_files.add(target_dir, arcname="")
    output_files.close()
    print "done archiving"
    print os.listdir(".")

def clean_up_epistasis(working_dir_path, exceptions_list):    
    for root, dirs, files in  os.walk(working_dir_path, topdown=False):
        for f in files: 
            if f[-6:] != ".tar.gz" and not f in exceptions_list :
                fil = os.path.join(root,f)
                os.remove(fil)
#                print "removed "+fil
        if dirs != [] :
            direct = os.path.join(root,dirs[0])
            os.rmdir(direct)
#            print "removed "+direct
        
    os.rmdir(working_dir_path)

def execute_epistasis(r_files, path, arg_str, r_bin, r_main): 
    cmd_begin = r_bin+" --save CMD BATCH "
    try:
        for f in r_files:
            cmd = cmd_begin+path+f
            print "Running "+cmd
            proc=subprocess.Popen(cmd, shell=True,  stdout=subprocess.PIPE)
            proc.wait()
 
        run_cmd = r_bin+" --save <"+path+r_main+"  --args "+arg_str
        print run_cmd
        #prc= subprocess.Popen(run_cmd, "w")
        #prc.wait()
        proc = subprocess.Popen(run_cmd, shell=True) # takes a list cmdline args
        #    while True:
         #       line = proc.stdout.readline()
         #       if not line:
          #          break
          #      print line,
        proc.wait()
        
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


def create_job_arguments_file(filename, selection_variable, sel_variable_values, genes, traits):
    f = open(filename,"w")
    f.write(selection_variable+"\n")
    f.write(" ".join(sel_variable_values)+"\n")
    f.write(" ".join(genes)+"\n")
    f.write(" ".join(traits)+"\n")
    f.close()

def load_job_data():
    #import pickle
    job_file = sys.argv[1]
    #pkl_file = open("job_file.pkl", 'rb')
    
    pkl_file = open(job_file, 'rb')
    data1 = pickle.load(pkl_file)
    pkl_file.close()
#    print "loaded job data: ", data1
    return data1
     #pickle.load(job, pickledfile)
       
if __name__ == "__main__":
    main()
