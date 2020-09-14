#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fileio - wrappers to keep file I/O in a single replaceable module
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
# -- END_HEADER ---
#

"""IO operations"""

from __future__ import print_function
from __future__ import absolute_import

from hashlib import md5, sha1, sha256, sha512
import errno
import fcntl
import os
import shutil
import sys
import tempfile
import time
import zipfile

# NOTE: We expose optimized walk function directly for ease and efficiency.
#       Requires stand-alone scandir module on python 2 whereas the native os
#       functions are built-in and optimized similarly on python 3+
slow_walk = False
if sys.version_info[0] < 3:
    from os import walk
else:
    try:
        from distutils.version import StrictVersion
        from scandir import walk, __version__ as scandir_version
        if StrictVersion(scandir_version) < StrictVersion("1.3"):
            # Important os.walk compatibility utf8 fixes were not added until 1.3
            raise ImportError(
                "scandir version is too old: fall back to os.walk")
    except ImportError as err:
        #print("DEBUG: not using scandir: %s" % err)
        slow_walk = True
        walk = os.walk

from mig.shared.base import force_utf8_rec
from mig.shared.defaults import default_chunk_size, default_max_chunks
from mig.shared.serial import dump, load

__valid_hash_algos = {'md5': md5, 'sha1': sha1, 'sha256': sha256,
                      'sha512': sha512}


def supported_hash_algos():
    """A list of supported hash algorithm names"""
    return __valid_hash_algos.keys()


def write_chunk(path, chunk, offset, logger, mode='r+b'):
    """Wrapper to handle writing of chunks with offset to path.
    Creates file first if it doesn't already exist.
    """
    logger.info('writing chunk to %s at offset %d' % (path, offset))

    # create dir and file if it does not exists

    (head, _) = os.path.split(path)
    if not os.path.isdir(head):
        try:
            os.mkdir(head)
        except Exception as err:
            logger.error('could not create dir %s' % err)
    if not os.path.isfile(path):
        try:
            open(path, "w").close()
        except Exception as err:
            logger.error('could not create file %s' % err)
    try:
        filehandle = open(path, mode)
        # Make sure we can write at requested position, filling if needed
        try:
            filehandle.seek(offset)
        except:
            filehandle.seek(0, 2)
            file_size = filehandle.tell()
            for _ in xrange(offset - file_size):
                filehandle.write('\0')
        logger.info('write %s chunk of size %d at position %d' %
                    (path, len(chunk), filehandle.tell()))
        filehandle.write(chunk)
        filehandle.close()
        logger.debug('file chunk written: %s' % path)
        return True
    except Exception as err:
        logger.error('could not write %s chunk at %d: %s' %
                     (path, offset, err))
        return False


def write_file(content, path, logger, mode='w', make_parent=True, umask=None):
    """Wrapper to handle writing of contents to path"""
    logger.debug('writing file: %s' % path)

    # create dir if it does not exists

    (head, _) = os.path.split(path)
    if umask is not None:
        old_umask = os.umask(umask)
    if not os.path.isdir(head) and make_parent:
        try:
            logger.debug('making directory: %s' % head)
            os.mkdir(head)
        except Exception as err:
            logger.error('could not create dir: %s' % err)
    try:
        filehandle = open(path, mode)
        filehandle.write(content)
        filehandle.close()
        # logger.debug('file written: %s' % path)
        retval = True
    except Exception as err:
        logger.error('could not write file: %s, error: %s' % (path, err))
        retval = False
    if umask is not None:
        os.umask(old_umask)
    return retval


def read_file(path, logger):
    """Wrapper to handle reading of contents from path"""
    #logger.debug('reading file: %s' % path)
    content = None
    try:
        filehandle = open(path)
        content = filehandle.read()
        filehandle.close()
        #logger.debug('read %db from: %s' % (len(content), path))
    except Exception as err:
        logger.error('could not read %s: %s' % (path, err))
    return content


