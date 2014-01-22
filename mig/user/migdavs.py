#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migdavs - sample python_webdav-based davs client for user home access
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

Run with:
python migdavs.py [GENERATED_USERNAME]

where the optional GENERATED_USERNAME is the username displayed on your
personal MiG ssh settings page. You will be interactively prompted for it if
it is not provided on the command line.

Please check the global configuration section below if it fails. The comments
should help you tweak the configuration to solve most common problems.

This example should be a good starting point for writing your own custom davs
client acting on your MiG home.
"""

import getpass
import netrc
import os
import sys
import python_webdav
import python_webdav.client
from requests.exceptions import ConnectionError


### Global configuration ###

#server_fqdn = 'dk.migrid.org'
server_fqdn = 'localhost'
server_port = 4443
server_host_key = "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA0ImsGTKx3Rky7jaGDRVts" \
"e80YUcVTYW5NCvU0ntclfosdlFdDli8S3tOLk47DcwZkYt1/XY4rP/LN6unVTiZK7dpRTACuSGr" \
"Kc/TVM63TzG9Zwq1M95pNLdhgRJen1Ez7CzbrWDcsFJNfjxJtvnIWuKmXJ8NBbmhw1nqtZRdvcF" \
"7aLX12KxCxcpJLPtU0N/cbRghi2BTYsGbPUrVd1vYJKhtvc2dQ+vfOiYGSj1bo3LOdTsLmpOoIm" \
"GvYyGnpA8mVgc4sbWW6/RVSkIJxnyoUeP/xgsMQlfcXLZ/9vi/QPe64UVAAAdk18+eNnjHq2Qs8" \
"fxHMVyV2vhLpP/xFdJVNQ=="


class MiGDAVClient(python_webdav.client.Client):
    """Extend basic client with a few methods we want for the testing"""

    def __init__(self, webdav_server_uri, webdav_path='.', port=80, realm='',
                 allow_bad_cert=False):
        """Just call parent constructor for now"""
        python_webdav.client.Client.__init__(self, webdav_server_uri,
                                             webdav_path, port, realm,
                                             allow_bad_cert)

    def stat(self, path):
        """Wrap underlying connection.client.get_properties to provide
        something like os.stat .
        Reuse ls(path) code from python_webdav/client.py
        """
        list_format=('F', 'C', 'M')
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

    def rm(self, path):
        """Wrap underlying connection.client.delete_resource to provide
        something like os.remove .
        """
        return self.client.delete_resource(self.connection, path)

    def get(self, src_path, dst_path):
        """Wrap send_get to emulate sftp get. The existing download_file method
        is limited to providing destination directory so we modify the code
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
        """Wrap upload_file to emulate sftp put"""
        # TODO: this should work without error but upload succeeds and throws
        #    requests.exceptions.ConnectionError: 
        #    HTTPSConnectionPool(host='localhost', port=4443):
        #        Max retries exceeded with url: /this-is-a-migdavs-dummy-file.txt
        #          (Caused by <class 'socket.error'>: [Errno 32] Broken pipe)
        try:
            self.upload_file(src_path, dst_path)
        except ConnectionError:
            pass
 

### Initialize client session ###

if __name__ == "__main__":
    user_name, password = None, None
    try:
        auth_helper = netrc.netrc()
        creds = auth_helper.authenticators(server_fqdn)
        if creds:
            (user_name, _, password) = creds
            print "Read login for %s from .netrc" % server_fqdn
    except Exception, exc:
        print "Didn't find login in ~/.netrc: %s" % exc

    # Override with username/password from command line if given

    if sys.argv[1:]:
        user_name = sys.argv[1]
        print "Using username %s from command line" % user_name
    if sys.argv[2:]:
        password = sys.argv[2]
        print "Using password from command line"

    if not user_name:
        print """Please enter/paste the short alias username from your MiG
ssh settings page"""
        user_name = raw_input('Username: ')
    if not password:
        print """Please enter your password entered on your MiG ssh settings
page"""
        password = getpass.getpass('Password: ')


    # grid_davs server does not support long usernames it seems - so please
    # enable email alias or similar and use it here
#    if len(user_name) < 64:
#        print """Warning: the supplied username is shorter than expected!
#Please verify it on your MiG ssh Settings page in case of failure."""
    if len(user_name) > 99:
        print """Warning: the supplied username is longer than expected!
Please note that the long user names are not supported on the server and that
you should use the short alias found on your MiG ssh Settings page."""

    # Connect with provided settings

    ignore_cert = True
    server_url = 'https://%s:%d' % (server_fqdn, server_port)
    print "connecting to %s" % server_url
    
    client = MiGDAVClient(server_url, allow_bad_cert=ignore_cert)

    print "auth as user %s" % user_name
    client.set_connection(user_name, password)

    ### Sample actions on your MiG home directory ###

    # List and stat files in the remote .ssh dir which should always be there

    base = '.ssh'
    print "listing files in %s" % base
    # ls returns list of list with hrefs - convert to relative paths
    # list includes directory itself so filter on type
    nested_hrefs = client.ls(base, list_format=('T', 'F'))
    hrefs = [i[1] for i in nested_hrefs if i[0] != 'collection']
    files = []
    for uri in hrefs:
        split_str = ':%d/%s/' % (server_port, base)
        pos = uri.find(split_str)
        rel_path = uri[pos+len(split_str):]
        files.append(rel_path)
    print "got files: %s" % files
    path_stat = client.stat(base)
    print "stat %s:\n%s" % (base, path_stat)
    print "files in %s dir:\n%s" % (base, files)
    for name in files:
        rel_path = os.path.join(base, name)
        print "stat on %s" % rel_path
        path_stat = client.stat(rel_path)
        print "stat %s:\n%s" % (rel_path, path_stat)
    dummy = 'this-is-a-migdavs-dummy-file.txt'
    dummy_text = "sample file\ncontents from client\n"
    dummy_fd = open(dummy, "w")
    dummy_fd.write(dummy_text)
    dummy_fd.close()
    print "create dummy in %s" % dummy
    path_stat = os.stat(dummy)
    print "local stat %s:\n%s" % (dummy, path_stat)
    print "upload migdavsdummy in %s home" % dummy
    client.put(dummy, dummy)
    path_stat = client.stat(dummy)
    print "remote stat %s:\n%s" % (dummy, path_stat)
    print "delete dummy in %s" % dummy
    os.remove(dummy)
    print "verify gone: %s" % (dummy not in os.listdir('.'))
    print "download migdavsdummy from %s home" % dummy
    client.get(dummy, dummy)
    path_stat = os.stat(dummy)
    print "local stat %s:\n%s" % (dummy, path_stat)
    dummy_fd = open(dummy, "r")
    verify_text = dummy_fd.read()
    dummy_fd.close()
    print "verify correct contents: %s" % (dummy_text == verify_text)
    print "delete dummy in %s" % dummy
    os.remove(dummy)
    print "delete remote dummy in %s home" % dummy
    client.rm(dummy)

    ### Clean up before exit ###

    del client
