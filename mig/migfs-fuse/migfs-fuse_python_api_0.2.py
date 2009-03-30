#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# migfs - A fuse based remote MiG home file system
# Copyright (C) 2006-2009  Jonas Bardino <bardino at diku dot dk>
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#
# Thanks to the authors of GMailFS and FlickrFS - both projects
# were used as inspiration for this module.
#

"""MiGFS provides a virtual filesystem using a Minimum intrusion
Grid account as its storage base. It relies on the miglib module
which at the time of this writing uses curl as a HTTPS transport
with client certificate support.
"""

__version__ = '0.5.1'

import ConfigParser
import array
import fuse
import logging

# For some reason this (redundant?) import is needed to get log

import logging.handlers
import os
import stat
import sys
import tempfile
import thread
import time
import traceback
from threading import Thread
from fuse import Fuse
from errno import EINVAL, ENOENT, ENOSPC, EPERM, ENOTEMPTY, ENOSYS
from stat import S_ISREG

import miglib

if not hasattr(fuse, '__version__'):
    msg = \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old"
    raise RuntimeError(msg)

fuse.fuse_python_api = (0, 2)

# Globals

migfs_config = 'migfs.conf'
default_block_size = 512 * 1024
print_block_size = 8
uri_sep = ';path='

# TODO: URI splitting should no longer be necessary

uri_len = 8000


def _log_exception(msg):
    """Log stack trace"""

    sys.stderr.write('MiG FS exception: ')
    traceback.print_exc(file=sys.stderr)
    log.exception(msg)


class DummyStat(fuse.Stat):

    """A dummy stat object to fit the API"""

    st_blksize = default_block_size
    st_rdev = None
    st_blocks = 0
    
    def __init__(self, stat_tuple):
        fuse.Stat.__init__(self)
        self.st_mode = stat_tuple[0]
        self.st_ino = stat_tuple[1]
        self.st_dev = stat_tuple[2]
        self.st_nlink = stat_tuple[3]
        self.st_uid = stat_tuple[4]
        self.st_gid = stat_tuple[5]
        self.st_size = stat_tuple[6]
        self.st_atime = stat_tuple[7]
        self.st_mtime = stat_tuple[8]
        self.st_ctime = stat_tuple[9]


class MiGAccess:

    """Class providing wrappers to all low level MiG access"""

    server = None

    def __init__(self, server='DEFAULT'):
        self.server = server

    def stat(self, path_list):
        """MiG version of un*x operation of same name"""

        status = miglib.stat_file('path=%s' % ';path='.join(path_list))
        return status

    def ls(self, path_list):
        """MiG version of un*x operation of same name"""

        status = miglib.ls_file('path=%s' % ';path='.join(path_list))
        return status

    def upload(self, src, dst):
        """MiG write all - upload file"""

        status = miglib.put_file(src, dst, False, False)
        return status

    def download(self, src, dst):
        """MiG read all - download file"""

        status = miglib.get_file(src, dst)
        return status

    def read(
        self,
        first,
        last,
        src,
        dst,
        ):
        """MiG read - read byte sequence from remote src file into
        local dst file. The first and last parameters specify the
        offset in the src file. The dst file will be truncated to
        only contain the specified range.
        """

        # TODO: allow file-like object as dst

        # Parse stdout and send data to dst file

        status = miglib.read_file(first, last, src, '-')

        # read still uses old (0, '0\ncontents') output format!

        out = (status[1])[1:]
        dst_fd = open(dst, 'wb')
        dst_fd.seek(0)
        dst_fd.writelines(out)
        dst_fd.close()
        return status

    def write(
        self,
        first,
        last,
        src,
        dst,
        ):
        """MiG write - write byte sequence in local src file to
        remote dst file. The first and last parameters specify the
        offset in the dst file. The data are read from the beginning
        of the src file.
        """

        status = miglib.write_file(first, last, src, dst)
        return status

    def mv(self, src_list, dst):
        """MiG version of un*x operation of same name"""

        status = miglib.mv_file('src=%s' % ';src='.join(src_list), dst)
        return status

    def touch(self, path_list):
        """MiG version of un*x operation of same name"""

        status = miglib.touch_file('path=%s' % ';path='.join(path_list))
        return status

    def mkdir(self, path_list, mode):
        """MiG version of un*x operation of same name"""

        # TODO: mode is not supported
        # status = miglib.mk_dir(mode, "path=%s" % (";path=").join(path_list))

        status = miglib.mk_dir('path=%s' % ';path='.join(path_list))
        return status

    def rm(self, path_list):
        """MiG version of un*x operation of same name"""

        status = miglib.rm_file('path=%s' % ';path='.join(path_list))
        return status

    def rmdir(self, path_list):
        """MiG version of un*x operation of same name"""

        status = miglib.rm_dir('path=%s' % ';path='.join(path_list))
        return status

    def truncate(self, path_list, size):
        """MiG version of un*x operation of same name"""

        status = miglib.truncate_file(size, 'path=%s'
                 % ';path='.join(path_list))
        return status

    def statfs(self):
        """MiG version of un*x operation of same name"""

        # TODO: better prediction - requires remote support

        (max_space, used_space) = (((256 * 1024) * 1024) * 1024, (16
                                    * 1024) * 1024)
        return (0, (max_space, used_space))


