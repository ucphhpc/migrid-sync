#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migsftpaccess - paramiko-based sftp client for checking access limits
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

"""A Paramiko-based sftp client for checking access limits in MiG.

Requires paramiko (http://pypi.python.org/pypi/paramiko) and thus PyCrypto
(http://pypi.python.org/pypi/pycrypto).

Run with:
python migsftpaccess.py [SERVER_ADDRESS] [SERVER_PORT] [USER] [AUTH]

where the optional SERVER_ADDRESS, SERVER_PORT can be used to point the checks
at a specific server. USER and AUTH are used to specificy your user credentials
in the form of a user or sharelink ID and the authentication method.
The latter can be 'password', 'agent' or the path to your ssh key. Use 'agent'
to try any keys available from a running ssh-agent.
You will be prompted for a password if not provided on the command line.

Please check the global configuration section below if it fails. The comments
should help you tweak the configuration to solve most common problems.

"""
from __future__ import print_function

import base64
import getpass
import os
import sys
import paramiko


# Global configuration ###

server_fqdn = 'dk-sid.migrid.org'
server_port = 22
# This is the current migrid.org key - but we default to auto for flexibility
# server_host_key = "ssh-rsa
# AAAAB3NzaC1yc2EAAAADAQABAAABAQDSmsGNpTnmOhIhLk+RtOxE+YL+rP77mbJ7os0JZpiId1U2jHkNqNEBr8DpmtkAyWn8DvJf4GtLkykVxysnBqj0fnI4nTOJpYtNT/0cw2IKKf0j5zjRzTzB/Jh1rb5OQKad4U31P8Z4sEHFS3kk4r7Ls2C/Sm8adUMt1SDW4G7TqlSgsq97uWOlCYLb0x0BQNuvjurLZpQCCkz0GIFlGXOKkwEZrhcD8vmAzjRUEbv7YyEwNr442HOJ7DtG/3Q+Zwe0UPojOYackvCKX2itrBA5Ko5eENiOCYXxIXHoVRAbDgGwL8hHHGjpKvIA/yivSB0UP7uMKf4QWz3Ax9HQdQUR"
server_host_key = 'AUTO'
known_hosts_path = os.path.expanduser("~/.ssh/known_hosts")
user_auth = 'password'
user_key = None
user_pw = ''
host_key_policy = paramiko.RejectPolicy()
data_compression = True
# Uncomment the next line if don't want compressed transfers. This is a trade
# off between CPU usage and throughput
# data_compression = False


def test_file_access(sftp, test_path, dummy_file):
    """Run remote sftp access tests on file in test_path using local
    dummy_file as input where needed.
    """
    try:
        path_stat = sftp.stat(test_path)
        print("stat %s:\n%s" % (test_path, path_stat))
    except Exception as exc:
        print("stat on %s failed: %s" % (test_path, exc))
    try:
        path_chmod = sftp.chmod(test_path, 0o2777)
        print("chmod %s:\n%s" % (test_path, path_chmod))
    except Exception as exc:
        print("chmod on %s failed: %s" % (test_path, exc))
    try:
        path_chown = sftp.chown(test_path, 0, 0)
        print("chown %s:\n%s" % (test_path, path_chown))
    except Exception as exc:
        print("chown on %s failed: %s" % (test_path, exc))
    try:
        sftp.put(dummy_file, test_path)
        print("put dummy into %s succeeded!" % test_path)
    except Exception as exc:
        print("put dummy into %s failed: %s" % (test_path, exc))
    block_size = 1024
    try:
        path_fd = sftp.file(test_path)
        path_md5_digest = path_fd.check("md5", block_size=block_size)
        path_sha1_digest = path_fd.check("sha1", block_size=block_size)
        path_fd.close()
        print("remote md5 sum %s:\n%s" % (test_path, path_md5_digest.encode('hex')))
        print("remote sha1 sum %s:\n%s" % (test_path, path_sha1_digest.encode('hex')))
    except Exception as exc:
        print("checksum %s failed: %s" % (test_path, exc))
    try:
        sftp.get(test_path, dummy_file)
        print("download %s succeeded!" % test_path)
    except Exception as exc:
        print("download %s failed: %s" % (test_path, exc))
    try:
        sftp.symlink(test_path, 'illegal-symlink')
        print("symlink %s succeeded!" % test_path)
    except Exception as exc:
        print("symlink %s failed: %s" % (test_path, exc))
    trunc_len = 4
    try:
        path_fd = sftp.file(test_path)
        path_fd.truncate(trunc_len)
        path_fd.close()
        print("open+truncate %s succeeded!" % test_path)
    except Exception as exc:
        print("open+truncate %s failed: %s" % (test_path, exc))
    try:
        sftp.truncate(test_path, trunc_len)
        print("direct truncate %s succeeded!" % test_path)
    except Exception as exc:
        print("direct truncate %s failed: %s" % (test_path, exc))
    try:
        sftp.remove(test_path)
        print("remove %s succeeded!" % test_path)
    except Exception as exc:
        print("remove %s failed: %s" % (test_path, exc))


