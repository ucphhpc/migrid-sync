

import time
import shutil
import os
import sys

sys.path.append("Configuration/")
import EpiConfigUS as EpiConfig
import runEpiStasisOnMig as EpiControl
sys.path.append("remoteInterface/")
import MiGuserscriptsInterface as MiG 

class EpistasisProcess: 
    def __init__(self):
#jobCmd = ["R --version"]#["python EpiMiGExec.py"]
    #jobCmd = ["cd MiGepistasis/", "ls", "python EpiMiGExec.py"]
        #inputfiles = EpiConfig.programFiles
    #executables = []
    #jobDir = "MiGjobsDir/"
    #jobDir = "MiGepistasis/"
        self.jobsDone = []
        self.epijobs = []
        #valuesDict = {'2':[1,2], '5':range(1,20)}
    #jobSize = -7
        self.status = "idle"
        self.localmode = False
    #selectionVariableIndex = 0
    #selectionVariableValues = [100]
                
    def epiStatusSummary(self):
        EpiControl.epiUpdateStatus(self.epijobs)
        for j in self.epijobs:
            if j["status"]["STATUS"] == "FINISHED":
                self.jobsDone.append(j)
                self.epijobs.remove(j)
                EpiControl.epiHandleOutput(j)
                
        if self.numJobs == len(self.jobsDone):
                    #mylogger.logprint(logfile, "All jobs completed")
            print "all jobs completed"
            self.status = "finished"
        
        progressStr = str(len(self.jobsDone))+"/"+str(self.numJobs) 
        statusLines = EpiControl.createStatusFeed(self.epijobs)
        statusLines.extend(EpiControl.createStatusFeed(self.jobsDone))
        status = ""
        for l in statusLines:
            status += l +"\n"
        return status, progressStr

    def startEpistasis(self,c1=0,c2=0,g1=74,g2=75,t1=7,t2=8,sv=2,df=EpiConfig.dataFile,outdir=EpiConfig.defaultUserOutputDir):#,local=self.localmode):
        print g1
        print "start epistasis ", g1,g2,t1,t2,sv,df,outdir

        print "SV: " +str(sv)
        selectionVariableIndex = str(sv)
        if c2 == 0:
            selectionVariableValues = EpiConfig.valuesDict[selectionVariableIndex]
        else:
            selectionVariableValues = range(int(c1),int(c2)+1,1)
        jobSize = 1#len(selectionVariableValues)
        print "SVvals: " +str(selectionVariableValues)
        print "JS: "+str(jobSize)
        if self.localmode:
            import localinterface as MiG
        
        epijobs = EpiControl.createEpiJobs(jobSize,  g1=g1, g2=g2, t1=t1, t2=t2,sv=sv,vals=selectionVariableValues, datafile=df, outputdir=outdir, local=self.localmode)
        
        EpiControl.printJobs(epijobs)
       
        EpiControl.epiStart(epijobs)
        self.epijobs= epijobs
        self.numJobs = len(epijobs)
        #return epijobs
        #EpiControl.epiMonitor(epijobs)

    def stopEpistasis(self):
      #  if self.status == "executing":
        #    print "stopping epistasis"
        EpiControl.epiCancelJobs(self.epijobs)
            #epiCleanUp(self.epijobs)
       #     self.status="cancelled"
       # else: 
       #     print "Not executing..."

    def monitorEpistasis(self):
        EpiControl.epiMonitor(self.epijobs)

    # Arguments are entered in the order: selectionvariableindex jobsize
if __name__ == "__main__":
    local = False
    if "-local" in sys.argv or "-l" in sys.argv:
        local = True
#print "Incorrect number of arguments... usage: <selection var> <jobsize>"
    #else:
    
    epistasisProc = EpistasisProcess()
    epistasisProc.localmode = local
    epistasisProc.startEpistasis()
    epistasisProc.monitorEpistasis()
        #epistasisProc.epiMonitor(epistasisProc.epijobs)
