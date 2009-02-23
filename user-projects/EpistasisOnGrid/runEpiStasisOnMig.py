import sys
sys.path.append("remoteInterface/")
sys.path.append("Configuration/")
import EpiConfigUS as EpiConfig
import time
import shutil
import os

import MiGuserscriptsInterface as MiG
#import localinterface as MiG

#from MigInterface import MiGuserscriptsInterface as MiG
#inputfiles = EpiConfig.programFiles
#executables = []
#jobDir = "MiGepistasis/"
#vgrid = "DCSC"#"DIKU"
#migJobDir= "MiGepistasis/"
#resourceArch = {"RUNTIMEENVIRONMENT": "GNU_R"}#{"ARCHITECTURE":"AMD64"}

#valuesDict = {'2':[1,2], '5':range(1,20)}
#jobSize = -7

def epiStart(jobs):
    migworkingdir = jobs[0]["workingDir"]
    MiG.makeDirTree(migworkingdir)
    for j in jobs: 
        jobCmd = ["cd "+j["workingDir"], "python EpiMiGExec.py", "dir"]
        #print "tjekking epiconfig ", str(EpiConfig.programFiles)
        j["id"] = MiG.createJob(exeCommands=jobCmd, inputfiles=j["programFiles"], executables=[], localWrkDir=j["workingDir"], migWrkDir=j["workingDir"], outputfiles=j["outputfiles"], staticfiles=[], vGrid=EpiConfig.vgrid, resourceSpecs=EpiConfig.resourceSpecs, args=[j])
   
def createEpiJobs(js, g1=EpiConfig.geneFirstIndex, g2=EpiConfig.geneLastIndex, t1=EpiConfig.traitFirstIndex, t2=EpiConfig. traitLastIndex,sv=2,vals=[1,2], datafile=EpiConfig.dataFile, outputdir=EpiConfig.outputDir, local=False):
    #while True:
    #workData = EpiConfig.initJob
    #stageJobFiles(workData)
    jobclasses = fragmentEpistasis(js, vals)
    print "classes " +str(jobclasses), js, vals
    jobs = []
    sernumber = 1
    #jobstamp = int(time.time())

    timelist = time.localtime(time.time())
    projectTag = str(timelist[2])+"_"+str(timelist[1])+"_"+str(timelist[0])+"_"+str(timelist[3])+str(timelist[4])+str(timelist[5])

    for j in jobclasses:
        job = createInitEpiJob()#selectionVariableIndex)       
        job["projectTag"] = projectTag
        job["class"] = j
        job["geneIndex1"] = g1 
        job["geneIndex2"] = g2
        job["traitIndex1"] = t1
        job["traitIndex2"] = t2
        
        job["userOutputDir"] = outputdir
        job["dataFile"] = datafile.split("/")[-1]
        job["selectionVariable"] = sv
        job["selVarValues"] = vals 
        outputfilename = "epifiles"+str(sernumber)+".tar.gz"
        jobDirector = "MiGepi"+str(sernumber)+"_"+projectTag+"/"
        job["workingDir"] = job["workingDir"]+jobDirector
        job["outputfiles"] = [outputfilename]
        os.mkdir(job["workingDir"])
        if local:
            job["Rbin"] = "R"
        else:
            job["Rbin"] = "$R_HOME/bin/R"
 
        print(job)
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

def epiCacheFiles(files):
    MiG.cacheFiles(files, isDir=True)

# updates the status key in the job dictionary with a status dictionary from MiG
def epiUpdateStatus(jobs):
    newStatus = False
    for j in jobs:
        #print j["id"]if j
        jobInfo = MiG.getStatus(j["id"])
        if not j.has_key("status") or jobInfo["STATUS"] != j["status"]["STATUS"]:
            j["status"] = jobInfo
            newStatus=True
    if newStatus:
        epiPrintStatus(jobs)
    return jobs

def epiMonitor(jobs):
    jobsDone = []
    #mylogger.logprint(logfile, "Started monitoring")
    while (True):
        try:
            epiUpdateStatus(jobs)
            for j in jobs:
                if j["status"]["STATUS"] == "FINISHED":
                    epiHandleOutput(j)
                    jobsDone.append(j)
                    jobs.remove(j)
                    #mylogger.logprint(logfile, "Job "+j["id"]+" done. Ligands: "+ str(j["ligands"]))
                    print  "Job "+j["id"]+" done."
                    
            if jobs == []:
                #mylogger.logprint(logfile, "All jobs completed")
                epiPrintStatus(jobsDone)
                print "all jobs completed"
                return
            #epiPrintStatus(jobs)
            #epiPrintStatus(jobsDone)
            time.sleep(EpiConfig.pollFrequency)
        except KeyboardInterrupt:
            print "User initiated cancellation of jobs"
            epiCancelJobs(jobs)
            return
        #except:
            #print "There was an error. Cancelling jobs..."
            #epiCancelJobs(jobs)
            #return
    return jobsDone

