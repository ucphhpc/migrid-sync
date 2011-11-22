#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migsftp - simple sftp client
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""Test python+paramiko sftp against MiG server"""

import os
import sys
import paramiko

print "Please enter the looong username from your MiG ssh settings page"
user = raw_input('Username: ')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy())
ssh.connect('dk-cert.migrid.org', username=user, port=2222)
ftp = ssh.open_sftp()
base = '.ssh'
files = ftp.listdir(base)
path_stat = ftp.stat(base)
print "stat %s:\n%s" % (base, path_stat)
print "files in %s dir:\n%s" % (base, files)
for name in files:
    rel_path = os.path.join(base, name)
    path_stat = ftp.stat(rel_path)
    print "stat %s:\n%s" % (rel_path, path_stat)
ftp.close()
