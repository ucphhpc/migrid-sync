#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_sftp - SFTP server providing access to MiG user homes
# Copyright (C) 2010  The MiG Project lead by Brian Vinter
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

#
# This code is a heavily modified version of the sftp server from
# http://achievewith.us/hg/simple_sftp_server
#
# = Original copyright notice follows =

# This is the MIT license:
# http://www.opensource.org/licenses/mit-license.php

# Copyright (c) 2009 Digital Achievement Incorporated and contributors.

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# = End of original copyright notice =

"""Provide SFTP access to MiG user homes"""

import base64
import glob
import logging
import os
import socket
import sys
import tempfile
import threading
import time
from optparse import OptionParser
from StringIO import StringIO
import paramiko
import paramiko.util

from shared.conf import get_configuration_object


configuration, logger = None, None


class User(object):
    def __init__(self, username, password, 
                 chroot=True, home=None, public_key=None):
        self.username = username
        self.password = password
        self.chroot = chroot
        self.public_key = public_key
        if type(self.public_key) in (str, unicode):
            bits = base64.decodestring(self.public_key.split(' ')[1])
            msg = paramiko.Message(bits)
            key = paramiko.RSAKey(msg)
            self.public_key = key

        self.home = home
        if self.home is None:
            self.home = self.username


class SFTPHandle(paramiko.SFTPHandle):
    def __init__(self, flags=0, path=None):
        paramiko.SFTPHandle.__init__(self, flags)
        self.path = path
        if(flags == 0):
            self.readfile = open(path, "r")
        else:
            self.writefile = open(path, "w")


class SimpleSftpServer(paramiko.SFTPServerInterface):
    def __init__(self, server, transport, fs_root, users, *largs, **kwargs):
        self.transport = transport
        self.root = fs_root
        self.user_name = self.transport.get_username()
        self.users = users

        if self.users[self.user_name].chroot:
            self.root = "%s/%s" % (self.root, self.users[self.user_name].home)

    def get_fs_path(self, sftp_path):
        real_path = "%s/%s" % (self.root, sftp_path)
        real_path = real_path.replace('//', '/')
        
        if not os.path.realpath(real_path).startswith(self.root):
            raise Exception("Invalid path")

        logger.debug("real_path :: %s" % real_path)
        return(real_path)

    def open(self, path, flags, attr):
        real_path = self.get_fs_path(path)
        logger.debug("open %s :: %s" % (path, real_path))
        #logger.debug("open %s :: %d" % (path, attr))
        return(SFTPHandle(flags, real_path))

    def list_folder(self, path):
        real_path = self.get_fs_path(path)
        logger.debug("list_folder %s :: %s" % (path, real_path))
        rc = []
        for filename in os.listdir(real_path):
            full_name = ("%s/%s" % (real_path, filename)).replace("//", "/")
            rc.append(paramiko.SFTPAttributes.from_stat(os.stat(full_name), filename.replace(self.root, '')))
        return rc

    def stat(self, path):
        real_path = self.get_fs_path(path)
        logger.debug("stat %s :: %s" % (path, real_path))
        return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)

    def lstat(self, path):
        real_path = self.get_fs_path(path)
        logger.debug("lstat %s :: %s" % (path, real_path))
        return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)

    def remove(self, path):
        real_path = self.get_fs_path(path)
        logger.debug("remove %s :: %s" % (path, real_path))
        os.remove(real_path)
        return paramiko.SFTP_OK

    def rename(self, oldpath, newpath):
        logger.debug("rename %s %s" % (oldpath, newpath))
        real_oldpath = self.get_fs_path(oldpath)
        real_newpath = self.get_fs_path(newpath)
        # print "rename %s %s" % (real_oldpath, real_newpath)
        os.rename(real_oldpath, real_newpath)
        return paramiko.SFTP_OK

    def mkdir(self, path, mode):
        logger.debug("mkdir %s" % path)
        real_path = self.get_fs_path(path)
	# Force MiG default mode
        os.mkdir(real_path, 0755)
        return paramiko.SFTP_OK

    def rmdir(self, path):
        logger.debug("rmdir %s" % path)
        real_path = self.get_fs_path(path)
        os.rmdir(real_path)
        return paramiko.SFTP_OK

    def chattr(self, path, attr):
        logger.debug("chattr %s" % path)
	# Prevent users from messing with access modes
        return paramiko.SFTP_OP_UNSUPPORTED
         
    #def canonicalize(self, path):
    #    print "canonicalize %s" % path
    #    return paramiko.SFTPServerInterface.canoncialize(self, path)

    def readlink(self, path):
        logger.debug("readlink %s" % path)
        real_path = self.get_fs_path(path)
	relative_path = os.readlink(path).replace(self.root, '')
	return relative_path

    def symlink(self, target_path, path):
        logger.debug("symlink %s" % target_path)
	# Prevent users from creating symlinks for security reasons
        return paramiko.SFTP_OP_UNSUPPORTED


