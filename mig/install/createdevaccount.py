#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createdevaccount - create a MiG server development account
# Copyright (C) 2003-2012  The MiG Project lead by Brian Vinter
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

# IMPORTANT: Run script with sudo or as root

"""Add a unprivileged user with access to a personal MiG server.
Still needs some semi-automated setup of apache, sudo and iptables
afterwards...

This is very much bound to the exact setup used on the main MiG servers
where things like remote login, firewalling, home dirs and sudo are set up
for separated developer accounts. Some paths like for apache and moin moin is
similarly hard coded to the Debian defaults on those servers.
"""

import getopt
import os
import socket
import sys

from shared.install import create_user

def usage(options):
    """Usage help"""
    lines = ["--%s=%s" % pair for pair in zip(options,
                                              [i.upper() for i in options])]
    print '''Usage:
%s [OPTIONS] LOGIN [LOGIN ...]
Create developer account with username LOGIN using OPTIONS.
Where supported options include -h/--help for this help or the conf settings:
%s

IMPORTANT: needs to run with privileges to create system user!
''' % (sys.argv[0], '\n'.join(lines))

if __name__ == '__main__':
    settings = {
        'public_fqdn': socket.getfqdn(),
        'cert_fqdn': socket.getfqdn(),
        'sid_fqdn': socket.getfqdn(),
        'debug_mode': True,
        }
    flag_str = 'h'
    opts_str = ["%s=" % key for key in settings.keys()] + ["help"]
    
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], flag_str, opts_str)
    except getopt.GetoptError, exc:
        print 'Error: ', exc.msg
        usage(settings)
        sys.exit(1)

    for (opt, val) in opts:
        opt_name = opt.lstrip('-')
        if opt in ('-h', '--help'):
            usage(settings)
            sys.exit(0)
        elif opt_name in settings.keys():
            settings[opt_name] = val
        else:
            print 'Error: %s not supported!' % opt
            usage(settings)
            sys.exit(1)

    if not args:
        usage(settings)
        sys.exit(1)

    if os.getuid() > 0:
        print "WARNING: needs to run with user management privileges!"

    print '# Creating dev account with:'
    for (key, val) in settings.items():
        print '%s: %s' % (key, val)
    for login in args:
        print '# Creating a unprivileged account for %s' % login
        create_user(login, login, debug=settings["debug_mode"],
                    public_fqdn=settings["public_fqdn"],
                    cert_fqdn=settings["cert_fqdn"],
                    sid_fqdn=settings["sid_fqdn"])

    sys.exit(0)
