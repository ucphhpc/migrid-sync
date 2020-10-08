#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# generateconfs - create custom MiG server configuration files
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
from __future__ import print_function

import datetime
import getopt
import os
import sys

# Ensure that the generateconfs.py script is able to execute from a fresh
# checkout when the cwd is not the parent directory where it was checked out.
# Solve this by ensuring that the chckout is part of the sys.path

# NOTE: __file__ is /MIG_BASE/mig/install/generateconfs.py and we need MIG_BASE

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# NOTE: moved mig imports into try/except to avoid autopep8 moving to top!
try:
    from mig.shared.install import generate_confs
except ImportError:
    print("ERROR: the migrid modules must be in PYTHONPATH")
    sys.exit(1)


def usage(options):
    """Usage help"""
    lines = ["--%s=%s" % pair for pair in zip(options,
                                              [i.upper() for i in options])]
    print('''Usage:
%s [OPTIONS]
Where supported options include -h/--help for this help or the conf settings:
%s
''' % (sys.argv[0], '\n'.join(lines)))


if '__main__' == __name__:
    str_names = [
        'source',
        'destination',
        'destination_suffix',
        'base_fqdn',
        'public_fqdn',
        'public_alias_fqdn',
        'mig_cert_fqdn',
        'ext_cert_fqdn',
        'mig_oid_fqdn',
        'ext_oid_fqdn',
        'sid_fqdn',
        'io_fqdn',
        'seafile_fqdn',
        'seafile_base',
        'seafmedia_base',
        'seafhttp_base',
        'jupyter_services',
        'jupyter_services_desc',
        'cloud_fqdn',
        'cloud_services',
        'cloud_services_desc',
        'user',
        'group',
        'apache_version',
        'apache_etc',
        'apache_run',
        'apache_lock',
        'apache_log',
        'openssh_version',
        'mig_code',
        'mig_state',
        'mig_certs',
        'mig_oid_provider',
        'ext_oid_provider',
        'dhparams_path',
        'daemon_keycert',
        'daemon_pubkey',
        'daemon_show_address',
        'alias_field',
        'signup_methods',
        'login_methods',
        'csrf_protection',
        'password_policy',
        'hg_path',
        'hgweb_scripts',
        'trac_admin_path',
        'trac_ini_path',
        'user_clause',
        'group_clause',
        'listen_clause',
        'serveralias_clause',
        'distro',
        'autolaunch_page',
        'landing_page',
        'skin',
        'short_title',
        'secscan_addr',
        'user_interface',
        'vgrid_label',
    ]
    int_names = [
        'apache_worker_procs',
        'sftp_subsys_auth_procs',
        'wsgi_procs',
        'public_port',
        'public_http_port',
        'public_https_port',
        'mig_cert_port',
        'ext_cert_port',
        'mig_oid_port',
        'ext_oid_port',
        'sid_port',
        'sftp_port',
        'sftp_show_port',
        'sftp_subsys_port',
        'sftp_subsys_show_port',
        'davs_port',
        'davs_show_port',
        'ftps_ctrl_port',
        'ftps_ctrl_show_port',
        'openid_port',
        'openid_show_port',
        'seafile_seahub_port',
        'seafile_seafhttp_port',
        'seafile_client_port',
        'seafile_quota',
    ]
    bool_names = [
        'enable_sftp',
        'enable_sftp_subsys',
        'enable_davs',
        'enable_ftps',
        'enable_wsgi',
        'enable_jobs',
        'enable_resources',
        'enable_workflows',
        'enable_events',
        'enable_sharelinks',
        'enable_transfers',
        'enable_freeze',
        'enable_sandboxes',
        'enable_vmachines',
        'enable_preview',
        'enable_jupyter',
        'enable_cloud',
        'enable_gdp',
        'enable_hsts',
        'enable_vhost_certs',
        'enable_verify_certs',
        'enable_seafile',
        'enable_duplicati',
        'enable_crontab',
        'enable_notify',
        'enable_imnotify',
        'enable_dev_accounts',
        'enable_twofactor',
        'enable_twofactor_strict_address',
        'enable_cracklib',
        'enable_openid',
        'enable_gravatars',
        'enable_sitestatus',
        'daemon_pubkey_from_dns',
        'seafile_ro_access',
        'public_use_https',
    ]
    names = str_names + int_names + bool_names
    settings = {}
    default_val = 'DEFAULT'
    # Force values to expected type
    for key in names:
        settings[key] = default_val

    flag_str = 'h'
    opts_str = ["%s=" % key for key in names] + ["help"]
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], flag_str, opts_str)
    except getopt.GetoptError as exc:
        print('Error: ', exc.msg)
        usage(names)
        sys.exit(1)

    for (opt, val) in opts:
        opt_name = opt.lstrip('-')
        if opt in ('-h', '--help'):
            usage(names)
            sys.exit(0)
        elif opt_name in str_names:
            settings[opt_name] = val
        elif opt_name in int_names:
            settings[opt_name] = int(val)
        elif opt_name in bool_names:
            settings[opt_name] = (val.strip().lower() in ['1', 'true', 'yes'])
        else:
            print('Error: %s not supported!' % opt)
            usage(names)
            sys.exit(1)

    if args:
        print('Error: non-option arguments are no longer supported!')
        print(" ... found: %s" % args)
        usage(names)
        sys.exit(1)
    if settings['destination_suffix'] == 'DEFAULT':
        suffix = "-%s" % datetime.datetime.now().isoformat()
        settings['destination_suffix'] = suffix
    print('# Creating confs with:')
    for (key, val) in settings.items():
        print('%s: %s' % (key, val))
        # Remove default values to use generate_confs default values
        if val == 'DEFAULT':
            del settings[key]
    conf = generate_confs(**settings)
    #print "DEBUG: %s" % conf
    instructions_path = "%(destination)s/instructions.txt" % conf
    try:
        instructions_fd = open(instructions_path, "r")
        instructions = instructions_fd.read()
        instructions_fd.close()
        print(instructions)
    except Exception as exc:
        print("ERROR: could not read generated instructions: %s" % exc)
        sys.exit(1)
    sys.exit(0)
