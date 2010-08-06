certName = "Benjamin_Richardt_Thomas_Sedoc"
jobstatusDir = ""#configuration.mrsl_files_dir+"/"+certName+"/"
#import configuration as config
import shutil
import subprocess
import time
import tarfile
import os

def create_job(exec_commands, input_files, executables, local_working_dir, mig_working_dir, output_files, cached_files=[], resource_specs={}, args=[], name=""):
    #import createMRSL 
    import time
    #import tarfile
    #import subprocess
    #import job
    # make MRSL
    #  outputfile = 
    #mrslfile = createMRSL.generateMRSL(exeCommands,inputfiles, outputfile, mrsldir)
    
    # make a fake id from the mrslfile
    if name == "":
        timestamp = str(int(time.time()*100))
        name = "submit_file_"+timestamp
    mrsl_filename = name+".mRSL"
    job_id = name#str(time.time()) #mrslfile.split("/")[-1].split(".")[0]
    #print job_id
    # submit 
    #copy files to the user directory where MRSL file operates
    # for file in inputfiles:
    #     filename = file.split("/")[-1]
    #     #print filename
    #     shutil.copy(file,userMiGDir+"/"+filename)
    #print input_files
    #copy_files_to_working_dir(input_files, local_working_dir)
    
    #if args !=[]:
    #    arg_files = write_args_to_files(args, local_working_dir)
     #   input_files.extend(arg_files)
        
    
        # hack to simulate 
    #olddir = "" 
    olddir = os.getcwd()
    os.chdir(local_working_dir)
    for cmd in exec_commands:
        if cmd.startswith( "cd"): # necessary to simulate change dir locally, since popen does not change python's "current dir" state. cd should propably be avoid if possible.
            os.chdir(cmd[3:])
         #   print os.getcwd()
          #  chdir = True
        else:
            proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE) # takes a list cmdline args
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                print line,

            #print str(proc.stdout.read())
            proc.wait()
    
    if olddir != "": # restore to initial working dir
        os.chdir(olddir)

    #clean_up(local_working_dir,exceptions_list=output_files)
    return job_id

def cancel_job(job_id):
    return True

def get_status(job_ids):
    #jobstatus = {"STATUS":"EXECUTING"}
    #resfile = job_id+".tar"
    #if os.path.exists(userMiGDir+"/"+resfile):
    job_status = {"STATUS" : "FINISHED"}
    status_list = []
    for jid in job_ids:
        status_list.append(job_status)
    return status_list

def get_output(filepath, destination_file):
    #copyfile = destination_file+filepath.split("/")[-1]
    print filepath, destination_file
    if filepath != destination_file:
        print "copying result: "+filepath
        shutil.copy(filepath, destination_file)
    return destination_file

#def getOutput(filename):
#    return userMiGDir+"/"+filename
    

def is_done(job_id):
    return 

def write_args_to_files(args, dest_dir):
    import pickle
    num = 0
    arg_files = []
    for arg in args:
        fname = dest_dir+"arg"+str(num)+".pkl"
        output = open(fname, 'wb')
        pickle.dump(arg, output)
        output.close()
        arg_files.append(fname)
        num +=1
    return arg_files

def clean_up(working_dir_path, exceptions_list):    
    for root, dirs, files in  os.walk(working_dir_path, topdown=False):
        for f in files: 
            if not f in exceptions_list and f[-7:] !=".tar.gz":
                fil = os.path.join(root,f)
                os.remove(fil)
                print "removed "+fil
        if dirs != [] :
            direct = os.path.join(root,dirs[0])
            os.rmdir(direct)
            print "removed "+direct


def copy_files_to_working_dir(input_files, dest_dir):
    #name = "EpistasisJobFiles.tar"
    #jobfilesArchivePath = EpiConfig.preMiGDir+name
    #if executionMode == "local":
        
    #tar = tarfile.open(jobfilesArchivePath,"w")
    #jobfilesPath = EpiConfig.EpiProgramPath
    """for f in workdata["programFiles"]:
        jobfile = jobfilesPath+f
        print "adding ", jobfile
        tar.add(jobfile, arcname=f)
    tar.close()
    """
    #workdata["jobfilesArchive"] = name
    # copy the episcript to working dir
    #shutil.copyfile(jobfilesPath+workdata["mainScript"],jobDir+workdata["mainScript"]) 
    files = []
    for f in input_files: 
        cpfilename = dest_dir+f.split("/")[-1]
        shutil.copyfile(f ,cpfilename)
        files.append(cpfilename)
        
    return files    