def printJobs(jobs):
    #num= 0
    for i in range(len(jobs)):
        print "job "+str(i)+" : "+str(jobs[i])

def createStatusFeed(jobs):
    feed = []
    for j in jobs:
        line = createStatusStr(j)
        feed.append(line)
    return feed

def createStatusStr(job):
    statstr = "Epistasis for class "
    for c in job["class"]: 
        statstr += str(c)+" "#+ str(job["class"])+"  :   " #(selection variable: "+str(job["selectionVariable"])+")"
    statstr += "\t"+"\t"+job["status"]["STATUS"]
    return statstr

def epiPrintStatus(jobs):
    fullStr = []
    for j in jobs:
        statusStr = "Job : "+j["id"]+"\t"+j["status"]["STATUS"]
        print statusStr
        fullStr.append(statusStr)
    return fullStr

def epiCancelJobs(jobs):
    for j in jobs:
        epiCancelJob(j)

def epiCancelJob(job):
    success = MiG.cancelJob(job["id"])
    if success: 
        print "Cancelled job : "+job["id"]
        #mylogger.logprint(logfile,"Cancelled job : "+job["id"])
    else:
        print "Unsuccesful cancellation of job :"+job["id"]
        #mylogger.logprint(logfile,"Unsuccesful cancellation of job :"+job["id"])
    epiCleanUpJob(job)

def epiHandleOutput(job):
    #import resultHandle
    for f in job["outputfiles"]:
        outputfilename =  job["workingDir"]+f
        outputfile = MiG.getOutput(outputfilename, job["workingDir"])
    #mylogger.logprint(logfile, "Retrieved output file for job "+job["id"])
          #print "opening ", destDir+filepath, "to", destDir
        destDir = job["userOutputDir"]
        mainresultsdir = destDir+EpiConfig.resultsdirPrefixName+job["projectTag"]+"/"
        if not os.path.exists(mainresultsdir):
            os.mkdir(mainresultsdir)
        extractOutput(outputfile, mainresultsdir)
        #epiCleanUpJob(job)
        

def extractOutput(filepath, destDir):
    import tarfile
    newdir = destDir+filepath.split("/")[-1][:-7]
    if not os.path.exists(newdir):
        os.mkdir(newdir)
    progfiles = tarfile.open(filepath, "r")
    #print "efter open"
    #print "tarmembers" , progfiles.getmembers()
    #progfiles.extractall(path=destDir)
    progfiles.extractall(path=newdir)
    progfiles.close()

def createInitEpiJob():
    initJob = {}
 #   initJob["geneIndex1"] = EpiConfig.geneFirstIndex
 #   initJob["geneIndex2"] = EpiConfig.geneLastIndex
   # initJob["traitIndex1"] = EpiConfig.traitFirstIndex
 #   initJob["traitIndex2"] =EpiConfig. traitLastIndex
    
    initJob["programFiles"] = list(EpiConfig.programFiles)#map(lambda x : x.split("/")[-1],list(EpiConfig.programFiles)) 
    initJob["inputFiles"] =EpiConfig.inputFiles
    initJob["mainScript"] = EpiConfig.mainScript 
    #initJob["selectionVariable"] = selvarIndex#EpiConfig.selectionVariableIndex
    #initJob["selectionVariableName"] = EpiConfig.selectionVariableName
    #initJob["dataFile"] = EpiConfig.dataFile
    initJob["path"] = EpiConfig.EpiProgramPath
   # initJob["selVarValues"] = selectionVariableValues#EpiConfig.selectionVariableValues
    initJob["workingDir"] = EpiConfig.EpiWorkingDir
    initJob["outputDir"] = EpiConfig.outputDir
    
    return initJob

def epiCleanUp(jobs):
    for j in jobs:
        epiCleanUpJob(j)

def epiCleanUpJob(job):
    filepaths = []
    allfiles = []
    allfiles.extend(job["programFiles"]) # r files
    allfiles.append("arg0.pkl") #r arguments file
    allfiles.extend(job["outputfiles"])  # output
    for f in allfiles:
        filepaths.append(job["workingDir"]+f) # add path
    
    MiG.removeFiles(filepaths)
    MiG.removeDir(job["workingDir"]) # directory
    
    # locally
    for f in filepaths:
        try:
            os.remove(f)
        except OSError:
            print "Could not delete file : "+f
        except IOError:
            print "Could not delete file : "+f
            
    try:
        os.rmdir(job["workingDir"])
    except OSError:
        print "Could not delete dir : "+job["workingDir"]
    except IOError:
            print "Could not delete file : "+f

# Arguments are entered in the order: selectionvariableindex jobsize
if __name__ == "__main__":
    if len(sys.argv[1:]) < 2:
        print "Incorrect number of arguments... usage: <selection var> <jobsize>"
    else:
        selectionVariableIndex = sys.argv[1]
        selectionVariableValues = EpiConfig.valuesDict[selectionVariableIndex]
        jobSize = int(sys.argv[2])
        
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
