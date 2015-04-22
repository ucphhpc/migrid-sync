#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# base - shared base helper functions
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Base helper functions"""

import base64
import os

# IMPORTANT: do not import any other MiG modules here - to avoid import loops
from shared.defaults import sandbox_names, _user_invisible_files, \
     _user_invisible_dirs

id_dir_remap = {'/': '+', ' ': '_'}
dir_id_remap = dict([(val, key) for (key, val) in id_dir_remap.items()])

def client_id_dir(client_id, remap=id_dir_remap):
    """Map client ID to a valid directory name:
    client_id is a distinguished name on the form /X=ab/Y=cdef ghi/Z=klmn...
    so we just replace slashes with plus signs and space with underscore
    in line with remap dictionary to avoid file system problems.
    """

    client_dir = client_id
    for (key, val) in remap.items():
        client_dir = client_dir.replace(key, val)
    return client_dir

def client_dir_id(client_dir, remap=dir_id_remap):
    """Map client directory name to valid client ID:
    client_dir is a distinguished name on the form +X=ab+Y=cdef_ghi+Z=klmn...
    so we just replace slashes with plus signs and space with underscore
    in line with remap dictionary to avoid file system problems.
    """

    client_id = client_dir
    for (key, val) in remap.items():
        client_id = client_id.replace(key, val)
    return client_id

def client_alias(client_id):
    """Map client ID to a version containing only simple ASCII characters.
    This is for e.g. commandline friendly use and it is a one-to-one mapping.
    """
    # sftp and friends choke on potential '=' padding - replace by underscore
    return base64.urlsafe_b64encode(client_id).replace('=', '_')

# TODO: old_id_format should be eliminated after complete migration to full DN

def old_id_format(client_id):
    """Map client ID to the old underscore CN only ID:
    client_id is a distinguished name on the form /X=ab/Y=cdef ghi/CN=klmn...
    so we just extract the CN field and replace space with underscore.
    """

    try:
        old_id = client_id.split('/CN=', 1)[1]
        old_id = old_id.split('/', 1)[0]
        return old_id.replace(' ', '_')
    except:
        return client_id

def sandbox_resource(unique_resource_name):
    """Returns boolean indicating if the resource is a sandbox"""
    fqdn = unique_resource_name.rsplit('.', 1)[0]
    return fqdn in sandbox_names

def invisible_file(filename):
    """Returns boolean indicating if the file with filename is among restricted
    files to completely hide. Such files can not safely be removed or modified
    by users and should only be changed through fixed interfaces.
    Provided filename is expected to be without directory prefix.
    """
    return filename in _user_invisible_files

def invisible_dir(dir_path):
    """Returns boolean indicating if the directory with dir_path is among
    restricted directories to completely hide. Such directories can not
    safely be removed or modified by users and should only be changed
    through fixed interfaces.
    Provided dir_path can contain a directory prefix.
    """
    for dirname in dir_path.split(os.sep):
        if dirname in _user_invisible_dirs:
            return True
    return False

def invisible_path(path):
    """Returns boolean indicating if the file or directory with path is among
    restricted files or directories to completely hide. Such items can not
    safely be removed or modified by users and should only be changed through
    a few restricted interfaces.
    Provided path may be absolute or relative.
    """
    filename = os.path.basename(path)
    if invisible_file(filename):
        return True
    elif invisible_dir(path):
        return True
    return False

def requested_page(environ=None, fallback='dashboard.py'):
    """Lookup requested page from environ or os.environ if not provided.
    Return fallback if no page was found in environ.
    """
    if not environ:
        environ = os.environ
    page_path = environ.get('SCRIPT_URL', False) or \
                environ.get('PATH_INFO', False) or \
                environ.get('REQUEST_URI', fallback).split('?', 1)[0]
    return page_path

def force_utf8(val):
    """Internal helper to encode unicode strings to utf8 version"""
    # We run into all kind of nasty encoding problems if we mix
    if not isinstance(val, unicode):
        return val
    return val.encode("utf8")

def force_unicode(val):
    """Internal helper to decode unicode strings from utf8 version"""
    # We run into all kind of nasty encoding problems if we mix
    if not isinstance(val, unicode):
        return val.decode("utf8")
    return val


if __name__ == '__main__':
    orig_id = '/X=ab/Y=cdef ghi/Z=klmn'
    client_dir = client_id_dir(orig_id)
    client_id = client_dir_id(client_dir)
    test_paths = ['simple.txt', 'somedir/somefile.txt']
    sample_file = _user_invisible_files[0]
    sample_dir = _user_invisible_dirs[0]
    illegal = ["%s%s%s" % (prefix, sample_dir, suffix) for (prefix, suffix) in \
               [('', ''), ('./', ''), ('/', ''), ('somedir/', ''),
                ('/somedir/', ''), ('somedir/sub/', ''), ('/somedir/sub/', ''),
                ('', '/sub'), ('', '/sub/sample.txt'),
                ('somedir/', '/sample.txt'), ('/somedir/', '/sample.txt'),
                ('/somedir/sub/', '/sample.txt')]] + \
                ["%s%s" % (prefix, sample_file) for prefix, _ in \
               [('', ''), ('./', ''), ('/', ''), ('somedir/', ''),
                ('/somedir/', ''), ('somedir/sub/', ''), ('/somedir/sub/', ''),
                ]]
    legal = ["%s%s%s" % (prefix, sample_file, suffix) for (prefix, suffix) in \
               [('prefix', ''), ('somedir/prefix', ''), ('', 'suffix'),
                ('', 'suffix/somedir'), ('prefix', 'suffix')]] +\
                ["%s%s%s" % (prefix, sample_dir, suffix) for (prefix, suffix) in \
               [('prefix', ''), ('somedir/prefix', ''), ('', 'suffix'),
                ('', 'suffix/somedir'), ('prefix', 'suffix')]]
    legal += ['sample.txt', 'somedir/sample.txt', '/somedir/sample.txt']
    print "orig id %s, dir %s, id %s (match %s)" % \
          (orig_id, client_dir, client_id, orig_id == client_id)
    print "invisible tests"
    print "check that these are invisible:"
    for path in illegal:
        print "  %s: %s" % (path, invisible_path(path))
    print "make sure these are not invisible:"
    for path in legal:
        print "  %s: %s" % (path, not invisible_path(path))
        
