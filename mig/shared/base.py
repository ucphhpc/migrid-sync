#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# base - shared base helper functions
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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
    _user_invisible_dirs, _vgrid_xgi_scripts, cert_field_order, \
    gdp_distinguished_field, valid_gdp_auth_scripts, valid_gdp_anon_scripts

_id_sep, _dir_sep, _id_space, _dir_space = '/', '+', ' ', '_'
_key_val_sep = '='
_remap_fields = ['CN', 'O', 'OU']
cert_field_map = dict(cert_field_order)


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
            entry = entry.replace(_id_space, _dir_space)
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


def fill_user(target):
    """Fill target user dictionary with all expected fields"""

    for (key, _) in cert_field_order:
        target[key] = target.get(key, '')
    return target


def fill_distinguished_name(user):
    """Fill distinguished_name field from other fields if not already set.

    Please note that MiG certificates get empty fields set to NA, so this
    is translated here, too.
    """

    if user.get('distinguished_name', ''):
        return user
    else:
        user['distinguished_name'] = ''
    for (key, val) in cert_field_order:
        setting = user.get(key, '')
        if not setting:
            setting = 'NA'
        user['distinguished_name'] += '/%s=%s' % (val, setting)

    setting = user.get(gdp_distinguished_field, '')
    if setting:
        user['distinguished_name'] += '/%s=%s' \
            % (gdp_distinguished_field, setting)

    return user


def distinguished_name_to_user(distinguished_name):
    """Build user dictionary from distinguished_name string on the form:
    /X=abc/Y=def/Z=ghi

    Please note that MiG certificates get empty fields set to NA, so this
    is translated back here, too.
    """

    user_dict = {'distinguished_name': distinguished_name}
    parts = distinguished_name.split(_id_sep)
    for field in parts:
        if not field or field.find(_key_val_sep) == -1:
            continue
        (key, val) = field.split(_key_val_sep, 1)
        if 'NA' == val:
            val = ''
        if not key in cert_field_map.values():
            user_dict[key] = val
        else:
            for (name, short) in cert_field_order:
                if key == short:
                    user_dict[name] = val
    return user_dict


def extract_field(distinguished_name, field_name):
    """Extract field_name value from client_id if included"""
    user = distinguished_name_to_user(distinguished_name)
    return user.get(field_name, None)


def pretty_format_user(distinguished_name, hide_email=True):
    """Format distinguished_name of a user to a human-friendly display format,
    and optionally include the email address.
    """
    user_dict = distinguished_name_to_user(distinguished_name)
    if hide_email:
        user_dict['email'] = 'email hidden'
    else:
        # NOTE: obfuscate email by replacing with html entities
        for (src, dst) in [('@', '&#064;'), ('.', '&#046;')]:
            user_dict['email'] = user_dict.get('email', '').replace(src, dst)
    return "%(full_name)s, %(organization)s &lt;%(email)s&gt;" % user_dict


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


def invisible_path(path, allow_vgrid_scripts=False):
    """Returns boolean indicating if the file or directory with path is among
    restricted files or directories to completely hide. Such items can not
    safely be removed or modified by users and should only be changed through
    a few restricted interfaces.
    Provided path may be absolute or relative.
    The optional allow_vgrid_scripts argument can be set to allow certain Xgi
    script paths inside otherwise invisible directories. This is useful in
    relation to specifically allowing access to vgrid collaboration component
    Xgi scripts from apache.
    Please note that users should NEVER be allowed write access to those, as it
    would open up a major remote code execution security hole!
    Thus, only use allow_vgrid_scripts when checking access to files in apache
    chroot checks.
    """
    filename = os.path.basename(path)
    if invisible_file(filename):
        return True
    elif invisible_dir(path):
        if allow_vgrid_scripts:
            for i in _vgrid_xgi_scripts:
                # NOTE: mercurial uses hgweb.cgi/BLA to pass args,
                #       so path.endswith(i) is too narrow
                if path.find(i) != -1:
                    return False
        # No valid exception
        return True
    return False


def requested_page(environ=None, fallback='dashboard.py'):
    """Lookup requested page from environ or os.environ if not provided.
    Return fallback if no page was found in environ.
    """
    if not environ:
        environ = os.environ
    # NOTE: RPC wrappers inject name of actual backend as BACKEND_NAME
    page_path = environ.get('BACKEND_NAME', False) or \
        environ.get('SCRIPT_URL', False) or \
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
        return {force_utf8_rec(i): force_utf8_rec(j) for (i, j) in
                input_obj.items()}
    elif isinstance(input_obj, list):
        return [force_utf8_rec(i) for i in input_obj]
    elif isinstance(input_obj, unicode):
        return force_utf8(input_obj)
    else:
        return input_obj


