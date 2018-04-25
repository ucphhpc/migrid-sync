#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# base - [insert a few words of module description on this line]
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

# Script version (automagically updated by cvs)

"""This module contains various wrapper functions for distributed
server file system operations (think the python 'os' module). In that
way the underlying distribution of the server FS can be separated
from the normal server operation.
"""

__version__ = '$Revision: 2084 $'
__revision__ = __version__

# $Id: base.py 2084 2007-09-11 08:39:37Z jones $

import sys
import os
import stat as realstat

# TODO: change to import shared.distos.path as distpath

import path as distpath

# load distbase from parent directory

module_dir = os.path.dirname(__file__)
parent_dir = os.path.realpath('%s/../' % module_dir)
sys.path.append(parent_dir)
import shared.distbase as distbase
from shared.distbase import HTTPS_CERT_PORT, BASE_HOME, get_leader

# ############################
# Internal helper classes   #
# ############################


class dummystat(object):

    """A simple dummy class used to emulate os.stat() objects. 90% of
    the class code is used to write-protect the attributes like the
    real stat does.
    """

    attributes = [
        'st_mode',
        'st_ino',
        'st_dev',
        'st_nlink',
        'st_uid',
        'st_gid',
        'st_size',
        'st_atime',
        'st_mtime',
        'st_ctime',
        ]

    def __init__(self, stat_info):
        self.__stat_info = stat_info
        self.__fields = {}
        for (name, value) in zip(self.attributes, stat_info):
            self.__fields[name] = value

    def __getvar(self, name):
        return self.__fields[name]

    def __set(self, value):
        raise TypeError, 'read-only attribute'

    def __del(self):
        raise TypeError, 'read-only attribute'

    def __repr__(self):
        return str(self.__stat_info)

    def __str__(self):
        return self.__repr__()

    def __getitem__(self, index):
        return self.__stat_info[index]

    # Triavial get'ers

    def getmode(self):
        return self.__getvar('st_mode')

    def getino(self):
        return self.__getvar('st_ino')

    def getdev(self):
        return self.__getvar('st_dev')

    def getnlink(self):
        return self.__getvar('st_nlink')

    def getuid(self):
        return self.__getvar('st_uid')

    def getgid(self):
        return self.__getvar('st_gid')

    def getsize(self):
        return self.__getvar('st_size')

    def getatime(self):
        return self.__getvar('st_atime')

    def getmtime(self):
        return self.__getvar('st_mtime')

    def getctime(self):
        return self.__getvar('st_ctime')

    # Now publish attributes in read only mode

    st_mode = property(getmode, __set, __del, 'mode property')
    st_ino = property(getino, __set, __del, 'inode property')
    st_dev = property(getdev, __set, __del, 'dev property')
    st_nlink = property(getnlink, __set, __del, 'nlink property')
    st_uid = property(getuid, __set, __del, 'uid property')
    st_gid = property(getgid, __set, __del, 'gid property')
    st_size = property(getsize, __set, __del, 'size property')
    st_atime = property(getatime, __set, __del, 'atime property')
    st_mtime = property(getmtime, __set, __del, 'mtime property')
    st_ctime = property(getctime, __set, __del, 'ctime property')


# ############################
# Internal helper functions #
# ############################


def __walk_generator(tree):
    """This is a generator (http://linuxgazette.net/100/pramode.html)!
    The user can either iterate through the values from the yield
    command (for root, dirs, files in generator: do stuff) or
    explicitly call generator.next() in order to get the next
    iteration tuple.
    """

    if not tree:
        return
    for (dirpath, dirnames, filenames) in tree:
        yield (dirpath, dirnames, filenames)


def __stat_wrapper(stat_tuple):
    """This is a simple wrapper that creates a pseudo stat object from
    a stat tuple.
    """

    return dummystat(stat_tuple)


def __reraise_errors(errors):
    """Shared verification function, to make sure that query did not
    return error in status code or as exceptions.
    """

    if errors:
        filtered_data = '\n'.join(errors).replace('/%s' % BASE_HOME, '')
        raise OSError(filtered_data)