def read_tail(path, lines, logger):
    """Read last lines from path"""
    out_lines = []
    try:
        #logger.debug("loading %d lines from %s" % (lines, path))
        if not os.path.exists(path):
            return out_lines
        tail_fd = open(path, 'r')
        tail_fd.seek(0, os.SEEK_END)
        size = tail_fd.tell()
        pos = tail_fd.tell()
        step_size = 100
        # locate last X lines
        while pos > 0 and len(out_lines) < lines:
            offset = min(lines * step_size, size)
            logger.debug("seek to offset %d from end of %s" % (offset, path))
            tail_fd.seek(-offset, os.SEEK_END)
            pos = tail_fd.tell()
            out_lines = tail_fd.readlines()
            step_size *= 2
            #logger.debug("reading %d lines from %s" % (lines, path))
        tail_fd.close()
    except Exception as exc:
        logger.error("reading %d lines from %s: %s" % (lines, path, exc))
    return out_lines[-lines:]


def get_file_size(path, logger):
    """Wrapper to handle getsize of path"""
    logger.debug('getsize on file: %s' % path)
    try:
        return os.path.getsize(path)
    except Exception as err:
        logger.error('could not get size for %s: %s' % (path, err))
        result = -1


def delete_file(path, logger, allow_broken_symlink=False, allow_missing=False):
    """Wrapper to handle deletion of path. The optional allow_broken_symlink is
    used to accept delete even if path is a broken symlink.
    """
    logger.debug('deleting file: %s' % path)
    if os.path.exists(path) or allow_broken_symlink and os.path.islink(path):
        try:
            os.remove(path)
            result = True
        except Exception as err:
            logger.error('could not delete %s %s' % (path, err))
            result = False
    elif allow_missing:
        result = True
    else:
        logger.info('delete_file: %s does not exist.' % path)
        result = False

    return result


def make_symlink(dest, src, logger, force=False):
    """Wrapper to make src a symlink to dest path"""

    # NOTE: we use islink instead of exists here to handle broken symlinks
    if os.path.islink(src) and force and delete_symlink(src, logger):
        logger.debug('deleted existing symlink: %s' % (src))

    try:
        logger.debug('creating symlink: %s %s' % (dest, src))
        os.symlink(dest, src)
    except Exception as err:
        logger.error('Could not create symlink %s' % err)
        return False
    return True


def delete_symlink(path, logger, allow_broken_symlink=True,
                   allow_missing=False):
    """Wrapper to handle deletion of symlinks"""
    logger.debug('deleting symlinks: %s' % path)
    return delete_file(path, logger, allow_broken_symlink, allow_missing)


def filter_pickled_list(path, changes):
    """Filter pickled list on disk with provided changes where changes is a
    dictionary mapping existing list entries and the value to replace it with.
    """

    saved_list = load(path)
    saved_list = [changes.get(entry, entry) for entry in saved_list]
    dump(saved_list, path)
    return saved_list


def filter_pickled_dict(path, changes):
    """Filter pickled dictionary on disk with provided changes where changes
    is a dictionary mapping existing dictionary values to a value to replace
    it with.
    """

    saved_dict = load(path)
    for (key, val) in saved_dict.items():
        if val in changes.keys():
            saved_dict[key] = changes[val]
    dump(saved_dict, path)
    return saved_dict


def update_pickled_dict(path, changes):
    """Update pickled dictionary on disk with provided changes"""

    saved_dict = load(path)
    saved_dict.update(changes)
    dump(saved_dict, path)
    return saved_dict


def unpickle_and_change_status(path, newstatus, logger):
    """change status in the MiG server mRSL file"""

    changes = {}
    changes['STATUS'] = newstatus
    changes[newstatus + '_TIMESTAMP'] = time.gmtime()
    try:
        job_dict = update_pickled_dict(path, changes)
        logger.info('job status changed to %s: %s' % (newstatus,
                                                      path))
        return job_dict
    except Exception as err:
        logger.error('could not change job status to %s: %s %s'
                     % (newstatus, path, err))
        return False


def unpickle(path, logger, allow_missing=False):
    """Unpack pickled object in path"""
    try:
        data_object = load(path)
        logger.debug('%s was unpickled successfully' % path)
        return data_object
    except Exception as err:
        # NOTE: check that it was in fact due to file does not exist error
        if not allow_missing or getattr(err, 'errno', None) != errno.ENOENT:
            logger.error('%s could not be opened/unpickled! %s'
                         % (path, err))
        return False


def pickle(data_object, path, logger):
    """Pack data_object as pickled object in path"""
    try:
        dump(data_object, path)
        logger.debug('pickle success: %s' % path)
        return True
    except Exception as err:
        logger.error('could not pickle: %s %s' % (path, err))
        return False