def get_xgi_bin(configuration, force_legacy=False):
    """Lookup the preferred Xgi-bin for server URLs. If WSGI is enabled in the
    configuration wsgi-bin is used. Otherwise the legacy cgi-bin is used.
    The optional force_legacy argument can be used to force legacy cgi-bin use
    e.g. for scripts that are not supported in WSGI.
    """

    if not force_legacy and configuration.site_enable_wsgi:
        return 'wsgi-bin'
    return 'cgi-bin'


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
    mig_cert_url = configuration.migserver_https_mig_cert_url
    ext_cert_url = configuration.migserver_https_ext_cert_url
    mig_oid_url = configuration.migserver_https_mig_oid_url
    ext_oid_url = configuration.migserver_https_ext_oid_url
    locations = []
    for i in configuration.site_login_methods:
        if i == 'migcert' and mig_cert_url and not mig_cert_url in locations:
            locations.append(mig_cert_url)
        elif i == 'extcert' and ext_cert_url and not ext_cert_url in locations:
            locations.append(ext_cert_url)
        elif i == 'migoid' and mig_oid_url and not mig_oid_url in locations:
            locations.append(mig_oid_url)
        elif i == 'extoid' and ext_oid_url and not ext_oid_url in locations:
            locations.append(ext_oid_url)
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


def valid_dir_input(base, variable):
    """This function verifies that user supplied variable used as a directory
    in file manipulation doesn't try to illegally access directories by
    using e.g. '..'. The base argument is the directory that the user
    should be bound to, and the variable is the variable to be checked.
    The verification amounts to verifying that base/variable doesn't
    expand to a path outside base or among the invisible paths.
    """

    # Please note that base_dir must end in slash to avoid access to other
    # dirs when variable is a prefix of another dir in base

    path = os.path.abspath(base) + os.sep + variable
    if os.path.abspath(path) != path or invisible_path(path):

        # out of bounds

        return False
    return True


def user_base_dir(configuration, client_id, trailing_slash=True):
    """This function returns the absolute path for the home directory of client_id.
    By default a trailing slash is appended to the path before it
    is returned but it can be disabled with the boolean trailing_slash argument.
    If no client_id is provided, False is returned instead.
    """
    if not client_id:
        return False
    client_dir = client_id_dir(client_id)
    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir))
    if trailing_slash:
        base_dir += os.sep
    return base_dir


def allow_script(configuration, script_name, client_id):
    """Helper to detect if script_name is allowed to run or not based on site
    configuration. I.e. GDP-mode disables a number of functionalities.
    """
    _logger = configuration.logger
    #_logger.debug("in allow_script for %s from %s" % (script_name, client_id))
    if configuration.site_enable_gdp:
        #_logger.debug("in allow_script gdp for %s" % script_name)
        reject_append = " functionality disabled by site configuration!"
        if not client_id:
            if script_name in valid_gdp_anon_scripts:
                allow = True
                msg = ""
            else:
                allow = False
                msg = "anonoymous access to" + reject_append
        else:
            if script_name in valid_gdp_auth_scripts + valid_gdp_anon_scripts:
                allow = True
                msg = ""
            else:
                allow = False
                msg = "all access to" + reject_append
    else:
        allow, msg = True, ''
    #_logger.debug("allow_script returns %s for %s" % (allow, script_name))
    return (allow, msg)


def brief_list(full_list, max_entries=10):
    """Takes full_list and returns a potentially shortened representation with
    at most max_entries elements where any excess elements are pruned from the
    center. Similar to numpy string output of big arrays.
    """
    if not full_list[max_entries:]:
        return full_list
    half_entries = max_entries / 2
    return full_list[:half_entries] + [' ... shortened ... '] + full_list[-half_entries:]


if __name__ == '__main__':
    orig_id = '/X=ab/Y=cdef ghi/Z=klmn'
    client_dir = client_id_dir(orig_id)
    client_id = client_dir_id(client_dir)
    test_paths = ['simple.txt', 'somedir/somefile.txt']
    sample_file = _user_invisible_files[0]
    sample_dir = _user_invisible_dirs[0]
    illegal = ["%s%s%s" % (prefix, sample_dir, suffix) for (prefix, suffix) in
               [('', ''), ('./', ''), ('/', ''), ('somedir/', ''),
                ('/somedir/', ''), ('somedir/sub/', ''), ('/somedir/sub/', ''),
                ('', '/sub'), ('', '/sub/sample.txt'),
                ('somedir/', '/sample.txt'), ('/somedir/', '/sample.txt'),
                ('/somedir/sub/', '/sample.txt')]] + \
        ["%s%s" % (prefix, sample_file) for prefix, _ in
         [('', ''), ('./', ''), ('/', ''), ('somedir/', ''),
          ('/somedir/', ''), ('somedir/sub/', ''), ('/somedir/sub/', ''),
          ]]
    legal = ["%s%s%s" % (prefix, sample_file, suffix) for (prefix, suffix) in
             [('prefix', ''), ('somedir/prefix', ''), ('', 'suffix'),
              ('', 'suffix/somedir'), ('prefix', 'suffix')]] +\
        ["%s%s%s" % (prefix, sample_dir, suffix) for (prefix, suffix) in
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

    from shared.conf import get_configuration_object
    configuration = get_configuration_object()
    print "check script restrictions:"
    for script_name in ['reqoid.py', 'ls.py', 'sharelink.py', 'put']:
        (allow, msg) = allow_script(configuration, script_name, '')
        print "check %s without client id: %s %s" % (script_name, allow, msg)
        (allow, msg) = allow_script(configuration, script_name, client_id)
        print "check %s with client id '%s': %s %s" % (script_name, client_id,
                                                       allow, msg)
    print "brief format of short list: %s" % brief_list(range(5))
    print "brief format of long list: %s" % brief_list(range(30))
    print "brief format of huge list: %s" % brief_list(range(200))
