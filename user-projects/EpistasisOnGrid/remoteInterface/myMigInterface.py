import sys
sys.path.append("/home/benjamin/Dokumenter/CSPBuilder/myCSPBuilderPrj/migdockingapp")

import EpiConfigUS as EpiConfig
import time
import shutil
import os

#jobCmd = ["R --version"]#["python EpiMiGExec.py"]
#jobCmd = ["cd MiGepistasis/", "ls", "python EpiMiGExec.py"]
inputfiles = EpiConfig.programFiles
executables = []
#jobDir = "MiGjobsDir/"
jobDir = "MiGepistasis/"
vgrid = "DIKU"
migJobDir= "MiGepistasis/"
resourceArch = {"ARCHITECTURE":"AMD64"}
valuesDict = {'2':[1,2], '5':range(1,20)}
jobSize = -7
selectionVariableIndex = 0
selectionVariableValues = [100]

def startJobs(jobs):
    for j in jobs: 
        #jobCmd = ["cd "+j["workingDir"], "python EpiMiGExec.py"]
        #print "tjekking epiconfig ", str(EpiConfig.programFiles)
        j["id"] = MiG.createJob(exeCommands=jobCmd, inputfiles=j["programFiles"], executables=executables, localWrkDir=j["workingDir"], migWrkDir=j["workingDir"], outputfiles=j["outputfiles"], staticfiles=[], vGrid=vgrid, resourceSpecs=resourceArch, args=[j])

def startJob(batchCmd, inputfiles):
    j["id"] = MiG.createJob(exeCommands=jobCmd, inputfiles=j["programFiles"], executables=executables, localWrkDir=j["workingDir"], migWrkDir=j["workingDir"], outputfiles=j["outputfiles"], staticfiles=[], vGrid=vgrid, resourceSpecs=resourceArch, args=[j])
    
# updates the status key in the job dictionary with a status dictionary from MiG
def updateStatus(jobs):
    newStatus = False
    for j in jobs:
        #print j["id"]if j
        jobInfo = MiG.getStatus(j["id"])
        if not j.has_key("status") or jobInfo["STATUS"] != j["status"]["STATUS"]:
            j["status"] = jobInfo
            newStatus=True
    if newStatus:
        printStatus(jobs)
    return jobs

def jobMonitor(jobs):
    jobsDone = []
    #mylogger.logprint(logfile, "Started monitoring")
    while (True):
        try:
            updateStatus(jobs)
            for j in jobs:
                if j["status"]["STATUS"] == "FINISHED":
                    handleOutput(j)
                    jobsDone.append(j)
                    jobs.remove(j)
                    #mylogger.logprint(logfile, "Job "+j["id"]+" done. Ligands: "+ str(j["ligands"]))
                    print  "Job "+j["id"]+" done."
                    
            if jobs == []:
                #mylogger.logprint(logfile, "All jobs completed")
                printStatus(jobsDone)
                print "all jobs completed"
                return
            #epiPrintStatus(jobs)
            #epiPrintStatus(jobsDone)
            time.sleep(EpiConfig.pollFrequency)
        except KeyboardInterrupt:
            print "User initiated cancellation of jobs"
            cancelJobs(jobs)
            return
        #except:
            #print "There was an error. Cancelling jobs..."
            #epiCancelJobs(jobs)
            #return

    return jobsDone

def printStatus(jobs):
    for j in jobs:
        statusStr = "Job : "+j["id"]+"\t"+j["status"]["STATUS"]
        print statusStr

def handleOutput(job):
    #import resultHandle
    for f in job["outputfiles"]:
        outputfilename =  job["workingDir"]+f
        outputfile = MiG.getOutput(outputfilename, job["workingDir"])
    #mylogger.logprint(logfile, "Retrieved output file for job "+job["id"])
        extractOutput(outputfile, job["workingDir"])

def cancelJobs(jobs):
    for j in jobs:
        epiCancelJob(j)

def cancelJob(job):
    success = MiG.cancelJob(job["id"])
    if success: 
        print "Cancelled job : "+job["id"]
        #mylogger.logprint(logfile,"Cancelled job : "+job["id"])
    else:
        print "Unsuccesful cancellation of job :"+job["id"]
        #mylogger.logprint(logfile,"Unsuccesful cancellation of job :"+job["id"])

