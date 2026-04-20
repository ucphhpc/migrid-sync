#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migsftp - sample paramiko-based sftp client for user home access
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#

"""Sample Paramiko-based sftp client working with your MiG home.

Requires paramiko (http://pypi.python.org/pypi/paramiko) and thus PyCrypto
(http://pypi.python.org/pypi/pycrypto).

Run with:
python migsftp.py [ADDRESS] [PORT] [USERNAME] [KNOWN_HOST_KEY] [AUTH_METHOD]

where the optional
ADDRESS is the FQDN of the SFTP server (default is dk-io.migrid.org)
PORT is the port of the SFTP server (default is 22)
USERNAME is the username e.g. displayed on your personal SFTP Setup page.
KNOWN_HOST_KEY is the host public key (default is to look in ~/.ssh/known_host)
AUTH_METHOD is password, agent or key (default is password)
You will be interactively prompted for username if it is not provided on the
command line.

Please check the global configuration section below if it fails. The comments
should help you tweak the configuration to solve most common problems.

This example should be a good starting point for writing your own custom sftp
client acting on your MiG home.
"""

from __future__ import print_function

import base64
import getpass
import os
import sys

import paramiko


# Global configuration ###

server_fqdn = 'dk-io.migrid.org'
server_port = 22
user_name = 'UNSET'
server_host_key = 'AUTO'
known_hosts_path = os.path.expanduser("~/.ssh/known_hosts")
user_auth = 'password'
user_key = None
user_pw = ''
host_key_policy = paramiko.RejectPolicy()
data_compression = False


# Initialize client session ###

if __name__ == "__main__":

    # Get server and login details from command line or use defaults

    if sys.argv[1:]:
        server_fqdn = sys.argv[1]
    if sys.argv[2:]:
        server_port = int(sys.argv[2])
    if sys.argv[3:]:
        user_name = sys.argv[3]
    if sys.argv[4:]:
        server_host_key = sys.argv[4]
    if sys.argv[5:]:
        user_auth = sys.argv[5]
    if user_name == 'UNSET':
        user_name = input("username: ")
    if len(user_name) < 10 and user_name.find('@') == -1:
        print("""Warning: the supplied username is not on expected form!
Please verify it on your MiG ssh Settings page in case of failure.""")
        sys.exit(1)

    # Connect with provided settings

    ssh = paramiko.SSHClient()
    known_host_keys = ssh.get_host_keys()
    if server_host_key == 'AUTO':
        # For safe and silent operation we try already known host keys
        ssh.load_system_host_keys()
    else:
        key_type, key_data = server_host_key.split(' ')[:2]
        pub_key = paramiko.RSAKey(data=base64.b64decode(key_data))
        # Add host key both on implicit and explicit port format
        server_fqdn_port = "[%s]:%d" % (server_fqdn, server_port)
        known_host_keys.add(server_fqdn, key_type, pub_key)
        known_host_keys.add(server_fqdn_port, key_type, pub_key)
    known_host_keys.load(known_hosts_path)
    if user_auth.lower() == 'password':
        user_pw = getpass.getpass()
    elif user_auth.lower() == 'agent':
        user_key = None
    else:
        user_key = user_auth
        user_pw = getpass.getpass()
    try:
        ssh.connect(server_fqdn, username=user_name, port=server_port,
                    password=user_pw, key_filename=user_key,
                    compress=data_compression)
        sftp = ssh.open_sftp()
    except paramiko.ssh_exception.SSHException as exc:
        if 'known_hosts' in str(exc):
            print("Missing host pub key for requested server %s" % server_fqdn)
            print("You need to provide it or have it in ~/.ssh/known_hosts")
            sys.exit(1)
        else:
            raise exc

    # Sample actions on your MiG home directory ###

    # List and stat files in the remote .ssh dir which should always be there

    base = '.ssh'
    files = sftp.listdir(base)
    path_stat = sftp.stat(base)
    print("stat %s:\n%s" % (base, path_stat))
    print("files in %s dir:\n%s" % (base, files))
    for name in files:
        rel_path = os.path.join(base, name)
        path_stat = sftp.stat(rel_path)
        print("stat %s:\n%s" % (rel_path, path_stat))
    dummy = 'this-is-a-migsftp-dummy-file.txt'
    dummy_text = "sample file\ncontents from client\n"
    dummy_fd = open(dummy, "w")
    dummy_fd.write(dummy_text)
    dummy_fd.close()
    print("create dummy in %s" % dummy)
    path_stat = os.stat(dummy)
    print("local stat %s:\n%s" % (dummy, path_stat))
    print("upload migsftpdummy in %s home" % dummy)
    sftp.put(dummy, dummy)
    path_stat = sftp.stat(dummy)
    print("remote stat %s:\n%s" % (dummy, path_stat))
    path_fd = sftp.file(dummy)
    block_size = max(len(dummy_text), 256)
    path_md5_digest = path_fd.check("md5", block_size=block_size)
    path_sha1_digest = path_fd.check("sha1", block_size=block_size)
    path_fd.close()
    print("remote md5 sum %s:\n%s" %
          (dummy, base64.b16encode(path_md5_digest)))
    print("remote sha1 sum %s:\n%s" %
          (dummy, base64.b16encode(path_sha1_digest)))
    print("delete dummy in %s" % dummy)
    os.remove(dummy)
    print("verify gone: %s" % (dummy not in os.listdir('.')))
    print("download migsftpdummy from %s home" % dummy)
    sftp.get(dummy, dummy)
    path_stat = os.stat(dummy)
    print("local stat %s:\n%s" % (dummy, path_stat))
    dummy_fd = open(dummy, "r")
    verify_text = dummy_fd.read()
    dummy_fd.close()
    print("verify correct contents: %s" % (dummy_text == verify_text))
    trunc_len = 42
    print("truncate handle %s to %db" % (dummy, trunc_len))
    attr = sftp.stat(dummy)
    print("current size is %db" % attr.st_size)
    dummy_fd = sftp.file(dummy, 'r+b')
    dummy_fd.truncate(trunc_len)
    dummy_fd.close()
    attr = sftp.stat(dummy)
    print("verify truncated %s to %d: %s" % (dummy, trunc_len,
                                             (attr.st_size == trunc_len)))
    trunc_len = 4
    print("truncate path %s to %db" % (dummy, trunc_len))
    attr = sftp.stat(dummy)
    print("current size is %db" % attr.st_size)
    sftp.truncate(dummy, trunc_len)
    attr = sftp.stat(dummy)
    print("verify truncated %s to %d: %s" % (dummy, trunc_len,
                                             (attr.st_size == trunc_len)))
    print("delete dummy in %s" % dummy)
    os.remove(dummy)

    # Clean up before exit ###

    sftp.close()
    ssh.close()
