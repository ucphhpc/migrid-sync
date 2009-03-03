import shutil
import os
import time
import tarfile
import createmrsl
import sys 
sys.path.append("Gridinterface/migscripts/")
import miglib
import string 
def create_job(exec_commands, input_files, executables, local_working_dir, mig_working_dir, output_files, static_files=[], vgrid="Generic", resource_specs={}, args=[]):

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
    mrsl_file = createmrsl.generate_mrsl(exec_commands, files_to_upload, expected_output, local_working_dir, executables, resource_specs_dict=resource_specs, vgrid=vgrid)
    files_to_upload.append(mrsl_file)
    archive = create_archive(files_to_upload, local_working_dir, mig_working_dir)
    #(code, out) = miglib.submit_file(mrslfile,local_working_dir,True,False)
    #out = mig_function_wrapper(miglib.submit_file,mrslfile,local_working_dir,True,False)
    out = mig_function_wrapper(miglib.submit_file,archive,archive.split("/")[-1],True,True) # upload job archive and submit mrsl
    
    job_id = out[-1].split("'")[-2]
    clean_up_locally([mrsl_file]) # delete generated mrsl file
    #cleanUpInputFiles(files_to_upload) # delete job input files 
    return job_id

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
    mrsl_file = createmrsl.generate_mrsl(exec_commands, files_to_upload, expected_output, local_working_dir, executables, resource_specs_dict=resource_specs, vgrid=vgrid)
    files_to_upload.append(mrsl_file)
    #archive = create_job_archive(files_to_upload, local_working_dir, mig_working_dir)
    #(code, out) = miglib.submit_file(mrslfile,local_working_dir,True,False)
    #out = mig_function_wrapper(miglib.submit_file,mrslfile,local_working_dir,True,False)
    #out = mig_function_wrapper(miglib.submit_file,archive,archive.split("/")[-1],True,True) # upload job archive and submit mrsl
    
    return mrsl_file

  #  migJobId = out[-1].split("'")[-2]
#migJobId = string.split(string.strip(out[-1][0]["job_id"]), " ")[0]
   # jobId = migJobId #ScriptsWrapper.submitToMiG(mrslfile)
    #cleanUpLocally([mrsl_file]) # delete generated mrsl file
    #cleanUpInputFiles(files_to_upload) # delete job input files 
    #return jobId

def submit_job(job_file, dest_dir):
    print job_file
    out = mig_function_wrapper(miglib.submit_file,job_file,dest_dir,True,False) 
#out = mig_function_wrapper(miglib.submit_file,mrslfile,local_working_dir,True,False)
#(code, out) = miglib.submit_file(mrslfile,local_working_dir,True,False)
    print out
    #exit(0)
    job_id = out[-1].split(" ")[0]
    
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

def upload_files(input_files, dest_dir, is_archive=True):
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
    print "uploading"
    print input_files
    #outStrs = ScriptsWrapper.put(tarpath, tarName)
    for f in input_files:
        output = mig_function_wrapper(miglib.put_file, f, dest_dir, False, is_archive)
    if is_archive:
        mig_function_wrapper(miglib.rm_file, dest_dir+f.split("/")[-1])

#print output
    print "uploading done"
    #return "hej"# delete the tar file in the mig server when it has been extracted
    #ScriptsWrapper.removeFile(tarName)
    #miglib.rm_file(tarName)
    # delete the locally staged files
    #cleanUpLocally([tarpath])


def get_output(filename, destination_dir):
    #success = ScriptsWrapper.get(filename, destinationDir)
    out = mig_function_wrapper(miglib.get_file,filename, filename)
    #print code, out
#if success:
    #  
    #else: 
    #    print "Can't get file : "+filename
    #    return ""
    #MiG.removeFiles(filename)
    #MiG.removeDir(job["workingDir"]) # directory
    #allfiles.extend(job["outputfiles"])  # output
    return filename

