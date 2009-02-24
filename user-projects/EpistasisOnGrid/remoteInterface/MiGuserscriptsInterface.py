import shutil
import os
import time
import tarfile
import createMRSL 
import MigScriptsWrapper as ScriptsWrapper

def createJob(exeCommands, inputfiles, executables, localWrkDir, migWrkDir, outputfiles, staticfiles=[], vGrid="Generic", resourceSpecs={}, args=[]):

    jobfiles = [] 
    jobfiles.extend(inputfiles)

    if staticfiles != []:
        jobfiles.extend(staticfiles)
        
    stagedFiles = stageJobFiles(jobfiles, localWrkDir)
    if args !=[]:
        argfiles = writeArgsToFiles(args, localWrkDir)
        #jobfiles.extend(argfiles)
        stagedFiles.extend(argfiles)

    expectedOutput = [migWrkDir+outputfiles[0]]
        
    # make MRSL
    mrslfile = createMRSL.generateMRSL(exeCommands, stagedFiles, expectedOutput, localWrkDir, executables, resourceSpecsDict=resourceSpecs, vgrid=vGrid)
    #copy files to the user directory where MRSL file operates
    #for file in inputfiles:
    #    filename = filepath.split("/")[-1]
    #    shutil.copy(file,userMiGDir+filename)
    
    #(status, newmsg) = job.new_job(mrslfiles, certName, configuration, False)
    #if not status : 
    #    print "Error creating job "
#	return -1
#     jobId = string.split(newmsg)[0]
    

    #if not runLocal:
    uploadFilesToMiG(stagedFiles, localWrkDir, migWrkDir)
    jobId = ScriptsWrapper.submitToMiG(mrslfile)
    #cleanUpLocally([mrslfile])
    #else: 
    #     for cmd in exeCommand:
    #         proc = os.popen(cmd)
     #        proc.close()
    #time.sleep(5)
    #dirCleanup(jobfiles, migWrkDir)
    return jobId

#import subprocess

def uploadFilesToMiG(inputfiles, tempDir, remoteDir):
    
    #ScriptsWrapper.makeDir(remoteDir, recursive=True)
    #makeDirTree(remoteDir)
    timestamp = str(time.time())
    tarName = "inputfiles"+timestamp+".tar.gz"
    tarpath = tempDir+tarName
    tar = tarfile.open(tarpath,"w:gz")
    
    for f in inputfiles:
        filename = f.split("/")[-1]
        tar.add(f, remoteDir+filename) 
    tar.close()
    #putScript = "migput.py"
    
    outStrs = ScriptsWrapper.put(tarpath, tarName)
 #   flags = "-x" # -x "to extract. use -p to automatically submit mrsl files
  #  scriptcmd = "python "+config.MiGscriptsDir+putScript+" "+flags+" "+configOption+" "+ tarpath+" "+tarName
 
   # print scriptcmd
    
   # proc, output = os.popen4(scriptcmd,"r")
    #outStrs = output.readlines()
   # proc.close()

  
    #whatStr = what.readlines()
    
    print outStrs
    # delete the tar file in the mig server when it has been extracted
    ScriptsWrapper.removeFile(tarName)
    # delete the locally staged files
    #cleanUpLocally([tarpath])

def getOutput(filename, destinationDir):
    success = ScriptsWrapper.get(filename, destinationDir)
    #if success:
    #  
    #else: 
    #    print "Can't get file : "+filename
    #    return ""
    return destinationDir+filename.split("/")[-1]


def parseStatus(statusMsg):
    #import time
    statmsgLines = statusMsg.split("\n")
    jobInfo = {}
    for line in statmsgLines:
        ls = line.split(": ")
        if len(ls) > 1:
            jobInfo[ls[0].upper()] = ls[1] 
    #print jobInfo
    return jobInfo

def writeArgsToFiles(args, destDir):
    import pickle
    num = 0
    argfiles = []
    for arg in args:
        fname = destDir+"arg"+str(num)+".pkl"
        output = open(fname, 'w')
        pickle.dump(arg, output)
        output.close()
        argfiles.append(fname)
        num +=1
    return argfiles

def removeFile(filename):
    return ScriptsWrapper.removeFile(filename)

def removeDir(filename):
    return ScriptsWrapper.removeDir(filename)
    
def removeFiles(filenames):
    filesStr = ""
    for f in filenames:
        filesStr += f + " "
    return ScriptsWrapper.removeFile(filesStr)


#mvd = "/home/benja/Documents/speciale/kode/molecular_docking/MVD"
#createdirOnMig(mvd,"MVD")
# copies files to an intermediary dir
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
    files = []
    for f in inputfiles: 
        cpfilename = destDir+f.split("/")[-1]
        shutil.copyfile(f ,cpfilename)
        files.append(cpfilename)
        
    return files    
    #workdata["jobfilesArchive"] = name
    # copy the episcript to working dir
    #shutil.copyfile(jobfilesPath+workdata["mainScript"],jobDir+workdata["mainScript"]) 

def getStatus(jobId):
    statusStr = ScriptsWrapper.status(jobId)
    jobInfo = parseStatus(statusStr)
    
    return jobInfo

def cancelJob(jobid):
    out = ScriptsWrapper.cancel(jobid)
    return out 

def dirCleanup(jobfiles, directory):
    for f in jobfiles:
        filename = directory+f.split("/")[-1]
        print "removing ", filename
        ScriptsWrapper.removeFile(filename)
        #print out

def cleanUpLocally(files):
      #clean up
    for f in files:
        try: 
            print "removing "+f+" locally"
            os.remove(f)
        except OSError:
            print "Can't delete : "+f


def makeDirTree(path):
    dirs = path.split("/")
    subdirs = ""
    for d in dirs:
        ScriptsWrapper.makeDir(subdirs+d)
        #print subdirs
        subdirs += d + "/"