def load_json(path, logger, allow_missing=False, convert_utf8=True):
    """Unpack json object in path"""
    try:
        data_object = load(path, serializer='json')
        logger.debug('%s was loaded successfully' % path)
        if convert_utf8:
            data_object = force_utf8_rec(data_object)
        return data_object
    except Exception as err:
        # NOTE: check that it was in fact due to file does not exist error
        if not allow_missing or getattr(err, 'errno', None) != errno.ENOENT:
            logger.error('%s could not be opened/loaded! %s'
                         % (path, err))
        return False


def send_message_to_grid_script(message, logger, configuration):
    """Write an instruction to the grid_script name pipe input"""
    try:
        filehandle = open(configuration.grid_stdin, 'a')
        fcntl.flock(filehandle.fileno(), fcntl.LOCK_EX)
        filehandle.write(message)
        filehandle.close()
        return True
    except Exception as err:
        print('could not get exclusive access or write to grid_stdin!')
        logger.error('could not write "%s" to grid_stdin: %s' %
                     (message, err))
        return False


def send_message_to_grid_notify(message, logger, configuration):
    """Write message to notify home"""
    try:
        (filedescriptor, filepath) = make_temp_file(
            suffix='.%s' % time.time(),
            prefix='',
            dir=configuration.notify_home)
        filehandle = os.fdopen(filedescriptor, 'a')
        filehandle.write(message)
        filehandle.close()
        return True
    except Exception as err:
        logger.error("Failed to send_message_to_grid_notify: %s" % err)
        try:
            filehandle.close()
        except Exception as err:
            pass
        try:
            os.remove(filepath)
        except Exception as err:
            pass
        return False


def touch(filepath, configuration, timestamp=None):
    """Create or update timestamp for filepath"""
    try:
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            filehandle = open(filepath, 'r+w')
            i = filehandle.read(1)
            filehandle.seek(0, 0)
            filehandle.write(i)
            filehandle.close()
        else:
            open(filepath, 'w').close()
        if timestamp != None:
            # set timestamp to supplied value
            os.utime(filepath, (timestamp, timestamp))
    except Exception as err:
        configuration.logger.error("could not touch file: '%s'" % filepath
                                   + ": %s" % err)
        return False

    return True


def remove_rec(dir_path, configuration):
    """
    Remove the given dir_path, and all subdirectories, recursively.
    This function sets the permissions on files and subdirectories
    before using shutil.rmtree, which is necessary when removing
    VGrid component dot directories.

    Returns Boolean to indicate success, writes messages to log.
    """
    _logger = configuration.logger
    if slow_walk:
        _logger.warning("no optimized walk available - using old os.walk")
    try:
        if not os.path.isdir(dir_path):
            raise Exception("Directory %s does not exist" % dir_path)

        os.chmod(dir_path, 0o777)

        # extend permissions top-down
        for root, dirs, files in walk(dir_path, topdown=True):
            for name in files:
                os.chmod(os.path.join(root, name), 0o777)
            for name in dirs:
                os.chmod(os.path.join(root, name), 0o777)
        shutil.rmtree(dir_path)

    except Exception as err:
        _logger.error("Could not remove_rec %s: %s" % (dir_path, err))
        return False

    return True


def remove_dir(dir_path, configuration):
    """
    Remove the given dir_path, if it's empty

    Returns Boolean to indicate success, writes messages to log.
    """
    try:
        os.rmdir(dir_path)
    except Exception as err:
        configuration.logger.error("Could not remove_dir %s: %s" %
                                   (dir_path, err))
        return False

    return True


def move(src, dst):
    """Recursively move a file or directory from src to dst. This version works
    even in cases rename does not - e.g. for src and dst on different devices.
    """
    return shutil.move(src, dst)


def makedirs_rec(dir_path, configuration, accept_existing=True):
    """Make sure dir_path is created if it doesn't already exist. The optional
    accept_existing argument can be used to turn off the default behaviour of
    ignoring if dir_path already exists.
    """
    _logger = configuration.logger
    try:
        if os.path.exists(dir_path) and not os.path.isdir(dir_path):
            _logger.error("Non-directory in the way: %s" % dir_path)
            return False
        os.makedirs(dir_path)
    except OSError as err:
        if not accept_existing or err.errno != errno.EEXIST:
            _logger.error("Could not makedirs_rec %s: %s" % (dir_path, err))
            return False
    return True