def write_args_to_files(args, dest_dir):
    import pickle
    num = 0
    arg_files = []
    for arg in args:
        fname = dest_dir+"arg"+str(num)+".pkl"
        output = open(fname, 'w')
        pickle.dump(arg, output)
        output.close()
        arg_files.append(fname)
        num +=1
    return arg_files

def remove_files(filenames):
    files_str = ""
    for f in filenames:
        files_str += f + " "
    #return ScriptsWrapper.removeFile(filesStr)
    return mig_function_wrapper(miglib.rm_file,files_str)

def remove_dir(dirname):
    #return ScriptsWrapper.removeDir(dirname)
    return mig_function_wrapper(miglib.rm_dir,dirname)

#mvd = "/home/benja/Documents/speciale/kode/molecular_docking/MVD"
#createdirOnMig(mvd,"MVD")
# copies files to an intermediary dir
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
    files = []
    for f in input_files: 
        cp_filename = dest_dir+f.split("/")[-1]
        shutil.copyfile(f ,cp_filename)
        files.append(cp_filename)
        
    return files    
    #workdata["jobfilesArchive"] = name
    # copy the episcript to working dir
    #shutil.copyfile(jobfilesPath+workdata["mainScript"],jobDir+workdata["mainScript"]) 

def get_status(job_id):
    #statusStr = ScriptsWrapper.status(jobId)
    #print job_ids
    job_id_list = "job_id=%s" % ";job_id=".join(job_id)
    job_status_list = mig_function_wrapper(miglib.job_status,job_id_list)
    #print statusStr
    job_info = parse_job_info( job_status_list)
    print job_info
    
    return job_info

def parse_status(status_msg):
    #import time
    status_msg_lines = status_msg.split("\n")
    job_info = {}
    for line in status_msg_lines:
        ls = line.split(": ")
        if len(ls) > 1:
            job_info[ls[0].upper()] = ls[1] 
    #print jobInfo
    return job_info

def parse_job_info(status_list):
    #import time
    status_str = "".join(status_list)
    job_info_str_list= status_str.split("Job ")[1:] # we don't need the preceding  information
    job_info_list = []
    for ji in job_info_str_list:
        status = parse_status(ji)
        job_info_list.append(status)
    return job_info_list

def cancel_job(job_id):
    #out = ScriptsWrapper.cancel(jobid)
    out = mig_function_wrapper(miglib.cancel_job,job_id)
    return out 

def dir_cleanup(job_files, directory):
    for f in job_files:
        filename = directory+f.split("/")[-1]
        print "removing ", filename
        #ScriptsWrapper.removeFile(filename)
        #print out

def clean_up_locally(files):
      #clean up
    for f in files:
        try: 
            print "removing "+f+" locally"
            os.remove(f)
        except OSError:
            print "Can't delete : "+f

def make_dir_tree(path):
    dirs = path.split("/")
    subdirs = ""
    for d in dirs:
        #ScriptsWrapper.makeDir(subdirs+d)
        #print subdirs
        subdirs += d + "/"

def clean_up_input_files(files):
    #filepaths = []
    #allfiles = []
    #allfiles.extend(job["programFiles"]) # r files
    #allfiles.append("arg0.pkl") #r arguments file
    #allfiles.extend(job["outputfiles"])  # output
    #for f in allfiles:
    #    filepaths.append(job["workingDir"]+f) # add path
    
    remove_files(files)
    #ScriptsWrapper.removeDir(job["jobDir"]) # directory
    
    # locally
    for f in files:
        try:
            os.remove(f)
        except OSError:
            print "Could not delete file : "+f
        except IOError:
            print "Could not delete file : "+f
            
            """try:
            os.rmdir(job["workingDir"])
            except OSError:
            print "Could not delete dir : "+job["workingDir"]
            except IOError:
            print "Could not delete file : "+f
            """

def mig_function_wrapper(func,*args):
    print args
    #funct = "miglib."+func
    code, out = func(*args)
    print "exit code", code
    if code != 0:
        raise Exception("Error on MiG: "+"".join(out))
    return out
