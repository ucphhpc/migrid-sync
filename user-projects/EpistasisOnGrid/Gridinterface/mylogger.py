import os
import string

def log(logfile, s, debug=False):

    t = getTimeStamp()
    entry = t +" | "+s + "\n"
    logfile = open(logfile, "a")
    logfile.write(entry)
    logfile.close()

    if debug:
        print "Debug: " + s
    
    return entry


def create_log_file(filename):
    if os.path.exists(filename):
        writemode = "a"
    else: 
        directory = string.join(logfile.split("/")[:-1],"/")
        #print dir
        os.mkdir(directory)
        writemode = "w"


def logprint(logfile, s):
    msg = log(logfile, s)
    print "Debug: " +msg 

def getTimeStamp():
    import time
    (y,mo,d,h,m,s,_,_,_)= time.localtime()
    timestamp = "%i %i.%i %02i:%02i:%02i" % (y,mo,d,h,m,s)
    return timestamp
 
