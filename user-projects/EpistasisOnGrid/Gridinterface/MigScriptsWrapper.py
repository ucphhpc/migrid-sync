import MigConfiguration as Config
import os
import string
def cancel(jobId):    
    cancelScript = "migcancel.py"
    scriptcmd = "python "+Config.MiGscriptsDir+cancelScript+" "+Config.option+" "+jobId
    code,output = os.popen4(scriptcmd,"r")
    #Str = output.read()    
    return code

def status(jobId):
    statusScript = "migstatus.py"
    scriptcmd = "python "+Config.MiGscriptsDir+statusScript+" "+Config.option+" "+jobId
    proc,output = os.popen4(scriptcmd,"r")
    statusStr = output.read()    
    proc.close()
    return statusStr
    
def get(filename, destinationDir):
    getScript = "migget.py"
    verbose = "-v"
    scriptcmd = "python "+Config.MiGscriptsDir+getScript+" "+Config.option+" "+verbose+" "+filename+" "+destinationDir
    #destfile = destinationDir+filename.split("/")[-1]
    #scriptcmd = "python "+Config.MiGscriptsDir+getScript+" "+Config.option+" "+filename+" "+destfile
    print scriptcmd
    proc,out = os.popen4(scriptcmd,"w")
    output = out.readlines()
    print proc, out, output
    exitcode = output[0]
    if len(output) > 1:
         outstr = output[1]
         if exitcode != "0":
             print exitcode, outstr
    proc.close()
    return 0#int(exitcode)

def submitToMiG(mrslfile):
    submitScript = "migsubmit.py"
    if mrslfile[-5:] != ".mRSL":
        print "Error"

    proc,output = os.popen4("python "+Config.MiGscriptsDir+submitScript+" "+Config.option+" "+mrslfile,"r")
    outStrs = output.readlines()
    proc.close()

    print outStrs
    if outStrs == "":
        return
    migJobId = string.split(string.strip(outStrs[-1]), " ")[0]
    
    print "job id", migJobId
        
    return migJobId

"""
def getOutputfileFromMiG(filename, localdir):
    migGetScript = "migget.py"
    scriptcmd = "python "+Config.MiGscriptsDir+migGetScript+" "+filename+" "+localdir+"/"+filename
    _,output = os.popen4(scriptcmd,"r")
    outstr = output.read()
    print outstr
    
    # remove file from MiG dir

    removeFile(filename)
    
    return localdir+"/"+filename
"""


def removeFile(filename):
    # clean up
    migRmScript = "migrm.py"
    scriptcmd = "python "+Config.MiGscriptsDir+migRmScript+" "+Config.option+" "+filename
    print "Removing file "+filename
    proc,output = os.popen4(scriptcmd,"r")
    outstr = output.read()
    proc.close()
    print outstr

def removeDir(filename):
    # clean up
    migRmScript = "migrmdir.py"
    scriptcmd = "python "+Config.MiGscriptsDir+migRmScript+" "+Config.option+" "+filename
    print "Removing file "+filename
    proc,output = os.popen4(scriptcmd,"r")
    outstr = output.read()
    proc.close()
    print outstr
    




def cacheFiles(files, isDir=False):
    putScript = "migput.py"

    if isDir:
        flags = "-r -p"
        destDir = files.split("/")[-1]
    
    scriptcmd = "python "+Config.MiGscriptsDir+putScript+" "+flags+" "+Config.option+" "+ files+" "+destDir
    print scriptcmd
    _,output = os.popen4(scriptcmd,"r")
    outStrs = output.readlines()
    print outStrs


#def mkdir(dirs):
#    for root, dirs, files in os.walk(directory):
#    os.makedirs(dirs)

def createdirOnMig(srcdir, destdir):
    mkdirScript = "migmkdir.py"
    flags = "-r"
    scriptcmd = "python "+Config.MiGscriptsDir+mkdirScript+" "+flags+" "+Config.option+" "+ srcdir+" "+destdir
    print scriptcmd
    _,output = os.popen4(scriptcmd,"r")
    outStrs = output.readlines()
    print outStrs

def makeDir(dirname, recursive=False): 
    mkdirScript = "migmkdir.py"
    
    flags = ""
    if recursive:
        flags = "-r"
    scriptcmd = "python "+Config.MiGscriptsDir+mkdirScript+" "+flags+" "+Config.option+" "+ dirname
    print scriptcmd
    _,output = os.popen4(scriptcmd,"r")
    outStrs = output.readlines()
    print outStrs

def put(localfilename, remotefilename):
    putScript = "migput.py"
    
    flags = "-x" # -x "to extract. use -p to automatically submit mrsl files
    scriptcmd = "python "+Config.MiGscriptsDir+putScript+" "+flags+" "+Config.option+" "+ localfilename+" "+remotefilename
    
    print scriptcmd
    
    proc, output = os.popen4(scriptcmd,"r")
    outStrs = output.readlines()
    proc.close()
    return outStrs

"""
def getScript(command):
    
    scriptcmd = "python "+Config.MiGscriptsDir+putScript+" "+flags+" "+Config.option+" "+ filename+" "+remotefilename
    
    print scriptcmd
    
    proc, output = os.popen4(scriptcmd,"w")
    outStrs = output.readlines()
    proc.close()
"""
