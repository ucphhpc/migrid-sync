#!/usr/bin/python

import os, sys, timeit, pprint, threading

# dd if=/dev/urandom of=readfile bs=1048576 count=100


def read_mark(size, f):
    #print "Reading %d from %s" % (size, f)
    #f.seek(0)
    l = f.read(size)
    assert len(l) == size
    
def write_mark(size, f, data):
    f.write(data[:size])
    f.flush()
    os.fsync(f)
    


def main():
    """docstring for main"""
    setup_read = "import os; from __main__ import read_mark; f = open('readfile', 'r')"
    setup_write = "import os; from __main__ import write_mark; data_f = open('/dev/urandom', 'r'); f = open('writefile', 'w'); f.truncate(0); data = data_f.read(262144)"  
    
    read_sequence = [1, 2, 16, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 262144]
    write_sequence = [1, 2, 16, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 262144]
    read_results = []
    write_results = []

    for s in read_sequence:
        read_results.append((s, min(timeit.repeat("read_mark(%s, f)" % s, setup = setup_read, repeat=3, number=1000))))

    for s in write_sequence:
        write_results.append((s, min(timeit.repeat("write_mark(%s, f, data)" % s, setup = setup_write, repeat=3, number=1000))))
    pp = pprint.PrettyPrinter()
    pp.pprint(read_results)
    pp.pprint(write_results)
    
if __name__ == '__main__':
    main()