class SimpleSSHServer(paramiko.ServerInterface):
    def __init__(self, users):
        self.event = threading.Event()
        self.users = users
        self.authenticated_user = None

    def check_channel_request(self, kind, chanid):
        logger.info("channel_request: %s, %s" % (kind, chanid))
        return paramiko.OPEN_SUCCEEDED

    def check_auth_password(self, username, password):
        if self.users.has_key(username):
            if self.users[username].password == password:
                logger.info("Authenticated %s" % username)
                return paramiko.AUTH_SUCCESSFUL
        logger.info("Rejected %s" % username)
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        if self.users.has_key(username):
            u = self.users[username]
            if u.public_key is not None:
                if u.public_key.get_base64() == key.get_base64():
                    logger.info("Public key match for %s" % username)
                    return paramiko.AUTH_SUCCESSFUL
        logger.info('Public key authentication failed')
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def get_authenticated_user(self):
        return self.authenticated_user

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    #def check_channel_subsystem_request(self, channel, name):
    #    print channel
    #    print name
    #    self.event.set()
    #    return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                  pixelheight, modes):
        return True


def accept_client(client, addr, root_dir, users, host_rsa_key, conf={}):
    usermap = {}
    for u in users:
        usermap[u.username] = u

    host_key_file = StringIO(host_rsa_key)
    host_key = paramiko.RSAKey(file_obj=host_key_file)
    transport = paramiko.Transport(client)
    transport.load_server_moduli()
    transport.add_server_key(host_key)

    if conf.has_key("sftp_implementation"):
        mod_name, class_name = conf['sftp_implementation'].split(':')
        fromlist = None
        try:
            parent = mod_name[0:mod_name.rindex('.')]
            fromlist = [parent]
        except:
            pass
        mod = __import__(mod_name, fromlist=fromlist)
        impl = getattr(mod, class_name)
        logger.info("Custom implementation: %s" % conf['sftp_implementation'])
    else:
        impl = SimpleSftpServer
    transport.set_subsystem_handler("sftp", paramiko.SFTPServer, sftp_si=impl, transport=transport, fs_root=root_dir, users=usermap)

    server = SimpleSSHServer(users=usermap)
    transport.start_server(server=server)
    channel = transport.accept()
    while(transport.is_active()):
        time.sleep(3)

    username = server.get_authenticated_user()
    if username is not None:
        user = usermap[username]
        logger.info("Login from %s" % username)
        # Ignore user connection here as we only care about sftp 

def refresh_users(conf):
    '''Reload users from conf if it changed on disk'''
    last_update = conf['time_stamp']
    auth_name = '.authorized_keys'
    old_usernames = [i.username for i in conf['users']]
    cur_usernames = []
    for path in glob.glob(os.path.join(conf['root_dir'], '*', auth_name)):
        # TODO: use persistent regexp match instead
        user_home = path.replace(os.sep + auth_name, '')
        user_dir = user_home.replace(conf['root_dir'] + os.sep, '')
        # TODO: use real DN version instead?
        user_id = user_dir
        user_hex = base64.b16encode(user_id).lower()
        cur_usernames.append(user_hex)
        if last_update >= os.path.getmtime(path):
            continue
        # TODO: move to user settings
        key_fd = open(path, 'r')
        # TODO: consider multiple keys?
        all_keys = key_fd.readlines()
        key_fd.close()
        # Clean up all old entries for this user
        conf['users'] = [i for i in conf['users'] if i.username != user_hex]
        for user_key in all_keys:
            if not user_key.startswith('ssh-rsa '):
                logger.warning("Skipping broken key %s for user %s" % \
                               (user_key, user_id))
                continue
            user_key = user_key.strip()
            logger.info("Adding user:\nname: %s\nhex: %s\nhome: %s\nkey: %s"\
                        % (user_id, user_hex, user_dir, user_key))
            conf['users'].append(
                User(username=user_hex, home=user_dir, password=None,
                     public_key=user_key, chroot=True),
                )
    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d deleted users" % len(removed))
        conf['users'] = [i for i in conf['users'] if not i.username in removed]
    logger.info("Refreshed users from configuration (%d users)" % len(conf['users']))
    conf['time_stamp'] = time.time()
    return conf

