#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# generateconfs - create custom MiG server configuration files
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

"""Generate the configurations for a custom MiG server installation.
Creates MiG server and Apache configurations to fit the provided settings.
"""

import getopt
import sys

from shared.install import generate_confs

def usage(options):
    """Usage help"""
    lines = ["--%s=%s" % pair for pair in zip(options,
                                              [i.upper() for i in options])]
    print '''Usage:
%s [OPTIONS]
Where supported options include -h/--help for this help or the conf settings:
%s
''' % (sys.argv[0], '\n'.join(lines))


if '__main__' == __name__:
    names = (
        'source',
        'destination',
        'public_fqdn',
        'cert_fqdn',
        'sid_fqdn',
        'user',
        'group',
        'apache_etc',
        'apache_run',
        'apache_lock',
        'apache_log',
        'mig_code',
        'mig_state',
        'mig_certs',
        'enable_sftp',
        'moin_etc',
        'moin_share',
        'hg_path',
        'hgweb_scripts',
        'trac_admin_path',
        'trac_ini_path',
        'public_port',
        'cert_port',
        'sid_port',
        'user_clause',
        'group_clause',
        'listen_clause',
        'serveralias_clause',
        )
    settings = {}
    for key in names:
        settings[key] = 'DEFAULT'

    flag_str = 'h'
    opts_str = ["%s=" % key for key in names] + ["help"]    
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], flag_str, opts_str)
    except getopt.GetoptError, exc:
        print 'Error: ', exc.msg
        usage(names)
        sys.exit(1)

    for (opt, val) in opts:
        opt_name = opt.lstrip('-')
        if opt in ('-h', '--help'):
            usage(names)
            sys.exit(0)
        elif opt_name in names:
            settings[opt_name] = val
        else:
            print 'Error: %s not supported!' % opt
            usage(names)
            sys.exit(1)

    if args:
        print 'Error: non-option arguments are no longer supported!'
        usage(names)
        sys.exit(1)
    print '# Creating confs with:'
    for (key, val) in settings.items():
        print '%s: %s' % (key, val)    
    generate_confs(**settings)
    print '''Configurations for MiG and Apache were generated in
%(destination)s/
For a default setup you will probably want to copy the MiG daemon conf to the
server code directory:
cp %(destination)s/MiGserver.conf %(mig_code)s/server/

If you are running apache 2.x on Debian you can use the sites-available and
sites-enabled structure with:
cp %(destination)s/MiG.conf %(apache_etc)s/sites-available/MiG
a2ensite MiG

On other distro and apache combinations you will likely want to rely on the
automatic inclusion of configurations in the conf.d directory instead:
cp %(destination)s/MiG.conf %(apache_etc)s/conf.d/

You may also want to consider copying the generated apache2.conf,
httpd.conf, ports.conf and envvars to %(apache_etc)s/:
cp %(destination)s/apache2.conf %(apache_etc)s/
cp %(destination)s/httpd.conf %(apache_etc)s/
cp %(destination)s/ports.conf %(apache_etc)s/
cp %(destination)s/envvars %(apache_etc)s/

and the generated trac.ini to %(mig_code)s/server/:
cp %(destination)s/trac.ini %(mig_code)s/server/

On a MiG developer server the dedicated apache init script is added with:
cp %(destination)s/apache-%(user)s /etc/init.d/apache-%(user)s

Please reload or restart your apache daemons to catch the configuration
changes.
''' % settings
    sys.exit(0)