def _move_helper(src, dst, configuration, recursive):
    """Move a file/dir to dst where dst must be a new file/dir path and the
    parent dir is created if necessary. The recursive flag is used to enable
    recursion.
    """
    dst_dir = os.path.dirname(dst)
    makedirs_rec(dst_dir, configuration)
    try:
        # Always use the same recursive move
        shutil.move(src, dst)
    except Exception as exc:
        return (False, "move failed: %s" % exc)
    return (True, "")


def move_file(src, dst, configuration):
    """Move a file from src to dst where dst must be a new file path and
    the parent dir is created if necessary.
    """
    return _move_helper(src, dst, configuration, False)


def move_rec(src, dst, configuration):
    """Move a dir recursively to dst where dst must be a new dir path and the
    parent dir is created if necessary.
    """
    return _move_helper(src, dst, configuration, True)


def _copy_helper(src, dst, configuration, recursive):
    """Copy a file or directory from src to dst where dst must be a new
    file/dir path and the parent dir is created if necessary. The recursive
    flag enables recursive copy.
    """
    dst_dir = os.path.dirname(dst)
    makedirs_rec(dst_dir, configuration)
    try:
        if recursive:
            shutil.copytree(src, dst)
        else:
            shutil.copy(src, dst)
    except Exception as exc:
        return (False, "copy failed: %s" % exc)
    return (True, "")


def copy(src, dst):
    """Copy a file from src to dst where dst may be a directory"""
    return shutil.copy(src, dst)


def copy_file(src, dst, configuration):
    """Copy a file from src to dst where dst must be a new file path and
    the parent dir is created if necessary.
    """
    return _copy_helper(src, dst, configuration, False)


def copy_rec(src, dst, configuration):
    """Copy a dir recursively to dst where dst must be a new dir path and the
    parent dir is created if necessary.
    """
    return _copy_helper(src, dst, configuration, True)


def write_zipfile(zip_path, paths, archive_base=''):
    """Write each of the files/dirs in paths to a zip file with zip_path.
    Given a non-empty archive_base string, that string will be used as the
    directory path of the archived files.
    """
    try:
        # Force compression
        zip_file = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        # Directory write is not supported - add each file manually
        for script in paths:

            # Replace real directory path with archive_base if specified

            if archive_base:
                archive_path = '%s/%s' % (archive_base,
                                          os.path.basename(script))
            else:
                archive_path = script
            zip_file.write(script, archive_path)
        zip_file.close()
        return (True, '')
    except Exception as err:
        return (False, err)


def strip_dir(path):
    """Strip directory part of path for all known path formats. We can
    not simply use os.path.basename() as it doesn't work if client
    supplies, say, an absolute windows path.
    """

    if path[:4].find(':\\') >= 0:

        # Windows absolute path - name is just right of rightmost backslash

        index = path.rfind('\\')
        name = path[index + 1:]
    else:
        name = os.path.basename(path)
    return name


def check_empty_dir(path):
    """Check if path is an empty directory"""
    if not os.path.isdir(path):
        return False
    return not os.listdir(path)


def _check_access(path, mode, parent_dir, follow_symlink):
    """Internal helper to check for mode access on path. If parent_dir is set
    the check is applied to the directory part of path. With follow_symlink set
    any symlinks in path are first expanded so that the corresponding parent is
    checked if parent_dir is requested.  
    """
    if follow_symlink:
        path = os.path.realpath(path)
    if parent_dir:
        path = os.path.dirname(path.rstrip(os.sep))
    return os.access(path, mode)


def check_read_access(path, parent_dir=False, follow_symlink=True):
    """Check if path is readable or if the optional parent_dir is set check if
    the directory part of path is readable. The optional follow_symlink
    argument decides if any symlinks in path are expanded before this check
    and it is on by default.
    """
    return _check_access(path, os.O_RDONLY, parent_dir, follow_symlink)


def check_write_access(path, parent_dir=False, follow_symlink=True):
    """Check if path is writable or if the optional parent_dir is set check if
    the directory part of path is writable, which is particularly useful to
    check that a new file can be created. The optional follow_symlink argument
    decides if any symlinks in path are expanded before this check and it is
    on by default.
    """
    # IMPORTANT: we need to use RDWR rather than WRONLY here.
    return _check_access(path, os.O_RDWR, parent_dir, follow_symlink)


