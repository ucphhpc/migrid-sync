#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# generateconfs - create custom MiG server configuration files
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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
        'base_fqdn',
        'public_fqdn',
        'cert_fqdn',
        'oid_fqdn',
        'sid_fqdn',
        'user',
        'group',
        'apache_version',
        'apache_etc',
        'apache_run',
        'apache_lock',
        'apache_log',
        'mig_code',
        'mig_state',
        'mig_certs',
        'enable_sftp',
        'enable_davs',
        'enable_ftps',
        'enable_wsgi',
        'enable_sandboxes',
        'enable_vmachines',
        'enable_freeze',
        'enable_hsts',
        'enable_vhost_certs',
        'enable_seafile',
        'enable_imnotify',
        'enable_dev_accounts',
        'enable_openid',
        'openid_providers',
        'daemon_keycert',
        'daemon_pubkey',
        'daemon_show_address',
        'alias_field',
        'signup_methods',
        'login_methods',
        'hg_path',
        'hgweb_scripts',
        'trac_admin_path',
        'trac_ini_path',
        'public_port',
        'cert_port',
        'oid_port',
        'sid_port',
        'user_clause',
        'group_clause',
        'listen_clause',
        'serveralias_clause',
        'distro',
        'landing_page',
        'skin',
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
        # Remove default values to use generate_confs default values
        if val == 'DEFAULT':
            del settings[key]
    conf = generate_confs(**settings)
    #print "DEBUG: %s" % conf
    print '''Configurations for MiG and Apache were generated in
%(destination)s/
For a default setup you will probably want to copy the MiG daemon conf to the
server code directory:
cp %(destination)s/MiGserver.conf %(mig_code)s/server/
the static skin stylesheet to the styling directory:
cp %(destination)s/static-skin.css %(mig_code)s/images/
and the default landing page to the user_home directory:
cp %(destination)s/index.html %(mig_state)s/user_home/

If you are running apache 2.x on Debian/Ubuntu you can use the sites-available
and sites-enabled structure with:
sudo cp %(destination)s/MiG.conf %(apache_etc)s/sites-available/
sudo a2ensite MiG

On other distro and apache combinations you will likely want to rely on the
automatic inclusion of configurations in the conf.d directory instead:
sudo cp %(destination)s/MiG.conf %(apache_etc)s/conf.d/
and on Redhat based systems possibly mimic Debian with
sudo cp %(destination)s/mimic-deb.conf %(apache_etc)s/conf/httpd.conf
sudo cp %(destination)s/envvars /etc/sysconfig/httpd

You may also want to consider copying the generated apache2.conf,
httpd.conf, ports.conf and envvars to %(apache_etc)s/:
sudo cp %(destination)s/apache2.conf %(apache_etc)s/
sudo cp %(destination)s/httpd.conf %(apache_etc)s/
sudo cp %(destination)s/ports.conf %(apache_etc)s/
sudo cp %(destination)s/envvars %(apache_etc)s/

and if Trac is enabled, the generated trac.ini to %(mig_code)s/server/:
cp %(destination)s/trac.ini %(mig_code)s/server/

On a Debian/Ubuntu MiG developer server the dedicated apache init script is
added with:
sudo cp %(destination)s/apache-%(user)s /etc/init.d/apache-%(user)s

Please reload or restart your apache daemons afterwards to catch the
configuration changes.

The migrid-init.d-rh contains a standard SysV init style helper script to
launch all MiG daemons. It was written for RHEL/CentOS but may work
on other platforms, too.
You can install it with:
sudo cp %(destination)s/migrid-init.d-rh /etc/init.d/migrid

The migrid-init.d-deb contains a standard SysV init style helper script to
launch all MiG daemons. It was written for Debian/Ubuntu but may work
on other platforms, too.
You can install it with:
sudo cp %(destination)s/migrid-init.d-deb /etc/init.d/migrid

The logrotate-mig contains a logrotate configuration to automatically
rotate and compress log files for all MiG daemons.
You can install it with:
sudo cp %(destination)s/logrotate-migrid /etc/logrotate.d/migrid
''' % conf
    sys.exit(0)
