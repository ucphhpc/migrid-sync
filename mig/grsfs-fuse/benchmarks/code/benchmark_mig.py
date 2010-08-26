#!/usr/bin/python

import os, sys, timeit, pprint

# dd if=/dev/urandom of=readfile bs=1048576 count=100

    
def cycle(data):
    #sys.stdout.write('.')
    def nodot(item): return item[0] != '.'
    
    write_fd = open("./file", "wb")
    write_fd.write(data)
    write_fd.close()
    
    os.symlink("./file", "./symlinkedfile")
    os.stat("./symlinkedfile")
    for f in filter(nodot, os.listdir('.')):
        os.lstat(f)
    read_fd = open("./symlinkedfile", "rb")
    read_fd.close()
    
    read_fd = open("./file", "rb")
    read_fd.close()
    
    os.rename("./symlinkedfile", "./symlinkedfile2")
    os.unlink("./symlinkedfile2")
    os.unlink("./file")
    #done
    
def main():
    """docstring for main"""
    setup = "import os; from __main__ import cycle; data_fd = open('/dev/urandom', 'rb'); data = data_fd.read(1130); data_fd.close()"
    
    read_results = []
    read_results.append(min(timeit.repeat("cycle(data)", setup = setup, repeat=3, number=10000)))

    pp = pprint.PrettyPrinter()
    pp.pprint(read_results)
    
if __name__ == '__main__':
    main()