def cacheFiles(files):
    MiG.cacheFiles(files, isDir=True)

"""
def epi(ligandIndexes, ligandfile, targetfile, fragmentStrategy, runs, jobsize, seed=-1, cmd="", caching=True):
    resultdir = timestamp.generateFolderName()
    logfile = EpiConfig.resultDirectory +"/"+resultdir + "/"+EpiConfig.logfile
    newCmd = cmd
    caching = caching
    epiingJobs = epiStart(ligandIndexes, ligandfile, targetfile, fragmentStrategy, runs, jobsize, testseed=seed)
    epiMonitor(epiingJobs)
"""

def createEpiJobs(js):
    #while True:
    #workData = EpiConfig.initJob
    #stageJobFiles(workData)
    jobclasses = fragmentEpistasis(js, selectionVariableValues)
    print "classes " +str(jobclasses), js, selectionVariableValues
    jobs = []
    sernumber = 1
    jobstamp = int(time.time())
    for j in jobclasses:
        job = createInitEpiJob(selectionVariableIndex)        
        job["class"] = j
        outputfilename = "epifiles"+str(sernumber)+".tar.gz"
        jobDirector = "MiGepi"+str(sernumber)+"_"+str(jobstamp)+"/"
        job["workingDir"] = job["workingDir"]+jobDirector
        job["outputfiles"] = [outputfilename]
        os.mkdir(job["workingDir"])
        jobs.append(job)
        sernumber += 1
    return jobs

# fragments the epistasis procedure into jobs of classes
def fragmentEpistasis(jsize, values):
       #levelsInVariable = len(values)
    #numJobs = levelsInVariable / jobsize
    valueRange = []
    curSize = 0
    jobClasses = []
    for i in range(len(values)):
        valueRange.append(values[i])
        curSize += 1
        if curSize == jsize:
            jobClasses.append(valueRange)
            valueRange = []
            curSize = 0
    if valueRange != []: 
        jobClasses.append(valueRange)
    print jobClasses
    
    return jobClasses

"""

def stageJobFiles(workdata):
    
    jobfilesPath = EpiConfig.EpiProgramPath
    #for f in workdata["programFiles"]:
     #   jobfile = jobfilesPath+f
      #  print "adding ", jobfile
       # tar.add(jobfile, arcname=f)
    #tar.close()
    
    for f in workdata["programFiles"]:
         shutil.copyfile(jobfilesPath+f ,jobDir+f) 
    #workdata["jobfilesArchive"] = name
    # copy the episcript to working dir
    shutil.copyfile(jobfilesPath+workdata["mainScript"],jobDir+workdata["mainScript"]) 
"""

def extractOutput(filepath, destDir):
    import tarfile
    #print "opening ", destDir+filepath, "to", destDir
    newdir = destDir+filepath.split("/")[-1][:-7]
    os.mkdir(newdir)
    progfiles = tarfile.open(filepath, "r")
    #print "efter open"
    #print "tarmembers" , progfiles.getmembers()
    #progfiles.extractall(path=destDir)
    progfiles.extractall(path=newdir)
    progfiles.close()

def newJob():
    initJob = {}
    initJob["workingDir"] = EpiConfig.EpiWorkingDir
    initJob["outputDir"] = EpiConfig.outputDir

    return initJob


def printJobs(jobs):
    #num= 0
    for i in range(len(jobs)):
        print "job "+str(i)+" : "+str(jobs[i])



# Arguments are entered in the order: selectionvariableindex jobsize

if sys.argv[1:] != []:
    selectionVariableIndex = sys.argv[1]
    selectionVariableValues = valuesDict[selectionVariableIndex]
    jobSize = int(sys.argv[2])
#args[2]
    #args[3]
    
print "SV: " +str(selectionVariableIndex)
print "SVvals: " +str(selectionVariableValues )
print "JS: "+str(jobSize)
if "-local" in sys.argv or "-l" in sys.argv:
    import localinterface as MiG
else:
    import MiGuserscriptsInterface as MiG 

epijobs = createEpiJobs(jobSize)
printJobs(epijobs)
epiStart(epijobs)
epiMonitor(epijobs)