def start_service(service_conf):
     server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     # Allow reuse of socket to avoid TCP time outs
     server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
     server_socket.bind((service_conf['address'], service_conf['port']))
     server_socket.listen(10)

     logger.info("Accepting connections")
     while True:
         client, addr = server_socket.accept()
         # automatic reload of users if more than five minutes old
         if service_conf['time_stamp'] + 300 < time.time():
             service_conf = refresh_users(service_conf)
         t = threading.Thread(target=accept_client, args=[client, 
                                                          addr, 
                                                          service_conf['root_dir'],
                                                          service_conf['users'],
                                                          service_conf['host_rsa_key'],
                                                          service_conf,])
         t.start()


if __name__ == "__main__":
    configuration = get_configuration_object()
    logger = configuration.logger
    # TODO: move all options to configuration
    address = ""
    port = 2222
    host_rsa_key = """
-----BEGIN RSA PRIVATE KEY-----
MIIEoQIBAAKCAQEArJqP/6XFBa88x/DUootMmSzYa3MxcTV9FjNYUomqbQlGzuHa
n1Ef6YClJuBWu1eCdZfoeUoa56du1XV2eGKdDjWEqyie2uZ8RZeJZvT1wCuyvO6X
E143A4z3xHi6R6Qi7rimJFpxL6lGmYHx64wQgL93FXTe/HrmdPoxGeTEf+PnN/PV
Se321o/Ludqfu+8cldbuKaYRRZJSPT+sIMafvErL86I3JShYqaBjXcic8yYgaAZx
6Ieu6A19UJzZurQpCdnWoMMLEQ1EgU4LIkUg+SzVSTpBDV3uiBB0+iOdG+v0v+RO
53GAcKRx9Y38vQazpdAw4AhX97Hj6c/WcpET+QIBIwKCAQBsfmkkWZHJDxBDKao6
SO5RpyjzFTUFVNJIeAuhmFx/DSUxlUeXV5Bm4yX7Le1f0JslWCu59BDpYe3lQoT7
NqvdC7J6NspAc56SJLzEX3Xmgd4QW3Tnmk53QqpePUHj44Or/wlYreC+3240mtKU
DuXNRSZIAFGmBBvUgAGbP1bxTGRShWlebnDsEFuv8BnrjTB1GBN3SshgwTuApete
7yPPNNPhiAMHN27z5p5sMDU43+FgZd8GEJbHckmriIcwLr1Q0iwlmsrYRndRnA7u
bbl9D5SwTROE8mtACHBLOdkJ5glfp68GhKjZ+HPTkI+fKqv70DOB7TsP9F4EsNO/
FQUzAoGBANo2ScHL6RFHUpztE0+dc9g9Yk4S+tjW1sVHMOWGN/KmwiqBIwiusvWY
vXf/4i/kbehGnwedAtfRmjQSJbIyOEhMt1MxaN0Wn44YUgoWCbfplJG1Tmk25eEX
VrwOahTtzDGibtHNNmi97D2dFR7V36mhECTqwyzEE142yGrRJnLPAoGBAMp+YXd/
D2B0xhFMJmyzYHdBFCQHbm4DWZcGey09tSKo+mei+EDq+knSrjUmJV40PMXwxVjw
anLZJjEh72e71G28jlR5WEhciT5nJqN5pB8Oc9cHFCGC9mLQrEwW9MYqAz/WvCx4
lpa1Cge2b/lp7snc3Yt4BfAl35MIqElOg163AoGAGPBC8ZOlm5MfYmQ8uKRHwPES
jJR0cI2U41iX37eRXY9mpcWdmpefbIZ8DbbYBXkxIdwvbpWZ7Md/Vmh5VjGgCENI
JsPReFpbYLJShM9RkVyGAgYXlv71s1Mf2vpVRDhvG52JAgjTBKf9veYRCtadN/Um
ap58tKixwZ/cY/qlTvMCgYBFbSi7QYGdad2CRf6LqzcEUNO0lNVnjB63b++3vWKs
zDiYj6WSmbTmHFj8R5fIhvBD3YV9lEHA+f53PtW9KnS36OBXeg+jx/SKbIJGrVzX
cqtfqqfQ+bOPmACPHdBD8SWvfNLNayxQ7Z0J9Wg4QZOy7KO6yhCqG50cd/8vE5rB
YwKBgQCH9mHpdfORUCXVt1QScw29mhLskx5SA/9vU4lrKpwr0Kkce+d0Cex14jWG
cLz1fOlcctHsIQBMFxEBR0dM7RNX/kdvWfhiPDl1VgDQIyrAEC9euig92hKhmA2E
Myw1d5t46XP97y6Szrhcsrt15pmSKD+zLYXD26qoxKJOP9a6+A==
-----END RSA PRIVATE KEY-----
"""
    sftp_conf = {'address': address,
                 'port': port,
                 'root_dir': os.path.abspath(configuration.user_home),
                 'host_rsa_key': host_rsa_key,
                 'users': [],
                 'time_stamp': 0}
    start_service(sftp_conf)
