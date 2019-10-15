#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migdavs - sample python_webdav-based davs client for user home access
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Sample python_webdav-based davs client working with your MiG home.

Requires python_webdav (>0.4) (https://github.com/scaryclam/python-webdav) and
thus also the dependencies
lxml (https://pypi.python.org/pypi/lxml),
requests (https://pypi.python.org/pypi/requests),
mock (https://pypi.python.org/pypi/mock),
and BeautifulSoup (https://pypi.python.org/pypi/BeautifulSoup).
which can all be installed with:
pip install python_webdav httplib2 lxml mock beautifulsoup

Run with:
python migdavs.py [SERVER] [PORT] [USERNAME] [PASSWORD]

where the optional arguments specify the SERVER and PORT running the WebDAVS
service to use and the USERNAME would likely be your registered email or
whatever automatic username is displayed on your personal MiG WebDAVS Settings
page. Similarly PASSWORD is the one you saved there.
You will be interactively prompted for credentials if they are neither provided
on the command line nor available in any local ~/.netrc file.

This example should be a good starting point for writing your own custom davs
client acting on your MiG home.
"""

import getpass
import netrc
import os
import sys
import httplib2

import python_webdav
import python_webdav.client
from requests.exceptions import ConnectionError


class MiGDAVClient(python_webdav.client.Client):

    """Extend basic client with a few methods we want for the testing"""

    def __init__(self, webdav_server_uri, webdav_path='.', port=80, realm=''):
        """Just call parent constructor for now"""
        python_webdav.client.Client.__init__(self, webdav_server_uri,
                                             webdav_path, port, realm)

    def stat(self, path):
        """Wrap underlying connection.client.get_properties to provide
        something like os.stat .
        Reuse ls(path) code from python_webdav/client.py
        """
        list_format = ('F', 'C', 'M')
        # Format Map
        format_map = {'T': 'resourcetype',
                      'D': 'creationdate',
                      'F': 'href',
                      'M': 'getlastmodified',
                      'A': 'executable',
                      'E': 'getetag',
                      'C': 'getcontenttype'}

        props = self.client.get_properties(self.connection, path)
        property_lists = []
        for prop in props:
            for symbol in list_format:
                str_prop = getattr(prop, format_map[symbol], None)
                if not str_prop:
                    str_prop = ''
                if symbol == 'E':
                    str_prop = str_prop.strip('"')
                property_lists.append((format_map[symbol], str_prop))
        # TODO: convert to stat tuple/object
        return property_lists

    def exists(self, path):
        """Wrap underlying connection.client.send_get to provide
        something like os.path.exists"""
        result = False
        try:
            resource_path = "%s/%s" % (
                self.connection.path.rstrip('/'), path.lstrip('/'))
            resp, content = self.connection.send_get(resource_path)
            if int(resp.get('status', 0)) == 200:
                result = True
        except httplib2.ServerNotFoundError:
            raise
        except Exception, exc:
            result = False

        return result

    def rm(self, path):
        """Wrap underlying connection.client.delete_resource to provide
        something like os.remove
        """
        return self.client.delete_resource(self.connection, path)

    def cp(self, src, dest):
        """Wrap underlying connection.client.delete_resource to provide
        something like shutil.copyfile(src, dst)
        """
        return self.client.copy_resource(self.connection, src, dest)

    def mv(self, src, dest):
        """Wrap underlying connection to provide
        something shutil.move((src, dst)
        """
        try:
            full_destination = httplib2.urlparse.urljoin(
                self.connection.host, dest)
            headers = {'Destination': full_destination}
            resp, content = self.connection._send_request(
                'MOVE', src, headers=headers)
            return resp, content
        except httplib2.ServerNotFoundError:
            raise

    def get(self, src_path, dst_path):
        """Wrap send_get to emulate sftp get. The existing download_file method
        is limited to providing destination directory, so we modify the code
        from there.
        """
        resource_path = "%s/%s" % (
            self.connection.path.rstrip('/'), src_path.lstrip('/'))
        resp, content = self.connection.send_get(resource_path)
        file_name = os.path.basename(src_path)

        try:
            file_fd = open(dst_path, 'wb')
            file_fd.write(content)
        except IOError:
            raise
        finally:
            file_fd.close()

        return resp, content

    def put(self, src_path, dst_path):
        """Wrap send_put to emulate sftp put. The existing upload_file method
        appears broken and results in a 400 error response from the server, so
        we modify the code from there.
        """
        try:
            src_fd = open(src_path, 'rb')
            resp, content = self.connection.send_put(dst_path, src_fd.read())
        except IOError:
            raise
        finally:
            src_fd.close()


# Initialize client session ###

if __name__ == "__main__":
    server_fqdn = 'dk-io.migrid.org'
    server_port = 443
    user_name, password = None, None

    # Override with username/password from command line if given

    if sys.argv[1:]:
        server_fqdn = sys.argv[1]
    if sys.argv[2:]:
        server_port = int(sys.argv[2])
    if sys.argv[3:]:
        user_name = sys.argv[3]
    if sys.argv[4:]:
        password = sys.argv[4]

    print "Using server at %s:%d" % (server_fqdn, server_port)

    if not user_name or not password:
        print "Reading any available credentials from ~/.netrc"
        auto_user_name, auto_password = None, None
        try:
            auth_helper = netrc.netrc()
            creds = auth_helper.authenticators(server_fqdn)
            if creds:
                (auto_user_name, _, auto_password) = creds
                if not user_name or auto_user_name == user_name:
                    user_name = auto_user_name
                    password = auto_password
                    print "Read login for %s from .netrc" % server_fqdn
        except Exception, exc:
            print "Didn't find suitable credentials in ~/.netrc: %s" % exc

    if not user_name:
        print """Please enter/paste the short alias username from your %s
WebDAVS Settings page""" % server_fqdn
        user_name = raw_input('Username: ')

        print """Please enter your password entered on your %s WebDAVS
Settings page""" % server_fqdn
        password = getpass.getpass('Password: ')

    # Connect with provided settings

    server_url = 'https://%s:%d' % (server_fqdn, server_port)
    print "connecting to %s" % server_url

    client = MiGDAVClient(server_url)

    print "auth as user %s" % user_name
    client.set_connection(user_name, password)

    gdp_user = False
    if user_name.count('@') == 2:
        gdp_user = True
        print "GDP user detected"

    # Sample actions on your MiG home directory ###

    # List and stat files in the remote .davs dir which should always be there
    # for NON GDP users

    if not gdp_user:
        base = '.davs'
        if not client.exists(base):
            print "ERROR: remote dir '%s' does NOT exist" % base
        else:
            print "listing files in %s" % base
            # ls returns list of list with hrefs - convert to relative paths
            # list includes directory itself so filter on type
            nested_hrefs = client.ls(base, list_format=('T', 'F'))
            hrefs = [i[1] for i in nested_hrefs if i[0] != 'collection']
            files = []
            for uri in hrefs:
                # NOTE: uri may be full URL or slash-prefixed server path here - strip
                rel_path = uri.replace(server_url, '').lstrip('/')
                rel_path = rel_path.replace(base, '').lstrip('/')
                files.append(rel_path)
            print "got files: %s" % files
            path_stat = client.stat(base)
            print "stat '%s':\n%s" % (base, path_stat)
            print "files in '%s' dir:\n%s" % (base, files)
            for name in files:
                rel_path = os.path.join(base, name)
                print "stat on '%s'" % rel_path
                path_stat = client.stat(rel_path)
                print "stat '%s':\n%s" % (rel_path, path_stat)

    # GDP users chroot to vgrid_files_home/VGRIDNAME

    if not gdp_user:
        welcome = 'welcome.txt'
    else:
        welcome = 'README'
    if not client.exists(welcome):
        print "ERROR: remote file '%s' does NOT exist" % welcome
        exit(1)
    else:
        print "download '%s' from home" % welcome
        client.get(welcome, welcome)
        path_stat = os.stat(welcome)
        print "local stat '%s':\n%s" % (welcome, path_stat)
    dummy = 'this-is-a-migdavs-dummy-file.txt'
    dummy_text = "sample file\ncontents from client\n"
    dummy_fd = open(dummy, "w")
    dummy_fd.write(dummy_text)
    dummy_fd.close()
    print "create dummy '%s' in home" % dummy
    path_stat = os.stat(dummy)
    print "local stat '%s':\n%s" % (dummy, path_stat)
    print "upload migdavsdummy '%s' in home" % dummy
    client.put(dummy, dummy)
    print "stat on uploaded '%s'" % dummy
    path_stat = client.stat(dummy)
    print "remote stat '%s':\n%s" % (dummy, path_stat)
    print "delete dummy '%s' in home" % dummy
    os.remove(dummy)
    print "verify gone: '%s'" % (dummy not in os.listdir('.'))
    print "download '%s' from home" % dummy
    client.get(dummy, dummy)
    path_stat = os.stat(dummy)
    print "local stat '%s':\n%s" % (dummy, path_stat)
    dummy_fd = open(dummy, "r")
    verify_text = dummy_fd.read()
    dummy_fd.close()
    print "verify correct contents: %s" % (dummy_text == verify_text)
    print "delete dummy '%s' in home " % dummy
    os.remove(dummy)
    dummy_copy = "%s.copy" % dummy
    print "remote copy dummy '%s' -> '%s' in home" % (dummy, dummy_copy)
    client.cp(dummy, dummy_copy)
    path_stat = client.stat(dummy_copy)
    print "remote stat '%s':\n%s" % (dummy_copy, path_stat)
    dummy_move = "%s.move" % dummy
    print "move remote dummy '%s' -> '%s' in home" % (dummy, dummy_move)
    client.mv(dummy, dummy_move)
    path_stat = client.stat(dummy_move)
    print "remote stat '%s':\n%s" % (dummy_move, path_stat)
    print "delete remote dummy '%s' in home" % dummy
    client.rm(dummy)
    print "delete remote dummy '%s' in home" % dummy_copy
    client.rm(dummy_copy)
    print "delete remote dummy '%s' in home" % dummy_move
    client.rm(dummy_move)

    illegal_dir = '../'
    illegal_dummy = os.path.join(illegal_dir, 'tmp-' + dummy)
    print "change remote dir outside home - should fail"
    try:
        client.chdir('.')
        old_pwd = client.pwd()
        client.chdir(illegal_dir)
        new_pwd = client.pwd()
        if new_pwd == old_pwd:
            raise Exception('chdir did not change anything!')
        else:
            print "changed to illegal dir '%s' from '%s'" % (new_pwd, old_pwd)
    except Exception, exc:
        print "correctly rejected change dir to illegal destination: '%s'" % exc
    print "copy remote dummy outside home - should fail"
    try:
        resp, contents = client.copy(dummy, illegal_dummy)
        print resp, contents
    except Exception, exc:
        print "correctly rejected copy to illegal destination"
    print "delete remote dummy outside home - should fail"
    try:
        resp, contents = client.rm(illegal_dummy)
        if resp.status_code in range(400, 410):
            raise Exception("delete failed with '%s'" % resp)
        else:
            print "copied to illegal destination '%s'" % illegal_dummy
    except Exception, exc:
        print "correctly rejected removal of illegal dummy: %s" % exc

    # Clean up before exit ###

    del client
