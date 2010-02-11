#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fileio - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

import time
import os
import shutil
import fcntl

from shared.serial import dump, load

def write_file(content, filename, logger):
    logger.debug('writing file: %s' % filename)

    # create dir if it does not exists

    (head, _) = os.path.split(filename)
    if not os.path.isdir(head):
        try:
            logger.debug('making directory %s' % head)
            os.mkdir(head)
        except Exception, err:
            logger.error('could not create dir %s' % err)
    try:
        filehandle = open(filename, 'w')
        filehandle.write(content)
        filehandle.close()
        logger.debug('file written: %s' % filename)
        return True
    except Exception, err:
        logger.error('could not write %s %s' % (filename, err))
        return False


def delete_file(filename, logger):
    logger.debug('deleting file: %s' % filename)
    if os.path.exists(filename):
        try:
            os.remove(filename)
            result = True
        except Exception, err:
            logger.error('could not delete %s %s' % (filename, err))
            result = False
    else:
        logger.info('%s does not exist.' % filename)
        result = False

    return result


def make_symlink(dest, src, logger):
    try:
        logger.debug('creating symlink: %s %s' % (dest, src))
        os.symlink(dest, src)
    except Exception, err:
        logger.error('Could not create symlink %s' % err)
        return False
    return True


def filter_pickled_list(filename, changes):
    """Filter pickled list on disk with provided changes where changes is a dictionary
    mapping existing list entries and the value to replace it with.
    """

    saved_list = load(filename)
    saved_list = [changes.get(entry, entry) for entry in saved_list]
    dump(saved_list, filename)
    return saved_list


def filter_pickled_dict(filename, changes):
    """Filter pickled dictionary on disk with provided changes where changes is a
    dictionary mapping existing dictionary values to a value to replace it with"""

    saved_dict = load(filename)
    for (key, val) in saved_dict.items():
        if val in changes.keys():
            saved_dict[key] = changes[val]
    dump(saved_dict, filename)
    return saved_dict


def update_pickled_dict(filename, changes):
    """Update pickled dictionary on disk with provided changes"""

    saved_dict = load(filename)
    saved_dict.update(changes)
    dump(saved_dict, filename)
    return saved_dict


def unpickle_and_change_status(filename, newstatus, logger):
    """change status in the MiG server mRSL file"""

    changes = {}
    changes['STATUS'] = newstatus
    changes[newstatus + '_TIMESTAMP'] = time.gmtime()
    try:
        job_dict = update_pickled_dict(filename, changes)
        logger.info('job status changed to %s: %s' % (newstatus,
                    filename))
        return job_dict
    except Exception, err:
        logger.error('could not change job status to %s: %s %s'
                      % (newstatus, filename, err))
        return False


def unpickle(filename, logger):
    try:
        job_dict = load(filename)
        logger.debug('%s was unpickled successfully' % filename)
        return job_dict
    except Exception, err:
        logger.error('%s could not be opened/unpickled! %s'
                      % (filename, err))
        return False


def pickle(job_dict, filename, logger):
    try:
        dump(job_dict, filename)
        logger.debug('pickle success: %s' % filename)
        return True
    except Exception, err:
        logger.error('could not pickle: %s %s' % (filename, err))
        return False


def send_message_to_grid_script(message, logger, configuration):
    try:
        filehandle = open(configuration.grid_stdin, 'a')
        fcntl.flock(filehandle.fileno(), fcntl.LOCK_EX)
        filehandle.write(message)
        filehandle.close()
        return True
    except Exception, err:
        print 'could not get exclusive access or write to grid_stdin!'
        logger.error('could not get exclusive access or write to grid_stdin: %s %s'
                      % (message, err))
        return False


def touch(filepath, timestamp=None):
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
    except Exception, err:

        print "could not touch file: '%s', Error: %s" % (filepath, err)
        return False

def disk_stats(top_dir, follow_links=False):
    """Count the files and directories under top_dir and return a dictionary
    with file count, dir count and used space.
    If follow_links is set links will be followed.
    """
    # TODO: consider caching
    stats = {'files': 0, 'directories': 0, 'bytes': 0}
    for (root, dirs, files) in os.walk(top_dir):
        stats['files'] += len(files)
        stats['directories'] += len(dirs)
        for name in files + dirs:
            path = os.path.join(root, name)
            if follow_links or not os.path.islink(path):
                stats['bytes'] += os.path.getsize(path)
    stats['kilobytes'] = stats['bytes'] / 1024.0
    stats['megabytes'] = stats['kilobytes'] / 1024.0
    stats['gigabytes'] = stats['megabytes'] / 1024.0
    stats['terabytes'] = stats['gigabytes'] / 1024.0
    return stats
