import os
import sys

def main():
    args = sys.argv[1:]
    epistasis(args)

# this method is used when running the script alone
def epistasis(args):
    files = ["EpiCRnew_R_edit.R","DistrPost07_R_edit.R", "EpiPS_R_edit.R", "HWEwigNew_R_edit.R"]
    mainfile = "EpistasisMain.R"
    userSpecFiles = args
    if userSpecFiles != []:
        files = userSpecFiles
    
    # go to working dir
    outputdir = "epifiles"
    createDir(outputdir, True)
    cmdbegin = "R --save CMD BATCH "
    path = "../"
    for f in files:
        cmd = cmdbegin+path+f
        print "Running "+cmd
        proc=os.popen(cmd, "w")
        proc.close()
   
    runcmd = "R --save <"+path+mainfile
    print runcmd
    prc= os.popen(runcmd, "w")
    prc.close()
 
def createDir(dirpath, enterDirectory=False):
    if os.path.exists(dirpath):
        if enterDirectory :
            os.chdir(dirpath)
    else: 
        os.mkdir(dirpath)
        if enterDirectory:
            os.chdir(dirpath)

if __name__ == "__main__":
    import time
    t1 = time.time()
    main()
    t2 = time.time()
    T = t2-t1
    print 'Took %d min %0.3f s' % (T/60,T % 60 )
