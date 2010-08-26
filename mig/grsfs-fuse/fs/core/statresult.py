import fuse

class GRSStat(fuse.Stat):
    """FIXME: put here because if its in entities then we get a circular import!"""
    def __init__(self, posix):
        super(GRSStat, self).__init__()
        # HACK/TODO: try to clean up these data structures so we can serialize them in FUSE understandable format
        self.st_mode = posix['mode']
        self.st_ino = posix['ino']
        self.st_dev = posix['dev']
        self.st_nlink = posix['nlink']
        self.st_uid = posix['uid']
        self.st_gid = posix['gid']
        self.st_size = posix['size']
        self.st_atime = posix['atime']
        self.st_mtime = posix['mtime']
        self.st_ctime = posix['ctime']