class InodeCache:

    """
    Class holding all cached inode data: requires locking in
    order to allow multithreaded background update of cache.
    """

    def __init__(self, timeout):
        """Inodes must have unique IDs - use a dictionary
        for storing. Inodes are cached for timeout seconds.
        """

        self.__cache = {}
        self.__lock = thread.allocate_lock()
        self.__inode_timeout = timeout

    def read_inode(self, path):
        """Lookup and return inode data in a thread safe way"""

        inode = None
        time_stamp = -1
        self.__lock.acquire()
        if self.__cache.has_key(path):
            (time_stamp, inode) = self.__cache[path]
        self.__lock.release()
        return (time_stamp, inode)

    def write_inode(self, path, inode):
        """Write inode in a thread safe way"""

        self.__lock.acquire()
        now = time.time()
        self.__cache[path] = (now, inode)
        self.__lock.release()

    def update_inode(self, path, fields):
        """Update inode with the data from the fields dictionary
        in a thread safe way"""

        self.__lock.acquire()
        if self.__cache.has_key(path):
            (time_stamp, inode) = self.__cache[path]
            for (key, val) in fields.items():
                inode[key] = val
        self.__lock.release()

    def delete_inode(self, path):
        """Delete inode in a thread safe way"""

        self.__lock.acquire()
        if self.__cache.has_key(path):
            del self.__cache[path]
        self.__lock.release()


class FileBuffer:

    """Generic file buffering class"""

    __buffer = None

    def __init__(self, size):
        self.__buffer = list(' ' * size)

    def write(self, buf, pos=0):
        """Write buf into buffer at position, pos"""

        self.__buffer[pos:pos + len(buf)] = buf

    def read(self, size, pos=0):
        """Read size bytes of buffer from position, pos"""

        return self.__buffer[pos:pos + size]


