#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# generateconfs - create custom MiG server configuration files
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

import sys
import os
import re
import getopt


def usage(options):
    lines = ["--%s=%s" % pair for pair in zip(options,
                                              [i.upper() for i in options])]
    print '''Usage:
%s [OPTIONS]
Where supported options include -h/--help for this help or the conf settings:
%s
''' % (sys.argv[0], '\n'.join(lines))


def fill_template(template_file, output_file, settings):
    """Fill a configuration template using provided settings dictionary"""
    try:
        template = open(template_file, 'r')
        contents = template.read()
        template.close()
    except Exception, err:
        print 'Error: reading template file %s: %s' % (template_file,
                err)
        return False

    # print "template read:\n", output

    for (variable, value) in settings.items():
        contents = re.sub(variable, value, contents)

    # print "output:\n", contents

    # print "writing specific contents to %s" % (output_file)

    try:
        output = open(output_file, 'w')
        output.write(contents)
        output.close()
    except Exception, err:
        print 'Error: writing output file %s: %s' % (output_file, err)
        return False

    return True


def generate_confs(
    source=os.path.dirname(sys.argv[0]),
    destination=os.path.dirname(sys.argv[0]),
    server_fqdn='localhost',
    user='mig',
    group='mig',
    apache_etc='/etc/apache2',
    apache_run='/var/run',
    apache_log='/var/log/apache2',
    mig_code='/home/mig/mig',
    mig_state='/home/mig/state',
    mig_certs='/home/mig/certs',
    moin_etc='/etc/moin',
    moin_share='/usr/share/moin',
    http_port=80,
    https_port=443,
    user_clause='User',
    group_clause='Group',
    listen_clause='#Listen',
    ):
    """Generate Apache and MiG server confs with specified variables"""

    user_dict = {}
    user_dict['__SERVER_FQDN__'] = server_fqdn
    user_dict['__USER__'] = user
    user_dict['__GROUP__'] = group
    user_dict['__HTTP_PORT__'] = str(http_port)
    user_dict['__HTTPS_PORT__'] = str(https_port)
    user_dict['__MIG_HOME__'] = mig_code
    user_dict['__MIG_STATE__'] = mig_state
    user_dict['__MIG_CERTS__'] = mig_certs
    user_dict['__APACHE_ETC__'] = apache_etc
    user_dict['__APACHE_RUN__'] = apache_run
    user_dict['__APACHE_LOG__'] = apache_log
    user_dict['__MOIN_ETC__'] = moin_etc
    user_dict['__MOIN_SHARE__'] = moin_share
    user_dict['__USER_CLAUSE__'] = user_clause
    user_dict['__GROUP_CLAUSE__'] = group_clause
    user_dict['__LISTEN_CLAUSE__'] = listen_clause

    try:
        os.makedirs(destination)
    except OSError:
        pass

    apache_envs_template = os.path.join(source,
            'apache-envs-template.conf')
    apache_envs_conf = os.path.join(destination, 'envvars')
    fill_template(apache_envs_template, apache_envs_conf, user_dict)
    apache_apache2_template = os.path.join(source,
                                         'apache-apache2-template.conf')
    apache_apache2_conf = os.path.join(destination, 'apache2.conf')
    fill_template(apache_apache2_template, apache_apache2_conf, user_dict)
    apache_httpd_template = os.path.join(source,
                                         'apache-httpd-template.conf')
    apache_httpd_conf = os.path.join(destination, 'httpd.conf')
    fill_template(apache_httpd_template, apache_httpd_conf, user_dict)
    apache_ports_template = os.path.join(source,
                                         'apache-ports-template.conf')
    apache_ports_conf = os.path.join(destination, 'ports.conf')
    fill_template(apache_ports_template, apache_ports_conf, user_dict)
    apache_mig_template = os.path.join(source,
            'apache-MiG-template.conf')
    apache_mig_conf = os.path.join(destination, 'MiG.conf')
    fill_template(apache_mig_template, apache_mig_conf, user_dict)
    apache_initd_template = os.path.join(source,
            'apache-init.d-template')
    apache_initd_script = os.path.join(destination, 'apache-%s' % user)
    fill_template(apache_initd_template, apache_initd_script, user_dict)
    os.chmod(apache_initd_script, 0755)

    server_template = os.path.join(source, 'MiGserver-template.conf')
    server_conf = os.path.join(destination, 'MiGserver.conf')
    fill_template(server_template, server_conf, user_dict)

    return True


if '__main__' == __name__:

    # ## Main ###

    names = (
        'source',
        'destination',
        'server_fqdn',
        'user',
        'group',
        'apache_etc',
        'apache_run',
        'apache_log',
        'mig_code',
        'mig_state',
        'mig_certs',
        'moin_etc',
        'moin_share',
        'http_port',
        'https_port',
        'user_clause',
        'group_clause',
        'listen_clause',
        )
    settings = {}

    flag_str = 'h'
    opts_str = ["%s=" % i for i in names] + ["help"]
    
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

    full_settings = {}
    for i in names:
        full_settings[i] = 'DEFAULT'
    full_settings.update(settings)

    print '''# Creating confs with:
source: %(source)s
destination: %(destination)s
server_fqdn: %(server_fqdn)s
user: %(user)s
group: %(group)s
apache_etc: %(apache_etc)s
apache_run: %(apache_run)s
apache_log: %(apache_log)s
mig_code: %(mig_code)s
mig_state: %(mig_state)s
mig_certs: %(mig_certs)s
moin_etc: %(moin_etc)s
moin_share: %(moin_share)s
http_port: %(http_port)s
https_port: %(https_port)s
user_clause: %(user_clause)s
group_clause: %(group_clause)s
listen_clause: %(listen_clause)s
'''\
         % full_settings
    generate_confs(**settings)

    print '''Configurations for MiG and Apache were generated in %(destination)s/
For a default setup you will probably want to copy the MiG daemon conf to the server code directory:
cp %(destination)s/MiGserver.conf %(mig_code)s/server/

If you are running apache 2.x on Debian you can use the sites-available and sites-enabled structure with:
cp %(destination)s/MiG.conf %(apache_etc)s/sites-available/MiG
a2ensite MiG

On other distro and apache combinations you will likely want to rely on the automatic inclusion of configurations in the conf.d directory instead:
cp %(destination)s/MiG.conf %(apache_etc)s/conf.d/

You may also want to consider copying the generated apache2.conf,
httpd.conf and envvars to %(apache_etc)s/:
cp %(destination)s/apache2.conf %(apache_etc)s/
cp %(destination)s/httpd.conf %(apache_etc)s/
cp %(destination)s/envvars %(apache_etc)s/

On a MiG developer server the dedicated apache init script is added with:
cp %(destination)s/apache-%(user)s /etc/init.d/apache-%(user)s

Please reload or restart your apache daemons to catch the configuration changes.'''\
         % full_settings

    sys.exit(0)
