#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# base - shared base helper functions
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

_id_sep, _dir_sep, _id_space, _dir_space = '/', '+', ' ', '_'
_key_val_sep = '='
_remap_fields = ['CN', 'O', 'OU']

def client_id_dir(client_id):
    """Map client ID to a valid directory name:
    client_id is a distinguished name on the form /X=ab/Y=cdef ghi/Z=klmn...
    so we just replace slashes with plus signs and space with underscore
    for the name fields. Please note that e.g. emailAddress may contain
    underscore, which must be preserved.
    """

    dir_parts = []
    for entry in client_id.split(_id_sep):
        if entry.split(_key_val_sep, 1)[0] in _remap_fields:
            entry = entry.replace(_id_space,_dir_space)
        dir_parts.append(entry)
    client_dir = _dir_sep.join(dir_parts)
    return client_dir

def client_dir_id(client_dir):
    """Map client directory name to valid client ID:
    client_dir is a distinguished name on the form +X=ab+Y=cdef_ghi+Z=klmn...
    so we just replace slashes with plus signs and space with underscore
    for the name fields. Please note that e.g. emailAddress may contain
    underscore, which must be preserved.
    """

    id_parts = []
    for entry in client_dir.split(_dir_sep):
        if entry.split(_key_val_sep, 1)[0] in _remap_fields:
            entry = entry.replace(_dir_space, _id_space)
        id_parts.append(entry)
    client_id = _id_sep.join(id_parts)
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
    if not isinstance(val, basestring):
        val = str(val)
    if not isinstance(val, unicode):
        return val
    return val.encode("utf8")

def force_unicode(val):
    """Internal helper to decode unicode strings from utf8 version"""
    # We run into all kind of nasty encoding problems if we mix
    if not isinstance(val, basestring):
        val = str(val)
    if not isinstance(val, unicode):
        return val.decode("utf8")
    return val

def force_utf8_rec(input_obj):
    """Recursive object conversion from unicode to utf8: useful to convert e.g.
    dictionaries with nested unicode strings to a pure utf8 version.
    """
    if isinstance(input_obj, dict):
        return {force_utf8_rec(i): force_utf8_rec(j) for (i, j) in \
                input_obj.items()}
    elif isinstance(input_obj, list):
        return [force_utf8_rec(i) for i in input_obj]
    elif isinstance(input_obj, unicode):
        return force_utf8(input_obj)
    else:
        return input_obj

def generate_https_urls(configuration, url_template, helper_dict):
    """Generate a string with one or more URLS for enabled https login
    methods. The url_template is filled with helper_dict, the best available
    auto_bin web provider method and in turn with the auto_base parameter set
    to the HTTPS URL of enabled login method in prioritized order.
    """
    local_helper = {}
    local_helper.update(helper_dict)
    local_helper['auto_bin'] = 'cgi-bin'
    if configuration.site_enable_wsgi:
        local_helper['auto_bin'] = 'wsgi-bin'
    cert_url = configuration.migserver_https_cert_url
    oid_url = configuration.migserver_https_oid_url
    locations = []
    for i in configuration.site_login_methods:
        if i.endswith('cert') and not cert_url in locations:
            locations.append(cert_url)
        elif i.endswith('oid') and not oid_url in locations:
            locations.append(oid_url)
    filled_list = []
    for https_base in locations:
        local_helper['auto_base'] = https_base
        filled_list.append(url_template % local_helper)
    url_str = '\nor\n'.join(filled_list)
    if locations[1:]:
        url_str += '''
(The URL depends on whether you log in with OpenID or a user certificate -
just use the one that looks most familiar or try them in turn)'''
    return url_str


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
        
