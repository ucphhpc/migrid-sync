#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# iobase - wrapper to wrap local and dist io in one
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""A common entry point to all IO"""

from __future__ import print_function
from __future__ import absolute_import

import os
import time
import new
import glob as realglob
import shutil as realshutil
import stat as realstat
import zipfile as realzipfile

from mig.shared import localfile
from mig.shared import localos
from mig.shared import localpickle
from mig.shared import distfile
from mig.shared import distos
from mig.shared import distpickle

# export os / os.path functions and variables

sep = os.sep

# Create dummy path submodule to avoid tampering with os.path

path = new.module('path')

# some string-only path operations

path.basename = os.path.basename
path.dirname = os.path.dirname
path.join = os.path.join
path.normpath = os.path.normpath
path.split = os.path.split

LOCK_SH = distfile.LOCK_SH
LOCK_EX = distfile.LOCK_EX
USER_AGENT = distfile.USER_AGENT
DISTRIBUTED = 'distributed'
LOCAL = 'local'

# TODO: find best block size in practice

OPTIMAL_BLOCK_SIZE = 4096

# TODO: separate glob (and shutils) sub-modules?


def glob(pattern, location=DISTRIBUTED):
    """Distributed file glob"""

    if DISTRIBUTED == location:

        # Overload real glob with dist os ops

        realglob.os = distos
        realglob.curdir = './'
        realglob.os.curdir = realglob.curdir
        realglob.os.error = os.error
    elif LOCAL == location:
        pass
    else:
        raise Exception('Illegal location in glob: %s' % location)
    return realglob.glob(pattern)


def copytree(src, dst, location=DISTRIBUTED):
    """Distributed shutil.copytree"""

    if DISTRIBUTED == location:

        # Overload real shutil with dist file/os ops

        realshutil.os = distos
        realshutil.open = distfile.DistFile
    elif LOCAL == location:
        pass
    else:
        raise Exception('Illegal location in copytree: %s' % location)

    return realshutil.copytree(src, dst)


def force_close(filehandle):
    """Close the filehandle without caring about errors. This
    is very common operation with dist server where files will
    remain locked unless they are closed correctly.
    """

    try:
        filehandle.unlock()
        filehandle.close()
    except:
        pass


def abspath(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in abspath: %s' % location)
    return os_lib.path.abspath(path)


def chmod(path, mode, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in chmod: %s' % location)
    return os_lib.chmod(path, mode)


def exists(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in exists: %s' % location)
    return os_lib.path.exists(path)


def isdir(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in isdir: %s' % location)
    return os_lib.path.isdir(path)


def isfile(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in isfile: %s' % location)
    return os_lib.path.isfile(path)


def islink(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in islink: %s' % location)
    return os_lib.path.islink(path)


def getatime(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in getatime: %s' % location)
    return os_lib.path.getatime(path)


def getctime(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in getctime: %s' % location)
    return os_lib.path.getctime(path)


def getmtime(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in getmtime: %s' % location)
    return os_lib.path.getmtime(path)


def getsize(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in getsize: %s' % location)
    return os_lib.path.getsize(path)


def lstat(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in stat: %s' % location)
    return os_lib.lstat(path)


def mkdir(path, mode=0o775, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in mkdir: %s' % location)
    return os_lib.mkdir(path, mode)


def makedirs(path, mode=0o775, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in makedirs: %s' % location)
    return os_lib.makedirs(path, mode)


def rmdir(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in rmdir: %s' % location)
    return os_lib.rmdir(path)


def listdir(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in listdir: %s' % location)
    return os_lib.listdir(path)


def realpath(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in realpath: %s' % location)
    return os_lib.path.realpath(path)


def remove(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in remove: %s' % location)
    return os_lib.remove(path)


def removedirs(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in removedirs: %s' % location)
    return os_lib.removedirs(path)


def rename(src, dst, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in rename: %s' % location)
    return os_lib.rename(src, dst)


def stat(path, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in stat: %s' % location)
    return os_lib.stat(path)


def symlink(src, dst, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in symlink: %s' % location)
    return os_lib.symlink(src, dst)


def walk(path, topdown=True, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in walk: %s' % location)
    return os_lib.walk(path, topdown)


def open_file(
    filename,
    mode,
    bufsize=0,
    location=DISTRIBUTED,
):

    if DISTRIBUTED == location:
        return distfile.DistFile(filename, mode, bufsize)
    elif LOCAL == location:
        return localfile.LocalFile(filename, mode, bufsize)
    else:
        raise Exception('Illegal location in open_file: %s' % location)


def __read_kind(
    filename,
    logger=None,
    location=DISTRIBUTED,
    read_function='read',
):

    if DISTRIBUTED == location:
        file_lib = distfile
        file_opener = distfile.DistFile
    elif LOCAL == location:
        file_lib = localfile
        file_opener = localfile.LocalFile
    else:
        raise Exception('Illegal location in open_file: %s' % location)
    if logger:
        logger.debug('reading %s file: %s' % (location, filename))
    filehandle = None
    try:
        filehandle = open_file(filename, 'r', 0, location)
        filehandle.lock(file_lib.LOCK_SH)
        contents = eval('filehandle.%s()' % read_function)
        filehandle.unlock()
        filehandle.close()
        if logger:
            logger.debug('file read: %s' % filename)
        return contents
    except Exception as err:
        if logger:
            logger.error('could not read %s %s' % (filename, err))
        force_close(filehandle)
        raise err


def read_file(filename, logger=None, location=DISTRIBUTED):
    return __read_kind(filename, logger, location, read_function='read')


def read_lines(filename, logger=None, location=DISTRIBUTED):
    return __read_kind(filename, logger, location,
                       read_function='readlines')


def __write_kind(
    content,
    filename,
    logger=None,
    location=DISTRIBUTED,
    write_function='write',
):

    if DISTRIBUTED == location:
        os_lib = distos
        file_lib = distfile
        file_opener = distfile.DistFile
    elif LOCAL == location:
        os_lib = localos
        file_lib = localfile
        file_opener = localfile.LocalFile
    else:
        raise Exception('Illegal location in open_file: %s' % location)
    if logger:
        logger.debug('writing %s file: %s' % (location, filename))

    filehandle = None
    try:
        filehandle = open_file(filename, 'w', 0, location)
        filehandle.lock(file_lib.LOCK_EX)
        eval('filehandle.%s(content)' % write_function)
        filehandle.flush()
        filehandle.unlock()
        filehandle.close()
        if logger:
            logger.debug('file written: %s' % filename)
        return True
    except Exception as err:
        if logger:
            logger.error('could not write %s %s' % (filename, err))
        force_close(filehandle)
        raise err


def write_file(
    content,
    filename,
    logger=None,
    location=DISTRIBUTED,
):

    return __write_kind(content, filename, logger, location,
                        write_function='write')


def write_lines(
    content,
    filename,
    logger=None,
    location=DISTRIBUTED,
):

    return __write_kind(content, filename, logger, location,
                        write_function='writelines')


def copy_file(src, dst, location=DISTRIBUTED):

    # TODO: extend distos (beyond standard functions) to include copy?
    # it would be quite simple to copy/paste from rename and use
    # shutils to do the copy server-side

    if DISTRIBUTED == location:
        file_lib = distfile
        file_opener = distfile.DistFile
    elif LOCAL == location:
        file_lib = localfile
        file_opener = localfile.LocalFile
    else:
        raise Exception('Illegal location in copy_file: %s' % location)
    try:
        src_fd = file_opener(src, 'r')
        src_fd.lock(file_lib.LOCK_SH)
        dst_fd = file_opener(dst, 'w')
        dst_fd.lock(file_lib.LOCK_EX)
        while True:
            data = src_fd.read(OPTIMAL_BLOCK_SIZE)
            if not data:
                break
            dst_fd.write(data)
        src_fd.unlock()
        src_fd.close()
        dst_fd.flush()
        dst_fd.unlock()
        dst_fd.close()
    except Exception as err:
        force_close(src_fd)
        force_close(dst_fd)
        raise err


def delete_file(filename, logger=None, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in delete_file: %s'
                        % location)
    if logger:
        logger.debug('deleting file: %s' % filename)
    if os_lib.path.exists(filename):
        try:
            os_lib.remove(filename)
            result = True
        except Exception as err:
            if logger:
                logger.error('could not delete %s %s %s' % (location,
                                                            filename, err))
            result = False
    else:
        if logger:
            logger.info('%s does not exist.' % filename)
        result = False

    return result


def make_symlink(
    src,
    dst,
    logger=None,
    location=DISTRIBUTED,
):

    if DISTRIBUTED == location:
        os_lib = distos
    elif LOCAL == location:
        os_lib = localos
    else:
        raise Exception('Illegal location in make_symlink: %s'
                        % location)
    try:
        if logger:
            logger.debug('creating %s symlink: %s %s' % (location, dst,
                                                         src))
        os_lib.symlink(src, dst)
        return True
    except Exception as err:
        if logger:
            logger.error('make_symlink failed: %s' % err)
        return False


def unpickle_and_change_status(
    filename,
    newstatus,
    logger=None,
    location=DISTRIBUTED,
):
    """change status in the MiG server mRSL file"""

    job_dict = unpickle(filename, logger)
    try:
        job_dict['STATUS'] = newstatus
        job_dict[newstatus + '_TIMESTAMP'] = time.gmtime()
    except Exception as err:
        if logger:
            logger.error('could not change job %s status to %s: %s %s'
                         % (job_dict, newstatus, filename, err))
        return False
    if pickle(job_dict, filename, logger):
        if logger:
            logger.info('job status changed to %s: %s' % (newstatus,
                                                          filename))
        return job_dict
    else:
        if logger:
            logger.error('could not re-pickle job with new status %s: %s'
                         % (newstatus, filename))
        return False


def unpickle(filename, logger=None, location=DISTRIBUTED):
    if DISTRIBUTED == location:
        pickle_lib = distpickle
    elif LOCAL == location:
        pickle_lib = localpickle
    else:
        raise Exception('Illegal location in unpickle: %s' % location)
    try:
        obj = pickle_lib.load(filename)
        if logger:
            logger.debug('%s was unpickled successfully' % filename)
        return obj
    except Exception as err:
        if logger:
            logger.error('%s %s could not be opened/unpickled! %s'
                         % (location, filename, err))
        return None


def pickle(
    obj,
    filename,
    logger=None,
    location=DISTRIBUTED,
):

    if DISTRIBUTED == location:
        pickle_lib = distpickle
    elif LOCAL == location:
        pickle_lib = localpickle
    else:
        raise Exception('Illegal location in pickle: %s' % location)
    try:
        pickle_lib.dump(obj, filename, 0)
        if logger:
            logger.debug('pickle success: %s' % filename)
        return True
    except Exception as err:
        if logger:
            logger.error('could not pickle %s %s %s' % (location,
                                                        filename, err))
        return False


def write_zipfile(
    zip_path,
    paths,
    archive_base='',
    location=DISTRIBUTED,
):
    """Write each of the files/dirs in paths to a zip file with zip_path.
    Given a non-empty archive_base string, that string will be used as the
    directory path of the archived files.
    """

    if DISTRIBUTED == location:
        os_lib = distos
        file_lib = distfile
        file_opener = distfile.DistFile
    elif LOCAL == location:
        os_lib = localos
        file_lib = localfile
        file_opener = localfile.LocalFile
    else:
        raise Exception('Illegal location in write_zipfile: %s'
                        % location)
    zip_fd = None
    try:

        # Use zipfile on file object from IO to hide actual file location

        zip_fd = file_opener(zip_path, 'w')
        zip_fd.lock(LOCK_EX)
        # Force compression
        zip_file = realzipfile.ZipFile(zip_fd, 'w', realzipfile.ZIP_DEFLATED)

        # Directory write is not supported - add each file manually

        for script in paths:

            # Replace real directory path with archive_base if specified

            if archive_base:
                archive_path = '%s/%s' % (archive_base,
                                          os_lib.path.basename(script))
            else:
                archive_path = script

            # Files are not necessarily local so we must read and write

            zip_file.writestr(archive_path, read_file(script, None,
                                                      location))
        zip_file.close()
        zip_fd.flush()
        zip_fd.unlock()
        zip_fd.close()
    except Exception as err:
        force_close(zip_fd)
        raise err


def send_message_to_grid_script(message, logger, configuration):
    try:
        pipe = localfile.LocalFile(configuration.grid_stdin, 'a')
        pipe.lock(localfile.LOCK_EX)
        pipe.write(message)
        pipe.flush()
        pipe.unlock
        pipe.close()
        logger.info('%s written to grid_stdin' % message)
        return True
    except Exception as err:
        print('could not get exclusive access or write to grid_stdin!')
        logger.error('could not get exclusive access or write to grid_stdin: %s %s'
                     % (message, err))
        force_close(pipe)
        return False


# now override path functions (must be after functions are declared)

path.isfile = isfile
path.isdir = isdir
path.islink = islink
path.exists = exists
path.getsize = getsize
path.getatime = getatime
path.getctime = getctime
path.getmtime = getmtime
path.abspath = abspath
path.realpath = realpath
