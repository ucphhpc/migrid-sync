#!/usr/bin/python
import sys, os, threading, time

COUNTER = 100000
BYTES = 512
clock_fun = time.time

class write_t(threading.Thread):
    def __init__(self, start_time, writefile, data):
        threading.Thread.__init__(self)
        self.writefile = writefile
        self.data = data
        self.start_time = start_time
        
    def run(self):
        for n in xrange(COUNTER):
            self.writefile.write(self.data)
            self.writefile.flush()
            #time.sleep(0.001)
        self.endtime = (clock_fun() - self.start_time)
        print "Write finished at %0.3f" % (self.endtime * 1000)
            
class read_t(threading.Thread):
    def __init__(self, start_time, readfile):
        threading.Thread.__init__(self)
        self.readfile = readfile
        self.start_time = start_time

    def run(self):
        for n in xrange(COUNTER):
            l = len(self.readfile.read(BYTES))
            if  l < BYTES:
                self.readfile.seek(0)
            #time.sleep(0.001)
        self.endtime = (clock_fun() - self.start_time)
        print "Read finished at %0.3f" % (self.endtime * 1000)
          
def main():
    """docstring for main"""
    
    # WRITES ONLY
    threads = []
    readfile = open("readfile", "rb")
    writefile = open("writefile", "wb")
    data = open("/dev/urandom").read(BYTES/8)

    start_time =  clock_fun()

    for n in xrange(1):
        t = write_t(start_time, writefile, data)
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    end = time.time()
    print "Time for pure writes %d" % (end - start_time)    

    # MIXED MODE 
    threads = []
    readfile = open("readfile", "rb")
    writefile = open("writefile", "wb")
    data = open("/dev/urandom").read(BYTES/8)

    start_time =  clock_fun()
    t = write_t(start_time, writefile, data)
    threads.append(t)
    for n in xrange(4):
        t = read_t(start_time, readfile)
        threads.append(t)

    for t in threads:
        t.start()
        
    for t in threads:
        t.join()

    end = time.time()
    
    # READ/ONLY MODE
    print "Time for mixed reads/writes %d" % (end - start_time)    
    threads = []
    readfile = open("readfile", "rb")

    start_time =  clock_fun()

    for n in xrange(5):
        t = read_t(start_time, readfile)
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    end = time.time()

    print "Time for just reads %d" % (end - start_time)
            
if __name__ == '__main__':
    main()