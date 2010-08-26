#!/usr/bin/python

import os, sys, timeit, pprint, threading

# dd if=/dev/urandom of=readfile bs=1048576 count=100


def read_mark(size, f):
    #print "Reading %d from %s" % (size, f)
    #f.seek(0)
    l = f.read(size)
    #assert len(l) == size
    


def main():
    """docstring for main"""
    setup_read = "import os; from __main__ import read_mark; f = open('readfile', 'r')"
    
    read_sequence = [1, 2, 16, 256, 512, 1024, 2048, 4096, 8192, 16384]
    read_results = []

    for s in read_sequence:
        read_results.append((s, max(timeit.repeat("read_mark(%s, f)" % s, setup = setup_read, repeat=3, number=1000))))

    pp = pprint.PrettyPrinter()
    pp.pprint(read_results)
    
if __name__ == '__main__':
    main()