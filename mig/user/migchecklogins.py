#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migchecklogins - simple script to check all IO logins are functional
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

"""Simple helper script to check that all the MiG IO services are running and
functional. Just runs a a series of simple commands to login and do very basic
operations to make sure everything is alright.

Run with:
python migchecklogins.py [OPTIONS]

where OPTIONSallows overriding things like server fqdn, the username and
password. You will be interactively prompted for login if it is not provided
on the command line.

Please check the global configuration section below if it fails. The comments
should help you tweak the configuration to solve most common problems.
"""

import getopt
import getpass
import os
import subprocess
import sys

def usage(name='migchecklogins.py'):
    """Usage help"""

    print """Run a series of IO service logins.
Usage:
%(name)s [OPTIONS]
Where OPTIONS may be one or more of:
   -a METHOD           Auth method (password or key)
   -h                  Show this help
   -p PASSWORD         Password to login with (set on Settings page)
   -s SERVER           Server FQDN to contact
   -u USER             Username to login as (email from Settings page)
   -v                  Verbose output

Each search value can be a string or a pattern with * and ? as wildcards.
""" % {'name': name}


if '__main__' == __name__:
    sftp_path = 'sftp'
    server_fqdn = 'dk-io.migrid.org'
    server_port = 22
    user_auth = 'password'
    user_name = ''
    user_key = None
    user_pw = ''
    verbose = False
    opt_args = 'a:hp:s:u:v'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opt_args)
    except getopt.GetoptError, err:
        print 'Error: ', err.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-a':
            user_auth = val.strip()
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-p':
            user_pw = val
        elif opt == '-s':
            server_fqdn = val.strip()
        elif opt == '-u':
            user_name = val.strip()
        elif opt == '-v':
            verbose = True
        else:
            print 'Error: %s not supported!' % opt
            usage()
            sys.exit(1)

    if args:
        print 'Error: non-option arguments are not supported!'
        usage()
        sys.exit(1)

    if user_auth.lower() == 'password' and not user_pw:
        user_pw = getpass.getpass()
    elif user_auth.lower() == 'agent':
        user_key = None
    else:
        user_key = user_auth
        user_pw = getpass.getpass()

    sftp_cmd = [sftp_path]
    if user_name:
        sftp_cmd.append('-oUser=%s' % user_name)
    if user_auth == 'password':
        sftp_cmd.append('-oPasswordAuthentication=yes')
        sftp_cmd.append('-oPubkeyAuthentication=no')
    else:
        sftp_cmd.append('-oPasswordAuthentication=no')
        sftp_cmd.append('-oPubkeyAuthentication=yes')
    if user_key is not None:
        sftp_cmd.append('-oIdentityFile=%s' % user_key)
        
    # Add host keys to tmp file without asking
    sftp_cmd.append('-oStrictHostKeyChecking=no')
    sftp_cmd.append('-oUserKnownHostsFile=/tmp/dummy-known_hosts')
    
    sftp_cmd.append(server_fqdn)
    print "Running %s" % sftp_cmd
    sftp_proc = subprocess.Popen(sftp_cmd, shell=False,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if user_pw:
        print "sending password"
        sftp_proc.communicate(input='%s' % user_pw)
    print "communicate"
    sftp_proc.communicate()
    print "wait"
    sftp_proc.wait()
    print "sftp login returned %d" % sftp_proc.returncode
    sys.exit(0)
