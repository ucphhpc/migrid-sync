"""
    GRSStorage - storage super class
"""
from core.specialized import ReadWriteLock


class GRSStorage(object):
    def __init__(self):
        """docstring for __init__"""
        self.lock = ReadWriteLock.ReadWriteLock()
    def getlock(self, path):
        """
        Return a suitable lock class for this backend.
        This is a multiple-readers, single-writer lock that prioritizes the writer, 
        and has no provisions for more than one lock (path argument is ignored)."""
        #print "%s returning lock object %s" % (self.__class__.__name__, self.lock)
        return self.lock