class OpenFile:

    """
    Class holding any currently open files. Includes a reference
    to a cached instance of the last data block retrieved for
    performance.
    """

    def __init__(self, path, inode_cache):
        self.path = path
        self.__inode_cache = inode_cache
        self.ref_count = 1
        self.tmpfile = None
        self.blocks_read = 0
        self.is_dirty = False
        self.blocksize = default_block_size
        self.buffer = FileBuffer(self.blocksize)
        self.current_offset = -1
        self.current_block = -1
        self.last_block = -1
        self.last_block_read = None
        self.last_block_buffer = list(' ' * self.blocksize)
        self.mig_access = MiGAccess()

    def close(self):
        """Closes this file by committing any changes to the users
        MiG account."""

        if self.is_dirty:
            self.commit_to_mig()

    def write(self, buf, offset):
        """
        Write data to file from buf, offset by offset bytes into
        the file.
        Commit changes to MiG if the file buffer needs to be flushed.
        """

        buflen = len(buf)
        remain_len = buflen

        # log.debug("writing buf %s ... to offset %d: buffer is %s" % \
        #          (buf[:print_block_size],
        #          offset, self.buffer.read(print_block_size)))

        log.debug('writing %d bytes at offset %d' % (buflen, offset))

        self.current_block = self.current_offset / self.blocksize
        offset_block = offset / self.blocksize

        # refresh buffer if it is not ready

        if offset_block != self.current_block:

            # Write back changes before loading new data into
            # the buffer

            if self.is_dirty:
                log.debug('committing modified block %d'
                           % self.current_block)
                self.commit_to_mig()

            log.debug('buffering new block %d' % offset_block)
            self.current_block = offset_block
            self.buffer.write(self.read_from_mig(self.current_block), 0)
            self.current_offset = offset

        # The caching buffer now contains the block of data to be
        # modified, and current_offset is inititalized

        written = 0

        # Blockwise update of data

        while remain_len > 0:
            buffer_offset = self.current_offset % self.blocksize
            write_len = min(remain_len, self.blocksize - buffer_offset)
            log.debug('writing block of %d b at offset %d (%d)'
                       % (write_len, self.current_offset,
                      buffer_offset))

            # log.debug("updating buffer: buf is %s ... " % \
            #          buf[:print_block_size])

            self.buffer.write(buf[written:written + write_len],
                              buffer_offset)
            remain_len -= write_len
            written += write_len

            # update inode data
            # now = int(time.time())
            # updates = {"atime":now, "ctime":now, "mtime":now}

            updates = {}
            (time_stamp, inode) = \
                self.__inode_cache.read_inode(self.path)
            if offset + written > inode['size']:
                updates['size'] = offset + written
            if updates:
                self.__inode_cache.update_inode(self.path, updates)
            self.current_offset += write_len
            self.is_dirty = True
            if self.current_offset / self.blocksize\
                 > self.current_block:
                self.last_block = self.current_block
                self.commit_to_mig()
                self.current_block += 1
                if remain_len > 0:
                    self.buffer.write(self.read_from_mig(self.current_block),
                            0)
                    self.is_dirty = False

        log.debug('wrote %s bytes offset: %s current_offset: %s'
                   % (buflen, offset, self.current_offset))
        return buflen

    def commit_to_mig(self):
        """Send any unsaved data to MiG account of the user"""

        if not self.is_dirty:
            return 0
        if not self.tmpfile:
            self.tmpfile = tempfile.NamedTemporaryFile()

        # log.debug("seeking to block %d in tempfile" % 0)

        self.tmpfile.seek(0)
        arr = array.array('c')
        arr.fromlist(self.buffer.read(self.blocksize))
        log.debug('writing %s to offset %d'
                   % (self.buffer.read(print_block_size),
                  self.tmpfile.tell()))
        self.tmpfile.write(arr.tostring())
        self.tmpfile.flush()

        # log.debug("writing tmp file %s back to MiG: %s" % \
        #          (self.tmpfile.name, self.path))

        first = self.current_block * self.blocksize

        # Last should be last actual byte - not end of cache block

        buflen = self.blocksize

        (time_stamp, inode) = self.__inode_cache.read_inode(self.path)
        if self.current_block >= inode['size'] / self.blocksize:
            buflen = inode['size'] % self.blocksize

        # correct for inclusion of first and last byte in write

        last = (first + buflen) - 1
        log.debug('writing %d-%d from %s to %s' % (first, last,
                  self.tmpfile.name, self.path))
        (status, out) = self.mig_access.write(first, last,
                self.tmpfile.name, self.path)
        if status != 0:
            log.error('commit write failed (%s): %s' % (status, out))
            return 1
        else:
            log.debug('commit write ok')
            self.is_dirty = False
            now = int(time.time())
            updates = {'atime': now, 'ctime': now, 'mtime': now}
            self.__inode_cache.update_inode(self.path, updates)
            return 0

    def read(self, readlen, offset):
        """Read readlen bytes from an open file at position offset
        bytes into the data of the file"""

        (time_stamp, inode) = self.__inode_cache.read_inode(self.path)
        readlen = min(inode['size'] - offset, readlen)
        outbuf = list(' ' * readlen)

        # now = int(time.time())
        # self.__inode_cache.update_inode(self.path, {"atime":now})

        toread = readlen
        upto = 0
        while toread > 0:
            readoffset = (offset + upto) % self.blocksize
            thisread = min(toread, min(self.blocksize - readoffset
                            % self.blocksize, self.blocksize))
            bytes = (offset + upto) / self.blocksize
            (from_index, to_index) = (readoffset, readoffset + thisread)
            outbuf[upto:] = \
                self.read_from_mig(bytes)[from_index:to_index]
            upto += thisread
            toread -= thisread
            log.debug('still to read: %s' % toread)

        log.debug('returning %d bytes from read' % len(outbuf))
        return outbuf

    def read_from_mig(self, readblock):
        """Read data block with block number 'readblock' for this
        file in MiG home"""

        # log.debug("about to try and find path: %s blocknumber: %s" % \
        #          (self.path, readblock))

        if self.last_block_read == readblock:
            return self.last_block_buffer
        if not self.tmpfile:
            self.tmpfile = tempfile.NamedTemporaryFile()
        self.last_block_read = readblock
        content_list = list(' ' * self.blocksize)
        content = ''
        first = readblock * self.blocksize
        (time_stamp, inode) = self.__inode_cache.read_inode(self.path)
        last = min(first + self.blocksize, inode['size']) - 1

        # Don't waste time trying to read beyond EOF
        # This would otherwise happen during append operation

        if last <= first:
            self.tmpfile.truncate(0)
            return content_list

        log.debug('reading %d-%d of %s - inode size is %d' % (first,
                  last, self.path, inode['size']))
        (status, out) = self.mig_access.read(first, last, self.path,
                self.tmpfile.name)
        if status != 0:
            log.error('%s: failed to fetch %d-%d of %s into %s: %s' % (
                status,
                first,
                last,
                self.path,
                self.tmpfile.name,
                self.tmpfile.read(print_block_size),
                ))
            self.tmpfile.truncate(0)
            return content_list

        # log.debug("%s: fetched %s into %s" % (status, self.path,
        #                                      self.tmpfile.name))

        now = int(time.time())
        self.__inode_cache.update_inode(self.path, {'atime': now})

        try:
            tmp_fd = open(self.tmpfile.name, 'r')
            tmp_fd.seek(0)
            content = tmp_fd.read(self.blocksize)
            log.debug('read %d bytes from block %d of %s'
                       % (len(content), readblock, self.tmpfile.name))
            tmp_fd.close()
        except Exception, err:
            log.error('failed to read block %s from %s: %s'
                       % (readblock, self.tmpfile, err))
        self.last_block_buffer = content
        content_list[0:] = content
        return content_list