def make_temp_file(suffix='', prefix='tmp', dir=None, text=False):
    """Expose tempfile.mkstemp functionality"""
    return tempfile.mkstemp(suffix, prefix, dir, text)


def make_temp_dir(suffix='', prefix='tmp', dir=None):
    """Expose tempfile.mkdtemp functionality"""
    return tempfile.mkdtemp(suffix, prefix, dir)


def __checksum_file(path, hash_algo, chunk_size=default_chunk_size,
                    max_chunks=default_max_chunks):
    """Simple block hashing for checksumming of files inspired by  
    http://stackoverflow.com/questions/16799088/file-checksums-in-python
    Read at most max_chunks blocks of chunk_size (to avoid DoS) and checksum
    using hash_algo (md5, sha1, sha256, sha512, ...).
    Any non-positive max_chunks value removes the size limit.  
    If max_chunks is positive the checksum will match that of the Xsum
    command for files smaller than max_chunks * chunk_size and for bigger
    files a partial checksum of the first chunk_size * max_chunks bytes will
    be returned.
    """
    checksum = __valid_hash_algos.get(hash_algo, __valid_hash_algos['md5'])()
    chunks_read = 0
    msg = ''
    try:
        file_fd = open(path, 'rb')
        while max_chunks < 1 or chunks_read < max_chunks:
            block = file_fd.read(chunk_size)
            if not block:
                break
            checksum.update(block)
            chunks_read += 1
        if file_fd.read(1):
            msg = ' (of first %d bytes)' % (chunk_size * max_chunks)
        return "%s%s" % (checksum.hexdigest(), msg)
    except Exception as exc:
        return "checksum failed: %s" % exc


def md5sum_file(path, chunk_size=default_chunk_size,
                max_chunks=default_max_chunks):
    """Simple md5 hashing for checksumming of files"""
    return __checksum_file(path, "md5", chunk_size, max_chunks)


def sha1sum_file(path, chunk_size=default_chunk_size,
                 max_chunks=default_max_chunks):
    """Simple sha1 hashing for checksumming of files"""
    return __checksum_file(path, "sha1", chunk_size, max_chunks)


def sha256sum_file(path, chunk_size=default_chunk_size,
                   max_chunks=default_max_chunks):
    """Simple sha256 hashing for checksumming of files"""
    return __checksum_file(path, "sha256", chunk_size, max_chunks)


def sha512sum_file(path, chunk_size=default_chunk_size,
                   max_chunks=default_max_chunks):
    """Simple sha512 hashing for checksumming of files"""
    return __checksum_file(path, "sha512", chunk_size, max_chunks)


def acquire_file_lock(lock_path, exclusive=True, blocking=True):
    """Uses fcntl to acquire the lock in lock_path in exclusive and blocking
    mode unless requested otherwise.
    Should be used on separate lock files and not on the file that is
    meant to be synchronized itself.
    Returns the lock handle used to unlock the file again. We recommend
    explicitly calling release_file_lock when done, but technically it should
    be enough to delete all references to the handle and let garbage
    collection automatically unlock and close it.
    Returns None if blocking is disabled and the lock could not be readily
    acquired.
    """
    if exclusive:
        lock_mode = fcntl.LOCK_EX
    else:
        lock_mode = fcntl.LOCK_SH
    if not blocking:
        lock_mode |= fcntl.LOCK_NB
    # NOTE: Some system+python combinations require 'w+' here
    #       to allow both SH and EX locking
    lock_handle = open(lock_path, "w+")
    try:
        fcntl.flock(lock_handle.fileno(), lock_mode)
    except IOError as ioe:
        # Clean up
        try:
            lock_handle.close()
        except:
            pass
        # If non-blocking flock gave up an IOError will be raised and the
        # exception will have an errno attribute set to EACCES or EAGAIN.
        # All other exceptions should be re-raised for caller to handle.
        if not blocking and ioe.errno in (errno.EACCES, errno.EAGAIN):
            lock_handle = None
        else:
            raise ioe

    return lock_handle