def __raise_status_errors(status, data):
    """Shared verification function, to make sure that query did not
    return error in status code.
    """

    if status:
        filtered_data = data.replace('/%s' % BASE_HOME, '')
        raise OSError(filtered_data)


# #############################
# Public 'os'-like functions #
# #############################


def chmod(path, mode):
    """remote version of operation with same name"""

    errors = []
    (code, servers_string) = distbase.open_session(path, 'WRITE')
    if code:
        raise OSError('%s' % servers_string)
    for server in servers_string.split(' '):
        try:
            (status, data) = distbase.http_chmod(server,
                    HTTPS_CERT_PORT, '/%s' % path, mode)
        except Exception, err:
            errors.append('%s: %s' % (server, err))
            continue
    (code, _) = distbase.close_session(path, 'WRITE')

    __reraise_errors(errors)
    __raise_status_errors(status, data)


def listdir(path):
    """remote version of operation with same name"""

    errors = []
    (code, servers_string) = distbase.open_session(path, 'READ')
    if code:
        raise OSError('%s' % servers_string)
    for server in servers_string.split(' '):
        try:
            (status, data) = distbase.http_listdir(server,
                    HTTPS_CERT_PORT, '/%s' % path)
        except Exception, err:
            errors.append('%s: %s' % (server, err))
            continue
        if not status:
            break
    (code, _) = distbase.close_session(path, 'READ')

    __reraise_errors(errors)
    __raise_status_errors(status, data)
    return eval(data.strip())


def lstat(path):
    return stat(path, _flags='')


def makedirs(path, mode=0775):
    """remote version of operation with same name"""

    # TODO: this trial and error is very suboptimal! move to server
    # Remove any extra slashes

    path = distpath.normpath(path)

    # Try simple mkdir

    try:
        mkdir(path, mode)
        return
    except:
        pass

    # Simple mkdir failed try creating (grand-)parent dirs in turn

    current_dir = path
    parents = []
    while True:
        current_dir = distpath.dirname(current_dir)
        if not current_dir or '/' == current_dir:
            break
        parents.append(current_dir)

    # Bottom up order

    parents.reverse()

    # print "parents: %s" % parents

    for parent_dir in parents:

        # print "mkdir: %s" % parent_dir

        try:
            mkdir(parent_dir, mode)
        except:

            # already exists? just ignore for now..

            pass

    # Finally try creating dir again without catching exceptions

    mkdir(path, mode)


def mkdir(path, mode=0775):
    """remote version of operation with same name"""

    errors = []
    (code, servers_string) = distbase.open_session(path, 'CREATE')
    if code:
        raise OSError('%s' % servers_string)
    for server in servers_string.split(' '):
        try:
            (status, data) = distbase.http_mkdir(server,
                    HTTPS_CERT_PORT, '/%s' % path, mode)
        except Exception, err:
            errors.append('%s: %s' % (server, err))
            continue
    (code, _) = distbase.close_session(path, 'CREATE')

    __reraise_errors(errors)
    __raise_status_errors(status, data)


def remove(path):
    """remote version of operation with same name"""

    errors = []
    (code, servers_string) = distbase.open_session(path, 'DELETE')
    if code:
        raise OSError('%s' % servers_string)
    for server in servers_string.split(' '):
        try:
            (status, data) = distbase.http_remove(server,
                    HTTPS_CERT_PORT, '/%s' % path)
        except Exception, err:
            errors.append('%s: %s' % (server, err))
            continue
    (code, _) = distbase.close_session(path, 'DELETE')

    __reraise_errors(errors)
    __raise_status_errors(status, data)


def removedirs(path):
    """remote version of operation with same name"""

     # TODO: this trial and error is very suboptimal! move to server

    path = distpath.normpath(path)
    current_dir = path
    while True:
        if not current_dir or '/' == current_dir:
            break
        rmdir(current_dir)
        current_dir = distpath.dirname(current_dir)


