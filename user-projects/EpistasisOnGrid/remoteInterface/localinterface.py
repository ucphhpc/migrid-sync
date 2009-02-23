#userMiGDir = "mol_server_localtest"
#fakeMiGuserDir" #"/home/benja/mig/wwwuser/Benjamin_Richardt_Thomas_Sedoc/"
#mrsldir = "mol_server_localtest/mrsldir"
#localFakeOutputdir = "mol_server_localtest/createscript"
certName = "Benjamin_Richardt_Thomas_Sedoc"
jobstatusDir = ""#configuration.mrsl_files_dir+"/"+certName+"/"
#import configuration as config
import shutil
import os
# creates a MRSL script and submits it as MiG job. Returns the job id assigned by MiG.
#def createJob(exeCommands, inputfiles, executables, outputfile):
def createJob(exeCommands, inputfiles, executables, localWrkDir, migWrkDir, outputfiles, staticfiles=[], vGrid="Generic", resourceSpecs={}, args=[]):
    #import createMRSL 
    import time
    #import tarfile
    #import subprocess
    #import job
    # make MRSL
#  outputfile = 

    #mrslfile = createMRSL.generateMRSL(exeCommands,inputfiles, outputfile, mrsldir)

    # make a fake id from the mrslfile
    jobId = str(time.time()) #mrslfile.split("/")[-1].split(".")[0]
    print jobId
    # submit 
    #copy files to the user directory where MRSL file operates
    # for file in inputfiles:
    #     filename = file.split("/")[-1]
    #     #print filename
    #     shutil.copy(file,userMiGDir+"/"+filename)
    print inputfiles
    stageJobFiles(inputfiles, localWrkDir)
    
    if args !=[]:
        argfiles = writeArgsToFiles(args, localWrkDir)
        inputfiles.extend(argfiles)
        
    
        # hack to simulate 
    olddir = "" 
    for cmd in exeCommands:
        if cmd.startswith( "cd"):
            olddir = os.getcwd()
            os.chdir(cmd[3:])
            print os.getcwd()
            chdir = True
        else:
            proc = os.popen(cmd, "w")
            proc.close()
    
    if olddir != "": # restore to initial working dir
        os.chdir(olddir)

    cleanUp(localWrkDir,exceptionslist=outputfiles)
    #startJob(mrslfiles, certName, configuration)

#    (status, newmsg) = job.new_job(mrslfiles, certName, configuration, False)
#    if not status : 
#        print "Error creating job "
#	return -1
#     jobId = string.split(newmsg)[0]
     	    
     # cleanup files from user directory
    #for file in inputfiles:
    #    filename = file.split("/")[-1]
    #    os.remove(userMiGDir+"/"+filename)	        
    
    # make an output .tar to simulate MiG # cleanup output files 
    """ 
    mvdOutputFiles = os.listdir(localFakeOutputdir)
   
    tar = tarfile.open(userMiGDir+"/"+outputfile,"w:gz")
    for file in mvdOutputFiles:
        if not os.path.isdir(localFakeOutputdir+"/"+file) and not file.endswith(".tar"):
            tar.add(localFakeOutputdir+"/"+file, file, recursive=False) 
            os.remove(localFakeOutputdir+"/"+file)
    tar.close()
    """
    return jobId

#def startJob(mrslfiles, certName, configuration, False):
#os.popen(shellCommand, 'w')

#    (status, newmsg) = job.new_job(mrslfiles, certName, configuration, False)
#    if not status : 
#        print "Error creating job "
#	return -1
#     jobId = string.split(newmsg)[0]
#     return jobId

# Starts all local jobs. First, the mvd script is copied to the jobid folder to make sure output goes there too. 
# Then the jobs are executed with popen, in multiple processes.
"""    def startJobsLocal(self):
    	import os
    	import shutil
        
        localdir = "mol_server_localtest"
	jobs = self.jobsInfo
        jobFiles = os.listdir(self.jobsDir)
	path = "/home/benja/molecular_docking/"+self.jobsDir+"/"
	#path = ""
        mvdCommand = self.mvdProgramBin
        nogui = "-nogui"
        self.jobsDir
        
        dirs = os.listdir(os.getcwd())
        if localdir not in dirs:
            os.mkdir(localdir)
            
        os.chdir(localdir)

        for j in jobs:
            
            os.mkdir(j["localId"])
#            os.chdir(j["localId"])
            
            mvdFile = j["mvdFile"]
            mvdScript = self.prjroot+self.jobsDir + "/"+mvdFile
            newLocation = os.getcwd()+"/"+j["localId"]
            procs = []
            if j.has_key("mvdFile"): 
                shutil.copy(mvdScript,newLocation+"/"+mvdFile)

            shellCommand = mvdCommand+" "+newLocation+"/"+mvdFile+" "+nogui
            procs.append(os.popen(shellCommand, 'w'))
            

        # wait for processes to finish
        for proc in procs:
            proc.close()
        
        self.migOutputdir = os.getcwd()
        # create result tars to simulate MiG results
        jobOutputDirs = os.listdir(os.getcwd())
        for job in jobOutputDirs:
            if not os.path.isdir(job):
                continue
                      
            outputFiles = os.listdir(os.getcwd()+"/"+job)
            tarName = job+".tar"
            tar = tarfile.open(tarName,"w:gz")
            for f in outputFiles:
                os.chdir(job)
                tar.add(f) 
                os.chdir("..")
            tar.close()
        

        # where to put the results
        #self.resultsDir = 
        self.migUserDir = self.prjroot+"mol_server_localtest"
        
"""

def cancelJob(jobId):
    return True

def getStatus(jobId):
    #jobstatus = {"STATUS":"EXECUTING"}
    #resfile = jobId+".tar"
    #if os.path.exists(userMiGDir+"/"+resfile):
    jobstatus = {"STATUS" : "FINISHED"}
    return jobstatus

def getOutput(filename, destinationDir):
    copyfile = destinationDir+filename.split("/")[-1]
    if filename != copyfile:
        shutil.copy(filename, copyfile)
    return copyfile

#def getOutput(filename):
#    return userMiGDir+"/"+filename
    

def isDone(jobId):
    return 

def writeArgsToFiles(args, destDir):
    import pickle
    num = 0
    argfiles = []
    for arg in args:
        fname = destDir+"arg"+str(num)+".pkl"
        output = open(fname, 'wb')
        pickle.dump(arg, output)
        output.close()
        argfiles.append(fname)
        num +=1
    return argfiles

def cleanUp(workingDirPath, exceptionslist):    
    for root, dirs, files in  os.walk(workingDirPath, topdown=False):
        for f in files: 
            if not f in exceptionslist and f[-7:] !=".tar.gz":
                fil = os.path.join(root,f)
                os.remove(fil)
                print "removed "+fil
        if dirs != [] :
            direct = os.path.join(root,dirs[0])
            os.rmdir(direct)
            print "removed "+direct


def stageJobFiles(inputfiles, destDir):
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
    for f in inputfiles: 
        cpfilename = destDir+f.split("/")[-1]
        shutil.copyfile(f ,cpfilename)
        files.append(cpfilename)
        
    return files    
def removeFiles(filenames):
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

def removeDir(filename):
    # clean up
    #migRmScript = "migrmdir.py"
    #scriptcmd = "python "+MiGscriptsDir+migRmScript+" "+configOption+" "+filename
    print "(fake MiG operation) Removing dir "+filename
    #os.rmdir(filename)
#proc,output = os.popen4(scriptcmd,"r")
    #outstr = output.read()
    #proc.close()
   # print outstr

def makeDirTree(path):
    #whatever
    print "(fake) make mig dir : "+path 