# TODO: use this function for modify X calls with limited blocking
def responsive_acquire_lock(lock_path, exclusive, max_attempts=10,
                            retry_delay=2):
    """A simple helper to retry locking lock_path in non-blocking way
    until it either succeeds or the maximum allowed number of attempts failed.
    The exclusive arg is used to toggle between exclusive or shared locking.
    The optional max_attempts and retry_delay args can be used to tune the
    locking retries.
    """
    lock_handle = None
    for i in xrange(max_attempts):
        lock_handle = acquire_file_lock(lock_path, exclusive, False)
        if lock_handle is None:
            time.sleep(retry_delay)
        else:
            break
    if lock_handle is None:
        raise Exception("gave up locking %s for update" % lock_path)
    return lock_handle


def release_file_lock(lock_handle, close=True):
    """Uses fcntl to release the lock held in lock_handle. We generally lock a
    separate lock file when we wish to modify a shared file in line with the
    acquire_file_lock notes, so this release helper by default includes closing
    of the lock_handle file object.
    """
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    if close:
        try:
            lock_handle.close()
        except:
            pass


def check_readable(configuration, path):
    """Check and return boolean to indicate if path is a non-empty string and
    a readable location.
    """
    _logger = configuration.logger
    if not path:
        return False
    elif not check_read_access(path):
        return False
    return True


def check_writable(configuration, path):
    """Check and return boolean to indicate if path is a non-empty string and
    a writable location.
    """
    if not path:
        return False
    elif not check_write_access(path):
        return False
    return True


def check_readwritable(configuration, path):
    """Check and return boolean to indicate if path set and read+writable"""
    return check_readable(configuration, path) and \
        check_writable(configuration, path)


def check_readonly(configuration, path):
    """Check and return boolean to indicate if path is set and readonly"""
    return check_readable(configuration, path) and not \
        check_writable(configuration, path)


def untrusted_store_res_symlink(configuration, path):
    """Check and return boolean to indicate if path is a symlink inside a
    mounted storage resource folder. We cannot trust any such symlinks to be
    safe as they may be fully user controlled and thus bypass all our symlink
    restrictions. Thus we only allow symlinks there if they point to somewhere
    inside the same storage resource folder.
    """
    # If path doesn't expand to a different location we are generally safe
    real_path = os.path.realpath(path)
    if path == real_path:
        return False
    real_res_home = os.path.realpath(configuration.resource_home)
    # Lookup actual resource home dir and make sure path is somewhere inside
    # NOTE: we traverse from root to avoid illegal access to other resources
    path_parts = path.split(os.sep)
    parent = os.sep
    found_res_base = False
    for sub in path_parts:
        parent = os.path.join(parent, sub)
        real_parent = os.path.realpath(parent)
        if real_parent.startswith(real_res_home + os.sep):
            res_base = parent
            real_res_base = os.path.realpath(res_base)
            found_res_base = True
            break
    if not found_res_base:
        return False
    # configuration.logger.debug("check real_path %s inside %s" % \
    #                            (real_path, res_base))
    return not real_path.startswith(real_res_base)


def user_chroot_exceptions(configuration):
    """Lookup a list of chroot exceptions for use in chrooting user
    operations to the allowed subset of the file system. The allowed locations
    include the ones that valid symlinks from user home may point into.
    """
    # Allow access to vgrid linked dirs and optionally write restricted ones
    chroot_exceptions = [os.path.abspath(configuration.vgrid_private_base),
                         os.path.abspath(configuration.vgrid_public_base),
                         os.path.abspath(configuration.vgrid_files_home)]
    readonly_dir = configuration.vgrid_files_readonly
    if check_readonly(configuration, readonly_dir):
        chroot_exceptions.append(os.path.abspath(readonly_dir))
    writable_dir = configuration.vgrid_files_writable
    if check_writable(configuration, writable_dir):
        chroot_exceptions.append(os.path.abspath(writable_dir))
    # Allow access to mounted storage resource dirs and optional seafile mount
    chroot_exceptions.append(os.path.abspath(configuration.resource_home))
    if configuration.site_enable_seafile and configuration.seafile_mount:
        chroot_exceptions.append(os.path.abspath(configuration.seafile_mount))
    # Allow access to mig_system_storage used for merging multiple storage backends
    chroot_exceptions.append(os.path.abspath(configuration.mig_system_storage))
    return chroot_exceptions