def rename(src, dst):
    """remote version of operation with same name"""

    errors = []

    # Must appear to be atomic - lock and create copy before removing.

    (code, servers_string) = distbase.open_session(dst, 'CREATE')
    if code:
        raise OSError('%s' % servers_string)
    (code, servers_string) = distbase.open_session(src, 'DELETE')
    if code:
        raise OSError('%s' % servers_string)

    # In case src is a directory the sessions for all the directory
    # contents must be modified, too!
    # TODO: this should really be handled by the storage server (add RENAME session)

    for server in servers_string.split(' '):
        try:
            (status, data) = distbase.http_rename(server,
                    HTTPS_CERT_PORT, '/%s' % src, '/%s' % dst)
        except Exception, err:
            errors.append('%s: %s' % (server, err))
            continue
    (code, _) = distbase.close_session(dst, 'CREATE')
    (code, _) = distbase.close_session(src, 'DELETE')

    __reraise_errors(errors)
    __raise_status_errors(status, data)


def rmdir(path):
    """remote version of operation with same name"""

    errors = []
    (code, servers_string) = distbase.open_session(path, 'DELETE')
    if code:
        raise OSError('%s' % servers_string)
    for server in servers_string.split(' '):
        try:
            (status, data) = distbase.http_rmdir(server,
                    HTTPS_CERT_PORT, '/%s' % path)
        except Exception, err:
            errors.append('%s: %s' % (server, err))
            continue
    (code, _) = distbase.close_session(path, 'DELETE')

    __reraise_errors(errors)
    __raise_status_errors(status, data)


def stat(path, _flags='L'):
    """remote version of operation with same name"""

    errors = []
    (code, servers_string) = distbase.open_session(path, 'READ')
    if code:
        raise OSError('code %s - %s' % (code, servers_string))
    for server in servers_string.split(' '):
        try:
            (status, data) = distbase.http_stat(server,
                    HTTPS_CERT_PORT, '/%s' % path, _flags)
        except Exception, err:
            errors.append('%s: %s' % (server, err))
            continue
        if not status:
            break
        print 'DEBUG: warning stat %s at %s failed: %s %s' % (path,
                server, status, data)
    (code, _) = distbase.close_session(path, 'READ')

    __reraise_errors(errors)
    __raise_status_errors(status, data)
    stat_tuple = eval(data.strip())
    return __stat_wrapper(stat_tuple)


def symlink(src, dst):
    """remote version of operation with same name"""

    errors = []

    # Must appear to be atomic - lock and create copy unlocking.

    (code, servers_string) = distbase.open_session(dst, 'CREATE')
    if code:
        raise OSError('%s' % servers_string)

    # IMPORTANT: src locking disabled since source of symlinks is
    #  not required to exist!
    # code, servers_string = distbase.open_session(src, "READ")
    # if code:
    #    raise OSError("%s" % servers_string)

    for server in servers_string.split(' '):
        try:
            (status, data) = distbase.http_symlink(server,
                    HTTPS_CERT_PORT, '/%s' % src, '/%s' % dst)
        except Exception, err:
            errors.append('%s: %s' % (server, err))
            continue
    (code, _) = distbase.close_session(dst, 'CREATE')

    # code, _ = distbase.close_session(src, "READ")

    __reraise_errors(errors)
    __raise_status_errors(status, data)


def walk(path, topdown=True):
    """Emulate os.walk() which returns a generator object. We can't
    pass the raw generator object directly from the server (not even
    with pickle.dumps()) so we dump a list of the generated
    (dirpath, dirnames, filenames)-tuples and simply eval() the
    entire raw string to recover the structure on arrival.
    """

    errors = []
    (code, servers_string) = distbase.open_session(path, 'READ')
    if code:
        raise OSError('%s' % servers_string)
    for server in servers_string.split(' '):
        try:
            (status, data) = distbase.http_walk(server,
                    HTTPS_CERT_PORT, '/%s' % path, topdown)
        except Exception, err:
            errors.append('%s: %s' % (server, err))
            continue
        if not status:
            break
    (code, _) = distbase.close_session(path, 'READ')

    __reraise_errors(errors)
    __raise_status_errors(status, data)

    # Remove the added /BASE_HOME from all output

    filtered_data = data.replace('/%s' % BASE_HOME, '')

    # recover list of tuples in a way that allows empty list

    tree = eval('%s' % filtered_data)
    return __walk_generator(tree)