def remove_files(filenames):
    # clean up
    #migRmScript = "migrm.py"
    #filesStr = ""
    #for f in filenames:
    #    filesStr += f + " "
    #scriptcmd = "python "+MiGscriptsDir+migRmScript+" "+configOption+" "+filesStr
    
    for f in filenames:
        print "(fake MiG operation) Removing file "+f
      #  os.remove(f)
    
    
#proc,output = os.popen4(scriptcmd,"r")
    #outstr = output.read()
    #proc.close()
    #print outstr

def remove_dir(filename):
    # clean up
    #migRmScript = "migrmdir.py"
    #scriptcmd = "python "+MiGscriptsDir+migRmScript+" "+configOption+" "+filename
    print "(fake MiG operation) Removing dir "+filename
    #os.rmdir(filename)
#proc,output = os.popen4(scriptcmd,"r")
    #outstr = output.read()
    #proc.close()
   # print outstr

def make_dir_tree(path):
    #whatever
    print "(fake) make mig dir : "+path 


def mk_dir(path):
    "do nothing" # fake mig operation

#if not os.path.exists(path):
      #  os.mkdir(path)
#whatever
    #print "(fake) make mig dir : "+path 

def ls(path):
    files = os.listdir(path) 
#print files
    return files 

def path_exists(path):
    files = ls(".")
    exists = path.strip("/") in files
    #print exists
    #exit(0)
    return exists

def prepare_job(exec_commands, input_files, executables, local_working_dir, mig_working_dir, output_files, static_files=[], vgrid="Generic", resource_specs={}, args=[]):

    job_files = [] 
    job_files.extend(input_files)

    if static_files != []:
        job_files.extend(static_files)
        
    files_to_upload = copy_files_to_working_dir(job_files, local_working_dir)
    if args !=[]:
        arg_files = write_args_to_files(args, local_working_dir)
        files_to_upload.extend(arg_files)

    expected_output = [mig_working_dir+output_files[0]]
        
    # make MRSL
    mrsl_file = "fakemrsl.mrsl"#createmrsl.generate_mrsl(exec_commands, files_to_upload, expected_output, local_working_dir, executables, resource_specs_dict=resource_specs, vgrid=vgrid)
    files_to_upload.append(mrsl_file)
    
    return mrsl_file



def submit_job(job_file, dest_dir):
    print job_file
    #out = mig_function_wrapper(miglib.submit_file,job_file,dest_dir,True,False) 
#out = mig_function_wrapper(miglib.submit_file,mrslfile,local_working_dir,True,False)
#(code, out) = miglib.submit_file(mrslfile,local_working_dir,True,False)
    print "fake submit"#out
    #exit(0)
    job_id = str(time.time())#out[-1].split(" ")[0]
    
#print
#append
    return job_id

def create_archive(input_files, temp_dir, remote_dir):
        #ScriptsWrapper.makeDir(remoteDir, recursive=True)
    #makeDirTree(remoteDir)
    timestamp = str(time.time())
    tar_name = "inputfiles"+timestamp+".tar.gz"
    tar_path = temp_dir+tar_name
    tar = tarfile.open(tar_path,"w:gz")
    
    for f in input_files:
        filename = f.split("/")[-1]
        tar.add(f, remote_dir+filename) 
    tar.close()
    print "uploading"
    #outStrs = ScriptsWrapper.put(tarpath, tarName)
    #output = mig_function_wrapper(miglib.put_file, tarpath, tarName, False, True)
    #print output
    print "uploading done"
    return tar_path# delete the tar file in the mig server when it has been extracted
    #ScriptsWrapper.removeFile(tarName)
    #miglib.rm_file(tarName)
    # delete the locally staged files
    #cleanUpLocally([tarpath])

def upload_files(input_files, dest_dir, is_archive=True, recursive=True):
        #ScriptsWrapper.makeDir(remoteDir, recursive=True)
    #makeDirTree(remoteDir)
    #timestamp = str(time.time())
    #tarName = "inputfiles"+timestamp+".tar.gz"
    #tar_path = tempDir+tarName
    #tar = tarfile.open(tar_path,"w:gz")
    
    #for f in inputfiles:
    #    filename = f.split("/")[-1]
    #    tar.add(f, remoteDir+filename) 
    #tar.close()
    print "do nothing in local execution"
    print input_files
    
    #outStrs = ScriptsWrapper.put(tarpath, tarName)
    #for f in input_files:
    #    output = mig_function_wrapper(miglib.put_file, f, dest_dir, False, is_archive)
    #if is_archive:
    #    mig_function_wrapper(miglib.rm_file, dest_dir+f.split("/")[-1])

#print output
    print "uploading done"
    #return "hej"# delete the tar file in the mig server when it has been extracted
    #ScriptsWrapper.removeFile(tarName)
    #miglib.rm_file(tarName)
    # delete the locally staged files
    #cleanUpLocally([tarpath])