class MiGfs(Fuse):

    """Main MiG filessytem class: implements all required basic
    file ops. Please note that this class is *not* thread safe, so
    Fuse must be configured to run with the multithreaded flag set
    to False. I.e. the open file and inode caches do not support
    concurrent access and it probably wouldn't improve performance
    significantly either as the performance is network bound.
    """

    mount_point = None
    flags = 1
    mig_access = None
    __threads = None
    __open_files = None
    __inode_cache = None
    head_lines = 5

    def __init__(self, *args, **kw):
        blocksize = -1
        #print "DEBUG: got args and kwargs in MiGFS: %s, %s" % (args, kw)
        if kw.has_key('blocksize'):
            blocksize = kw['blocksize']

            # Fuse does and should not know about blocksize - so remove it

            del kw['blocksize']
        if kw.has_key('password'):

            # miglib allows overriding global password

            miglib.password = kw['password']

            # Fuse does and should not know about password - so remove it

            del kw['password']
        #print "DEBUG: passing args and kwargs to Fuse: %s, %s" % (args, kw)
        Fuse.__init__(self, *args, **kw)

        # self.mount_point = mount_point

        self.__inode_timeout = inode_timeout

        # log.info("Mountpoint: %s" % self.mount_point)
        # log.info("Unnamed mount options: %s" % (self.optlist, ))

        # obfuscate sensitive fields before logging

        # loggable_optdict = self.optdict.copy()
        # loggable_optdict['password'] = '*' * 8
        # log.info("Named mount options: %s" % (loggable_optdict, ))

        self.__threads = []

        # do stuff to set up your filesystem here, if you want

        self.__open_files = {}
        self.__inode_cache = InodeCache(inode_timeout)
        parent_inode = {
            'dev': 0,
            'ino': 42,
            'mode': 0755,
            'nlink': 1,
            'uid': 0,
            'gid': 0,
            'rdev': 0,
            'size': 0,
            'atime': 0,
            'mtime': 0,
            'ctime': 0,
            }

        # Hack to make prefetch stop complaining about parent dir

        self.__inode_cache.write_inode('/..', parent_inode)

        global default_block_size
        if blocksize > 0:
            default_block_size = int(blocksize)

        self.mig_access = MiGAccess()
        log.info('Connected to mig')

    def __split_path_list(
        self,
        path_list,
        separator,
        max_len,
        ):
        """Create a list of path_list sublists so that when calling
        separator.join(sublist) on each of the sublists the results
        strings will not exceed max_length in total length. This is
        necessary when calling miglib with long path lists because
        there's amn upper bound on the underlying URI length.
        """

        part_list = [[]]
        head_len = len(separator)
        part = part_list[-1]
        part_len = 0

        # sub_total = 0

        for path in path_list:
            next_len = len(path) + head_len
            if part_len + next_len > max_len:
                part_list.append([])
                part = part_list[-1]
                part_len = 0
            part.append(path)

            # sub_total += next_len

            part_len += next_len

        # total = len("%s%s" % (separator, separator.join(path_list)))
        # print "Done: split list of %d paths of total length %d" % \
        #      (len(path_list), total)
        # print "into %d sublists of total length %d" % \
        #      (len(part_list), sub_total)

        return part_list

    def getattr(self, path):
        """Read file attributes"""

        log.debug('get attr: %s' % path)

        # TODO: remove internal use of __getinode
        # - use __inode_cache operations instead

        inode = self.__getinode(path)
        if inode:
            if log.isEnabledFor(logging.DEBUG):
                log.debug('inode %s' % inode)
            stat_tuple = (
                inode['mode'],
                inode['ino'],
                inode['dev'],
                inode['nlink'],
                inode['uid'],
                inode['gid'],
                inode['size'],
                inode['atime'],
                inode['mtime'],
                inode['ctime'],
                )
            if log.isEnabledFor(logging.DEBUG):
                log.debug('stat_tuple: %s' % (stat_tuple, ))
            st = DummyStat(stat_tuple)
            return st
        else:
            err = OSError('No such file: %s' % path)
            err.errno = ENOENT
            raise err

    def readlink(self, path):
        """Don't expose symlinks used internally in MiG"""

        log.debug("readlink: path='%s'" % path)
        return path

    def readdir(self, path, offset):
        """Return contents of specified dir"""

        if not path.endswith('/'):
            path += '/'
        try:
            log.debug('getting dir %s' % path)
            dir_list = ['.', '..']

            (status, out) = self.mig_access.ls([path])
            if status != 0:
                raise IOError("ls failed on '%s': %s" % (path, out))
            dir_list += out[self.head_lines:]
            (time_stamp, dir_inode) = \
                self.__inode_cache.read_inode('%s%s' % (path, dir_list))
            if len(dir_list) > 1 and not dir_inode:

                # Unknown first entry: Do full stat here to avoid
                # tons of slow single stat requests later

                log.debug('prefetching dir inodes')

                for part in self.__split_path_list(dir_list, uri_sep,
                        uri_len):
                    log.debug('prefetching dir inodes of %d items'
                               % len(part))

                    prefetch_thread = \
                        Thread(target=self.__prefetch_inodes,
                               args=(path, part))
                    prefetch_thread.start()
                    self.__threads.append(prefetch_thread)
                for prefetch_thread in self.__threads:
                    prefetch_thread.join()
        except Exception, exc:
            log.error('migfs.py:MiGfs:getdir: %s: %s!' % (path, exc))
            _log_exception('got exception when listing dir: %s' % path)
            dir_list = None
        for entry in [entry.strip() for entry in dir_list]:
            yield fuse.Direntry(entry)

    def unlink(self, path):
        """Unlink file"""

        log.debug('unlink called on: %s' % path)
        try:
            (status, out) = self.mig_access.rm([path])
            if status != 0:
                raise IOError("rm failed on '%s': %s" % (path, out))
            self.__inode_cache.delete_inode(path)
            return status
        except Exception, exc:
            log.error('migfs.py:MiGfs:unlink: %s: %s!' % (path, exc))
            msg = 'Error unlinking file %s' % path
            _log_exception(msg)
            err = OSError(msg)
            err.errno = EINVAL
            raise err

    def rmdir(self, path):
        """Delete directory"""

        log.debug('rmdir called on: %s' % path)
        try:
            (status, out) = self.mig_access.rmdir([path])
            if status != 0:
                raise IOError("rmdir failed on '%s': %s" % (path, out))
        except Exception, exc:
            log.error('migfs.py:MiGfs:rmdir: %s: %s!' % (path, exc))
            msg = 'Error unlinking dir %s' % path
            err = OSError(msg)
            err.errno = ENOTEMPTY
            raise err
        try:
            self.__inode_cache.delete_inode(path)

            # update number of links in parent directory

            ind = path.rindex('/')
            parent_dir = path[:ind]
            log.debug('about to rmdir with parent_dir: %s' % parent_dir)
            if not parent_dir:
                parent_dir = '/'
            self.__inode_cache.delete_inode(parent_dir)
            return 0
        except Exception, exc:
            log.error('migfs.py:MiGfs:rmdir: %s: %s!' % (path, exc))
            msg = 'Error unlinking dir %s' % path
            _log_exception(msg)
            err = OSError(msg)
            err.errno = EINVAL
            raise err

    def symlink(self, src, dst):
        """Symlink is not supported in MiG - raise error"""

        log.debug("symlink: src='%s', dst='%s'" % (src, dst))
        msg = 'MiG does not allow symlinks'
        _log_exception(msg)
        err = OSError(msg)
        err.errno = ENOSYS
        raise err

    def rename(self, src, dst):
        """Rename src to dst"""

        log.debug('rename from: %s to: %s' % (src, dst))
        try:
            (status, out) = self.mig_access.mv([src], dst)
            if status != 0:
                raise IOError("mv failed on '%s': %s" % (path, out))
            self.__inode_cache.delete_inode(src)
            return status
        except Exception, exc:
            log.error('migfs.py:MiGfs:rename: %s: %s!' % (path, exc))
            msg = 'Could not rename %s to %s' % (src, dst)
            _log_exception(msg)
            err = OSError(msg)
            err.errno = ENOSPC
            raise err

    def link(self, src, dst):
        """Hardlink is not supported in MiG - raise error"""

        log.debug("hard link: src='%s', dst='%s'" % (src, dst))
        msg = 'MiG does not allow hardlinks'
        _log_exception(msg)
        err = OSError(msg)
        err.errno = ENOSYS
        raise err

    def chmod(self, path, mode):
        """MiG does not support chmod: warn on actual attempts and
        ignore the rest.
        """

        log.debug('chmod called with path: %s mode: %s' % (path, mode))
        inode = self.__getinode(path)
        if not inode or inode['mode'] != mode:
            msg = 'MiG does not allow changing mode'
            log.warning(msg)
            err = OSError(msg)
            err.errno = EPERM
            raise err

    def chown(
        self,
        path,
        user,
        group,
        ):
        """MiG does not support chown: warn on actual attempts and
        ignore the rest.
        """

        log.debug('chown called on %s with user: %s and group: %s'
                   % (path, user, group))
        inode = self.__getinode(path)
        if not inode or inode['uid'] != user or inode['gid'] != group:
            msg = 'MiG does not allow changing owner'
            _log_exception(msg)
            err = OSError(msg)
            err.errno = EPERM
            raise err

    def truncate(self, path, size):
        """Truncate file"""

        log.debug('truncate %s to size: %s' % (path, size))
        try:
            (status, out) = self.mig_access.truncate([path], size)
            if status != 0:
                raise IOError("truncate failed on '%s': %s" % (path,
                              out))
            now = int(time.time())
            updates = {
                'atime': now,
                'mtime': now,
                'ctime': now,
                'size': size,
                }
            self.__inode_cache.update_inode(path, updates)
        except Exception, exc:
            log.error('migfs.py:MiGfs:truncate: %s: %s!' % (path, exc))
            msg = 'Could not truncate %s to %s' % (path, size)
            _log_exception(msg)
            err = OSError(msg)
            err.errno = EINVAL
            raise err

    def mknod(
        self,
        path,
        mode,
        dev,
        ):
        """ Python has no os.mknod, so we can only do some things.
        Furthermore MiG does not allow anything but regular files.
        """

        log.debug('mknod %s, mode %s, dev %s' % (path, mode, dev))
        if S_ISREG(mode):
            (status, out) = self.mig_access.touch([path])
            if status != 0:
                raise IOError("touch failed on '%s': %s" % (path, out))
        else:
            msg = 'MiG does not allow making device files'
            _log_exception(msg)
            return -EINVAL

    def mkdir(self, path, mode):
        """Create directory"""

        log.debug('mkdir path: %s mode: %s' % (path, mode))
        try:
            (status, out) = self.mig_access.mkdir([path], mode)
            if status != 0:
                raise IOError("mkdir failed on '%s': %s" % (path, out))
            ind = path.rindex('/')
            log.debug('ind: %d' % ind)
            parent_dir = path[:ind]
            if not parent_dir:
                parent_dir = '/'
            self.__inode_cache.delete_inode(parent_dir)
            return status
        except Exception, exc:
            log.error('migfs.py:MiGfs:mkdir: %s: %s!' % (path, exc))
            msg = 'Error creating dir %s' % path
            _log_exception(msg)
            err = OSError(msg)
            err.errno = EINVAL
            raise err

    def utime(self, path, times):
        """Change timestamp of file: times is a 2-tuple of atime and mtime"""

        log.debug('utime for path: %s times: %s' % (path, times))
        try:

            # TODO: should change all remote timestamps, too

            (status, out) = self.mig_access.touch([path])
            if status != 0:
                raise IOError("touch failed on '%s': %s" % (path, out))
            updates = {'atime': times[0], 'mtime': times[1],
                       'ctime': times[1]}
            self.__inode_cache.update_inode(path, updates)
            return status
        except Exception, exc:
            log.error('migfs.py:MiGfs:utime: %s: %s!' % (path, exc))
            msg = 'Error changing timestamps on %s' % path
            _log_exception(msg)
            err = OSError(msg)
            err.errno = EINVAL
            raise err

    def open(self, path, flags):
        """Open file"""

        log.debug('migfs.py:MiGfs:open: %s' % path)
        try:
            open_file = OpenFile(path, self.__inode_cache)
            self.__open_files[path] = open_file
            return 0
        except Exception, exc:
            log.error('migfs.py:MiGfs:open: %s: %s!' % (path, exc))
            msg = 'Error opening file %s' % path
            _log_exception(msg)
            err = OSError(msg)
            err.errno = EINVAL
            raise err

    def read(
        self,
        path,
        readlen,
        offset,
        ):
        """Read readlen bytes from file at position given by offset"""

        try:
            log.debug('migfs.py:MiGfs:read: %s' % path)
            log.debug('reading len: %s offset: %s' % (readlen, offset))
            open_file = self.__open_files[path]
            buf = open_file.read(readlen, offset)
            return ''.join(buf)
        except Exception, exc:
            log.error('migfs.py:MiGfs:read: %s: %s!' % (path, exc))
            msg = 'Error reading file: %s' % path
            _log_exception(msg)
            err = OSError(msg)
            err.errno = EINVAL
            raise err

    def write(
        self,
        path,
        buf,
        offset,
        ):
        """Write buf to file at position given by offset"""

        try:
            log.debug('migfs.py:MiGfs:write: %s' % path)
            if log.isEnabledFor(logging.DEBUG):
                log.debug('writing: %s' % buf[:print_block_size])
            open_file = self.__open_files[path]
            written = open_file.write(buf, offset)
            return written
        except Exception, exc:
            log.error('migfs.py:MiGfs:write: %s: %s!' % (path, exc))
            msg = 'Error writing file: %s' % path
            _log_exception(msg)
            err = OSError(msg)
            err.errno = EINVAL
            raise err

    def release(self, path, flags):
        """Close file"""

        log.debug('migfs.py:MiGfs:release: %s %s' % (path, flags))
        try:
            open_file = self.__open_files[path]
            open_file.close()
            del self.__open_files[path]
        except Exception, exc:
            log.error('migfs.py:MiGfs:release: %s: %s!' % (path, exc))
            msg = 'Error releasing file: %s' % path
            err = OSError(msg)
            err.errno = ENOENT
            raise err
        return 0

    def statfs(self):
        """Should return a tuple with the following elements in
        respective order:

        F_BSIZE - Preferred file system block size. (int)
        F_FRSIZE - Fundamental file system block size. (int)
        F_BLOCKS - Total number of blocks in the filesystem. (long)
        F_BFREE - Total number of free blocks. (long)
        F_BAVAIL - Free blocks available to non-super user. (long)
        F_FILES - Total number of file nodes. (long)
        F_FFREE - Total number of free file nodes. (long)
        F_FAVAIL - Free nodes available to non-super user. (long)
        F_FLAG - Flags. System dependent: see 'man 2 statvfs'. (int)
        F_NAMEMAX - Maximum file name length. (int)
        Feel free to set any of the above values to 0, which tells
        the kernel that the info is not available.
        """

        log.debug('migfs.py:MiGfs:statfs')
        block_size = 1024
        total_blocks = 0L
        blocks_free = 0L
        blocks_free_user = 0L
        files = 0L
        files_free = 0L
        files_free_user = 0L
        namelen = 255
        (status, out) = self.mig_access.statfs()
        if status != 0:
            raise IOError("statfs failed on '%s': %s" % (path, out))
        (fs_blocks, used) = out
        if fs_blocks:
            total_blocks = long(fs_blocks / block_size)
            blocks_free = long((fs_blocks - used) / block_size)
            blocks_free_user = blocks_free
            log.debug('total blocks: %s' % total_blocks)
            log.debug('blocks_free: %s' % blocks_free)
        fs_stats = (
            block_size,
            total_blocks,
            blocks_free,
            blocks_free_user,
            files,
            files_free,
            namelen,
            )
        return fs_stats

    def fsync(self, path, isfsyncfile):
        """Sync buffers to file"""

        log.debug('migfs.py:MiGfs:fsync: path=%s, isfsyncfile=%s'
                   % (path, isfsyncfile))
        open_file = self.__open_files[path]
        open_file.commit_to_mig()
        return 0

    def __prefetch_inodes(self, dir_path, path_list):
        """Speed optimization: threaded fetching of inode data
        to avoid every single stat operation to take ages.
        """

        stat_list = []
        if not dir_path.endswith('/'):
            dir_path += '/'
        for entry in path_list:
            path = '%s%s' % (dir_path, entry.strip())
            log.debug('prefetch_inodes: checking %s' % path)
            (time_stamp, file_inode) = \
                self.__inode_cache.read_inode(path)
            if not file_inode:
                stat_list.append(path)

        if not stat_list:
            return []

        status = '1'
        stat = None
        stat_out = []
        inode_list = []
        mapping = {
            'device': 'dev',
            'inode': 'ino',
            'mode': 'mode',
            'nlink': 'nlink',
            'uid': 'uid',
            'gid': 'gid',
            'rdev': 'rdev',
            'size': 'size',
            'atime': 'atime',
            'mtime': 'mtime',
            'ctime': 'ctime',
            }
        fields = len(mapping.keys())
        try:
            log.debug('prefetch_inodes %s from MiG'
                       % ', '.join(stat_list))
            (status, out) = self.mig_access.stat(stat_list)
            if status != 0:
                raise IOError("stat failed on '%s': %s" % (path, out))

            # It's common to stat nonexistant files, but not
            # in prefetch

            if len(out) - self.head_lines != fields * len(stat_list):
                msg = 'failed to stat %s: %s (%d =? %d)'\
                     % (', '.join(stat_list), out[self.head_lines:],
                        len(out) - self.head_lines, fields
                         * len(stat_list))
                raise Exception(msg)
        except Exception, exc:
            _log_exception('failed to stat MiG path: %s'
                            % ', '.join(stat_list))
            return inode_list

        data = out[self.head_lines:]
        entry = -1
        for path in stat_list:
            entry += 1
            inode = {}
            for line in data[entry * fields:(entry + 1) * fields]:
                parts = line.strip().split('\t')
                if len(parts) != 2:
                    log.warning('prefetch_inodes %s: illegal format: %s'
                                 % (path, parts))
                    continue
                (name, val) = parts
                inode[mapping[name]] = int(val)
                inode['uid'] = int(os.getuid())
                inode['gid'] = int(os.getgid())
            log.debug('prefetch_inodes: %s; inode %s' % (path, inode))
            if inode:
                self.__inode_cache.write_inode(path, inode)
                inode_list.append(inode)
        return inode_list

    def __getinode(self, path):
        """Read inode information"""

        status = '1'
        log.debug('getinode: %s' % path)
        (time_stamp, inode) = self.__inode_cache.read_inode(path)
        now = time.time()
        if inode:
            if now - time_stamp > self.__inode_timeout:
                log.info('getinode expiring old inode for %s' % path)
                try:
                    if self.__open_files.has_key(path):
                        self.fsync(path, False)
                        log.debug('getinode synced data for %s' % path)
                except Exception, err:
                    log.error('getinode failed to commit file %s: %s'
                               % (path, err))
                    _log_exception('getinode')

                # expire cached inode contents

                log.debug('getinode resetting expired inode for %s'
                           % path)
                inode = {}
            else:
                log.debug('getinode %s from cache' % path)
                return inode
        else:
            inode = {}

        # Always cache inodes for path: even misses are useful since
        # programs often repeatedly try to open backup, etc files

        self.__inode_cache.write_inode(path, inode)
        try:
            log.debug('getinode: stat %s from MiG' % path)
            (status, out) = self.mig_access.stat([path])
            if status != 0:
                raise IOError("stat failed on '%s': %s" % (path, out))
        except Exception, exc:
            _log_exception('failed to stat MiG path: %s' % path)
            return inode

        # it is quite common to stat non-existant files

        if out and not out[0].startswith('Exit code: 0'):
            log.debug('getinode: stat output %s - stat miss' % out[0])
            return inode

        log.debug('getinode: out is %s' % out)
        data = out[self.head_lines:]
        mapping = {
            'device': 'dev',
            'inode': 'ino',
            'mode': 'mode',
            'nlink': 'nlink',
            'uid': 'uid',
            'gid': 'gid',
            'rdev': 'rdev',
            'size': 'size',
            'atime': 'atime',
            'mtime': 'mtime',
            'ctime': 'ctime',
            }
        for line in data:
            parts = line.strip().split('\t')
            if len(parts) != 2:
                log.warning('getinode: %s: illegal format: %s' % (path,
                            parts))
                continue
            (name, val) = parts
            inode[mapping[name]] = int(val)
        if inode:

            # Overwrite uid/gid and save to cache

            inode['uid'] = int(os.getuid())
            inode['gid'] = int(os.getgid())
            self.__inode_cache.write_inode(path, inode)
        log.debug('getinode: %s; inode %s' % (path, inode))
        return inode


