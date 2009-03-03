import os
import sys
gender = "1 2"
female = "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19"
selectionvalues = {"2":gender, "5":female}



def main():
    args = sys.argv[1:]
    epistasis(args)


# this method is used when running the script alone
def epistasis(args):
    g1 = "74"#"85" # 74
    g2 = "103"#"90" # 103
    t1 = "7" # 7 
    t2 = "37" # 37
#    selectname = "Gender"
    selectindex = "5"
    values = selectionvalues[selectindex]
    files = ["EpiCRnew_R_edit.R","DistrPost07_R_edit.R", "EpiPS_R_edit.R", "HWEwigNew_R_edit.R"]
    mainfile = "EpiMain.R"
    datafile = "Inter99All290606.sav"
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
   
    argsstr = path+datafile + " "+g1+" "+g2+" "+t1+" "+t2+" "+selectindex+" "+values
    runcmd = "R --save <"+path+mainfile+" --args "+argsstr
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
    #time.sleep(3)
    t2 = time.time()
    T = t2-t1
    print 'Took %d min %0.3f s' % (T/60,T % 60 )