def test_dir_access(sftp, test_path, dummy_file):
    """Run remote sftp access tests on directory in test_path using local
    dummy_file as input where needed.
    """
    show_limit = 4
    try:
        files = sftp.listdir(test_path)
        print("first %d entries in %s dir:\n%s" % (show_limit, test_path, files))
        for name in files[:show_limit]:
            rel_path = os.path.join(test_path, name)
            path_stat = sftp.stat(rel_path)
            print("stat %s:\n%s" % (rel_path, path_stat))
    except Exception as exc:
        print("listdir on %s failed: %s" % (test_path, exc))
    try:
        path_stat = sftp.stat(test_path)
        print("stat %s:\n%s" % (test_path, path_stat))
    except Exception as exc:
        print("stat on %s failed: %s" % (test_path, exc))
    try:
        sftp.symlink(test_path, 'illegal-symlink')
        print("symlink %s succeeded!" % test_path)
    except Exception as exc:
        print("symlink %s failed: %s" % (test_path, exc))
    try:
        sftp.put(dummy_file, os.path.join(test_path, "dummy"))
        print("upload to %s succeeded!" % test_path)
    except Exception as exc:
        print("upload to %s failed: %s" % (test_path, exc))
    try:
        sftp.rmdir(test_path)
        print("rmdir %s succeeded!" % test_path)
    except Exception as exc:
        print("rmdir %s failed: %s" % (test_path, exc))


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
        user_auth = sys.argv[4]
    if sys.argv[5:]:
        server_host_key = sys.argv[5]
    if len(user_name) != 10 and user_name.find('@') == -1:
        print("""Warning: the supplied username is not on expected form!
Please verify it on your MiG ssh Settings page in case of failure.""")

    # Connect with provided settings

    ssh = paramiko.SSHClient()
    known_host_keys = ssh.get_host_keys()
    if server_host_key == 'AUTO':
        # For silent operation we can just accept all host keys
        # host_key_policy = paramiko.AutoAddPolicy()
        # Warn about missing host key
        host_key_policy = paramiko.WarningPolicy()
    else:
        key_type, key_data = server_host_key.split(' ')[:2]
        pub_key = paramiko.RSAKey(data=base64.b64decode(key_data))
        # Add host key both on implicit and explicit port format
        server_fqdn_port = "[%s]:%d" % (server_fqdn, server_port)
        known_host_keys.add(server_fqdn, key_type, pub_key)
        known_host_keys.add(server_fqdn_port, key_type, pub_key)
    known_host_keys.load(known_hosts_path)
    ssh.set_missing_host_key_policy(host_key_policy)
    if user_auth.lower() == 'password':
        user_pw = getpass.getpass()
    elif user_auth.lower() == 'agent':
        user_key = None
    else:
        user_key = user_auth
        user_pw = getpass.getpass()
    ssh.connect(server_fqdn, username=user_name, port=server_port,
                password=user_pw, key_filename=user_key,
                compress=data_compression)
    sftp = ssh.open_sftp()

    # Run a series of possibly restricted operations in MiG home ###

    # List, stat, read and write files in the remote home
    # most of which should be chrooted out or at least forced in-bounds

    file_targets = ['.htaccess', '../../../mig/server/MiGserver.conf',
                    '../vinter@nbi.ku.dk/welcome.txt',
                    'eScience/.vgridscm/cgi-bin/hgweb.cgi',
                    '../../vgrid_files_home/BINF/README', '/etc/hosts',
                    '../../../../../etc/hosts']
    dir_targets = ['../', '/etc/', '/home/mig/state/user_home/',
                   '../vinter@nbi.ku.dk/', 'eScience/.vgridscm/cgi-bin/',
                   '../../vgrid_files_home/', '../../../../../etc/']

    # Uncomment to limit targets while developing/debugging
    # file_targets = file_targets[:1]
    # dir_targets = dir_targets[:1]

    print("= Running access tests against %s:%s as %s =" % (server_fqdn,
                                                            server_port,
                                                            user_name))

    dummy_path = 'this-is-a-migsftp-dummy-file.txt'
    dummy_text = "sample file\ncontents from client\n"
    # print "create local dummy file in %s" % dummy_path
    dummy_fd = open(dummy_path, "w")
    dummy_fd.write(dummy_text)
    dummy_fd.close()
    # path_stat = os.stat(dummy_path)
    # print "local stat %s:\n%s" % (dummy_path, path_stat)

    print("= Running file access tests =")
    for target in file_targets:
        test_file_access(sftp, target, dummy_path)

    print("= Running directory access tests =")
    for target in dir_targets:
        test_dir_access(sftp, target, dummy_path)

    print("= Clean up before exit =")

    os.remove(dummy_path)

    sftp.close()
    ssh.close()