# Setup logging - use stdout for now

log = logging.getLogger('migfs')
default_level = logging.WARNING
log.setLevel(default_level)
default_format = \
    logging.Formatter('%(asctime)s %(levelname)-10s %(message)s',
                      '%x %X')
stdout_handler = logging.StreamHandler(sys.stdout)

# stdout_handler.setFormatter(default_format)

log.addHandler(stdout_handler)

# Set up inode caching

inode_timeout = 300

conf = ConfigParser.ConfigParser()
try:
    conf.read(migfs_config)
    sections = conf.sections()
    if 'log' in sections:
        options = conf.options('log')
    if 'level' in options:
        level = conf.get('log', 'level')
        log.setLevel(logging._levelNames[level])
    if 'logfile' in options:
        logfile = os.path.abspath(os.path.expanduser(conf.get('log',
                                  'logfile')))
        file_handler = logging.handlers.RotatingFileHandler(logfile, 'a'
                , 5242880, 3)
        file_handler.setFormatter(default_format)
        log.addHandler(file_handler)
        log.removeHandler(stdout_handler)

    if 'connection' in sections:
        options = conf.options('connection')
        if 'retries' in options:
            connection_retries = conf.getint('connection', 'retries')

    if 'caching' in sections:
        options = conf.options('caching')
        if 'inode_timeout' in options:
            inode_timeout = conf.getint('caching', 'inode_timeout')
except Exception, fs_err:
    log.warning('Unable to read configuration file %s: %s'
                 % (migfs_config, fs_err))


def main(mount_point, fuse_flags=None, main_options=None):
    """Main: set up mount and handle requests"""

    usage = """
Userspace MiG file system

""" + Fuse.fusage

    # Must set mount point implicitly to fuse

    
    sys.argv = ['migfs.py', mount_point]
    if fuse_flags:
        # -d for debug implies -f for foreground mode
        if '-d' in fuse_flags and not '-f' in fuse_flags:
            fuse_flags.append('-f')
        sys.argv += fuse_flags
    if not main_options:
        main_options = {}
        
    main_options['version'] = '%prog ' + fuse.__version__
    main_options['usage'] = usage
    main_options['dash_s_do'] = 'setsingle'
    server = MiGfs(**main_options)
    server.parse(errex=1)

    # IMPORTANT: Fuse multithreaded must be disabled as migfs is not thread safe

    server.multithreaded = False
    server.main()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
