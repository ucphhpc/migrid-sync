import os
import sys
import tarfile
#R CMD BATCH [options] my_script.R [outfile]

def main():
#    args = sys.argv[1:]
    job = loadJobdata()
    runEpistasisJob(job)

# this method is intended to be called from a CSP process
def runEpistasisJob(job):
   
    #path = "/home/benjamin/Dokumenter/CSPBuilder/myCSPBuilderPrj/epistatis/Epistasis/"
#    datafile = "Inter99All290606.sav"
    print "run epi ", job
    
    #createDir(job["workingDir"]+job["outputDir"]) # create and enter output dir
    #print os.listdir(os.curdir)
    #extractjobfiles(job["jobfilesArchive"], job["workingDir"]) # extract program files 
    #os.chdir(job["workingDir"])
    #createDir(job["workingDir"]+job["outputDir"], enterDirectory=True) # create and enter output dir
    print "before create : ", os.listdir(os.curdir)
    createDir(job["outputDir"], True) # create and enter output dir
    
    rfiles = job["inputFiles"] 
    argstr = generateArgs(job, dataFileDir="../") # generate an argument string
    executeEpistasis(rfiles, "../", argstr, job["Rbin"]) # execute program
    archiveName = job["outputfiles"][0]#epifiles.tar.gz" 
    
    
    #archiveOutput(job["workingDir"]+job["outputDir"], job["workingDir"]+archiveName) # achive output dir
    os.chdir("../")
    archiveOutput(targetDir="epifiles", destDir="./",arcName=archiveName) # archive output dir
    print "Done executing job ", job
#cleanUpEpistasis(job["workingDir"], [archiveName, job["jobfilesArchive"], job["mainScript"]]) # delete all excess files


def extractjobfiles(filepath, destDir):
    print "opening ", destDir+filepath, "to", destDir
    
    progfiles = tarfile.open(destDir+filepath, "r")
    print "efter open"
    print "tarmembers" , progfiles.getmembers()
    progfiles.extractall(path=destDir)
    progfiles.close()

def createDir(dirpath, enterDirectory=False):
    if os.path.exists(dirpath):
        if enterDirectory :
            os.chdir(dirpath)
    else: 
        os.mkdir(dirpath)
        if enterDirectory:
            os.chdir(dirpath)

def archiveOutput(targetDir, arcName, destDir):
    outputfiles = tarfile.open(destDir+arcName, 'w:gz')
    outputfiles.add(targetDir, arcname="")
    outputfiles.close()

def cleanUpEpistasis(workingDirPath, exceptionslist):    
    for root, dirs, files in  os.walk(workingDirPath, topdown=False):
        for f in files: 
            if f[-6:] != ".tar.gz" and not f in exceptionslist :
                fil = os.path.join(root,f)
                os.remove(fil)
                print "removed "+fil
        if dirs != [] :
            direct = os.path.join(root,dirs[0])
            os.rmdir(direct)
            print "removed "+direct
                    
def executeEpistasis(rfiles, path, argstr, rbin): 
    # go to working dir
    #outputdir = "epifiles"
    #os.chdir(path+outputdir)
    #rbin = "$R_HOME/bin/R" 
   # rbin = "R"
#cmdbegin = "R --save CMD BATCH "
    cmdbegin = rbin+" --save CMD BATCH "
    
    try:
        for f in rfiles:
            cmd = cmdbegin+path+f
            print "Running "+cmd
            proc=os.popen(cmd, "w")
            proc.close()
            
    # run program
    #        runcmd = "R --save <"+path+"EpiMain.R" +" --args "+argstr
        runcmd = rbin+" --save <"+path+"EpiMain.R" +" --args "+argstr
        print runcmd
        prc= os.popen(runcmd, "w")
        prc.close()
    except:
        print "error in executeEpistasis()"
        
def generateArgs(job, dataFileDir):
     # data source
    argstr = dataFileDir+job["dataFile"] + " "

    # genes
    argstr += str(job["geneIndex1"]) + " "+ str(job["geneIndex2"]) +" "
    
    # traits
    argstr += str(job["traitIndex1"]) + " "+ str(job["traitIndex2"]) + " "
 
     # selection variable & name
    argstr += str(job["selectionVariable"]) + " "#+ job["selectionVariableName"] + " "
     
     # range
    classValues = job["class"]
    argstr += str(classValues[0])
    for i in range(1,len(classValues)):
        argstr += " "+str(classValues[i] )
 
    return argstr

def loadJobdata():
    import pickle
    
    pkl_file = open('arg0.pkl', 'rb')
    data1 = pickle.load(pkl_file)
     #pprint.pprint(data1)
    
    pkl_file.close()
    print "loaded job data: ", data1
    return data1
     #pickle.load(job, pickledfile)
     
  
if __name__ == "__main__":
    main()
