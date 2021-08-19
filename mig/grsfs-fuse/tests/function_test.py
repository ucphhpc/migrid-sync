#!/usr/bin/python
from builtins import object
import os, inspect,pprint,time, errno, fcntl
from stat import *

class Tests(object):
    def __init__(self):
        """docstring for __init__"""
        fd = open('/dev/urandom', 'r')
        self.binarydata = fd.read(100)
        fd.close()
        
        self.asciidata = 'Mary had a little lamp'
        
    def open_nonexisting(self):
        try:
            fd = open("therebutforthegraceofgodgoi", "r")
        except IOError as v:
            assert v.errno == errno.ENOENT
            
            
    def lock(self):
        fd = open("file", "w")
        fcntl.flock(fd, fcntl.LOCK_SH)
        fcntl.flock(fd, fcntl.LOCK_UN)
        
    def write_text(self):
        fd = open("file", "w")
        fd.write(self.asciidata)
        fd.close()
        
    def read_text(self):
        fd = open("file", "w")
        fd.write(self.asciidata)
        fd.close()
        
        fd2 = open("file", "r")
        return fd2.read() == self.asciidata
        
    def write_binary(self):
        fd = open("file", "wb")
        fd.write(self.binarydata)
        fd.close()

    def read_binary(self):
        fd = open("file", "wb")
        fd.write(self.binarydata)
        fd.close()

        fd2 = open("file", "rb")
        assert fd2.read() == self.binarydata

    def write_text_append(self):
        fd = open("file", "wa")
        fd.write(self.asciidata)
        fd.close()
        
        fd2 = open("file", "r")
        assert fd2.read() == self.asciidata
        fd2.close()

        fd2 = open("file", "a")
        fd2.write(self.asciidata)
        fd2.close()
        
        fd3 = open("file", "r")
        assert fd3.read() == self.asciidata+self.asciidata
        
    def chmod(self):
        f = open("file", "w")
        f.write("foo!")
        f.close()
        os.chmod("file", 0o500)
        filemode = S_IMODE(os.stat("file").st_mode)        
        assert filemode == 0o500
        
    def chown(self):
        """
        just change groups so we dont lose the file while testing
        groups  must exist.
        """
        f = open("file", "w")
        f.write("foo!")
        f.close()
        os.chown("file", 1007, 1007)
        d = os.stat("file")
        assert d.st_gid == 1007
        # below gives an error if not root (not root at klynge so not tested there)
        # os.chown("file", 1007, 1008)
        # d = os.stat("file")
        # assert d.st_gid == 1008
        
    def truncate(self):
        f = open("file", "w")
        f.write("foo!")
        f.close()
        d = os.stat("file")
        assert d.st_size == 4
        f = open("file", "a")
        f.truncate(2)
        f.close()
        d = os.stat("file")
        assert d.st_size == 2
        
        
    def utime(self):
        f = open("file", "w")
        f.write("foo!")
        f.close()
        data = os.stat("file")
        atime = data.st_atime
        mtime = data.st_mtime
        time.sleep(1)
        
        os.utime("file", (1, 1))
        data = os.stat("file")
        assert atime > data.st_atime
        assert mtime > data.st_mtime
        
    def dir_ops(self):
        os.mkdir("foo")
        os.rmdir("foo")
        
    def access(self):
        os.access(".", os.F_OK)
        
    def hardlink(self):
        f = open("file", "w")
        f.write("foo!")
        f.close()
        if os.path.exists("hardlinkedfile"):
            os.unlink("hardlinkedfile")
        os.link("file", "hardlinkedfile")
        assert os.path.exists("hardlinkedfile")
        f = open("hardlinkedfile", "r")
        assert f.read(-1) == "foo!"
        f.close()
        os.unlink("hardlinkedfile")
        
    def stat(self):
        f = open("file", "w")
        f.write("foo!")
        f.close()
        assert os.stat("file").st_size == 4

def main():
    """docstring for main"""
    testobj = Tests()
    testobj.write_text_append()
    results = []
    for test in [t for t in dir(testobj) if not t.startswith("_")]:
        obj = getattr(testobj, test)
        if inspect.ismethod(obj):
            try:
                if os.path.exists("file"):
                    os.unlink("file")
                obj()
                result = True
            except Exception as v:
                result = v
            results.append((test, result))
            
    pp = pprint.PrettyPrinter()
    pp.pprint(results)
        

if __name__ == '__main__':
    main()