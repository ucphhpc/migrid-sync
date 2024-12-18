#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# generateconfs - create custom MiG server configuration files
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

from builtins import zip
import datetime
import getopt
import os
import sys

# Ensure that the generateconfs.py script is able to execute from a fresh
# checkout when the cwd is not the parent directory where it was checked out.
# Solve this by ensuring that the chckout is part of the sys.path

# NOTE: __file__ is /MIG_BASE/mig/install/generateconfs.py and we need MIG_BASE
dirname = os.path.dirname
sys.path.append(dirname(dirname(dirname(os.path.abspath(__file__)))))

# NOTE: moved mig imports into try/except to avoid autopep8 moving to top!
try:
    from mig.shared.defaults import MIG_BASE, MIG_ENV
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


def main(argv, _generate_confs=generate_confs, _print=print):
    str_names = [
        'source',
        'destination',
        'destination_suffix',
        'auto_add_filter_fields',
        'auto_add_filter_method',
        'auto_add_user_permit',
        'auto_add_user_with_peer',
        'base_fqdn',
        'public_fqdn',
        'public_alias_fqdn',
        'public_sec_fqdn',
        'mig_cert_fqdn',
        'ext_cert_fqdn',
        'mig_oid_fqdn',
        'ext_oid_fqdn',
        'mig_oidc_fqdn',
        'ext_oidc_fqdn',
        'sid_fqdn',
        'io_fqdn',
        'cert_fqdn_extras',
        'seafile_fqdn',
        'seafile_base',
        'seafmedia_base',
        'seafhttp_base',
        'openid_address',
        'sftp_address',
        'sftp_subsys_address',
        'ftps_address',
        'ftps_pasv_ports',
        'davs_address',
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
        'mig_oid_title',
        'mig_oid_provider',
        'ext_oid_title',
        'ext_oid_provider',
        'mig_oidc_title',
        'mig_oidc_provider_meta_url',
        'ext_oidc_title',
        'ext_oidc_provider_meta_url',
        'ext_oidc_provider_issuer',
        'ext_oidc_provider_authorization_endpoint',
        'ext_oidc_provider_verify_cert_files',
        'ext_oidc_provider_token_endpoint',
        'ext_oidc_provider_token_endpoint_auth',
        'ext_oidc_provider_user_info_endpoint',
        'ext_oidc_scope',
        'ext_oidc_user_info_token_method',
        'ext_oidc_public_key_files',
        'ext_oidc_private_key_files',
        'ext_oidc_response_type',
        'ext_oidc_response_mode',
        'ext_oidc_client_id',
        'ext_oidc_client_name',
        'ext_oidc_pkce_method',
        'ext_oidc_id_token_encrypted_response_alg',
        'ext_oidc_id_token_encrypted_response_enc',
        'ext_oidc_user_info_signed_response_alg',
        'ext_oidc_cookie_same_site',
        'ext_oidc_pass_cookies',
        'ext_oidc_remote_user_claim',
        'ext_oidc_pass_claim_as',
        'ext_oidc_rewrite_cookie',
        'dhparams_path',
        'daemon_keycert',
        'daemon_pubkey',
        'daemon_show_address',
        'alias_field',
        'peers_permit',
        'vgrid_creators',
        'vgrid_managers',
        'signup_methods',
        'login_methods',
        'digest_salt',
        'crypto_salt',
        'csrf_protection',
        'password_policy',
        'password_legacy_policy',
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
        'title',
        'short_title',
        'extra_userpage_scripts',
        'extra_userpage_styles',
        'peers_explicit_fields',
        'peers_contact_hint',
        'external_doc',
        'secscan_addr',
        'user_interface',
        'vgrid_label',
        'default_menu',
        'user_menu',
        'collaboration_links',
        'default_vgrid_links',
        'advanced_vgrid_links',
        'support_email',
        'admin_email',
        'admin_list',
        'smtp_server',
        'smtp_sender',
        'log_level',
        'twofactor_mandatory_protos',
        'twofactor_auth_apps',
        'permanent_freeze',
        'freeze_to_tape',
        'status_system_match',
        'storage_protocols',
        'duplicati_protocols',
        'imnotify_address',
        'imnotify_channel',
        'imnotify_username',
        'imnotify_password',
        'gdp_data_categories',
        'gdp_id_scramble',
        'gdp_path_scramble',
        'quota_backend',
        'ca_fqdn',
        'ca_user',
        'ca_smtp',
        'datasafety_link',
        'datasafety_text',
    ]
    int_names = [
        'cert_valid_days',
        'oid_valid_days',
        'oidc_valid_days',
        'generic_valid_days',
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
        'mig_oidc_port',
        'ext_oidc_port',
        'sid_port',
        'sftp_port',
        'sftp_show_port',
        'sftp_subsys_port',
        'sftp_subsys_show_port',
        'sftp_max_sessions',
        'davs_port',
        'davs_show_port',
        'ftps_ctrl_port',
        'ftps_ctrl_show_port',
        'openid_port',
        'openid_show_port',
        'openid_session_lifetime',
        'seafile_seahub_port',
        'seafile_seafhttp_port',
        'seafile_client_port',
        'seafile_quota',
        'quota_user_limit',
        'quota_vgrid_limit',
        'wwwserve_max_bytes',
    ]
    bool_names = [
        'auto_add_cert_user',
        'auto_add_oid_user',
        'auto_add_oidc_user',
        'enable_migadmin',
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
        'enable_quota',
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
        'enable_peers',
        'peers_mandatory',
        'enable_cracklib',
        'enable_openid',
        'enable_gravatars',
        'enable_sitestatus',
        'daemon_pubkey_from_dns',
        'seafile_ro_access',
        'public_use_https',
        'prefer_python3',
        'io_account_expire',
        'gdp_email_notify',
    ]
    names = str_names + int_names + bool_names
    settings, options, result = {}, {}, {}
    default_val = 'DEFAULT'
    # Force values to expected type
    for key in names:
        settings[key] = default_val

    # Apply values from environment - use custom prefix to avoid
    # interference with certain native environments like USER.
    env_prefix = os.getenv("MIG_GENCONF_ENV_PREFIX", 'MIG_')
    for opt_name in names:
        val = os.getenv("%s%s" % (env_prefix, opt_name.upper()))
        if not val:
            # NOTE: Empty text values are not supported in env
            continue
        if opt_name in str_names:
            settings[opt_name] = val
        elif opt_name in int_names and val:
            settings[opt_name] = int(val)
        elif opt_name in bool_names and val:
            settings[opt_name] = (val.strip().lower() in ['1', 'true', 'yes'])
        else:
            _print('Error: environment options %r not supported!' % opt_name)
            usage(names)
            return 1

    # apply values from CLI parameters
    flag_str = 'h'
    opts_str = ["%s=" % key for key in names] + ["help"]
    try:
        (opts, args) = getopt.getopt(argv, flag_str, opts_str)
    except getopt.GetoptError as exc:
        _print('Error: ', exc.msg)
        usage(names)
        return 1

    for (opt, val) in opts:
        opt_name = opt.lstrip('-')
        if opt in ('-h', '--help'):
            usage(names)
            return 0
        elif opt_name in str_names:
            settings[opt_name] = val
        elif opt_name in int_names:
            settings[opt_name] = int(val)
        elif opt_name in bool_names:
            settings[opt_name] = (val.strip().lower() in ['1', 'true', 'yes'])
        else:
            _print('Error: command line option %r not supported!' % opt_name)
            usage(names)
            return 1

    if args:
        _print('Error: non-option arguments are no longer supported!')
        _print(" ... found: %s" % args)
        usage(names)
        return 1
    if settings['destination_suffix'] == 'DEFAULT':
        suffix = "-%s" % datetime.datetime.now().isoformat()
        settings['destination_suffix'] = suffix
    if os.getenv('MIG_ENV', 'default') == 'local':
        output_path = os.path.join(MIG_BASE, 'envhelp/output')
    elif settings['destination'] == 'DEFAULT' or \
            not os.path.isabs(settings['destination']):
        # Default to generate in subdir of CWD ...
        output_path = os.getcwd()
    else:
        # ... but use verbatim passthrough for absolute destination
        output_path = settings['destination']
    _print('# Creating confs with:')
    # NOTE: force list to avoid problems with in-line edits
    for (key, val) in list(settings.items()):
        _print('%s: %s' % (key, val))
        # Remove default values to use generate_confs default values
        if val == 'DEFAULT':
            del settings[key]

    (options, result) = _generate_confs(output_path, **settings)

    # TODO: avoid reconstructing this path (also done inside generate_confs)
    instructions_path = os.path.join(options['destination_dir'],
                                     'instructions.txt')
    try:
        instructions_fd = open(instructions_path, "r")
        instructions = instructions_fd.read()
        instructions_fd.close()
        _print(instructions)
    except Exception as exc:
        _print("ERROR: could not read generated instructions: %s" % exc)
        return 1
    return 0


if '__main__' == __name__:
    exit_code = main(sys.argv[1:])
    sys.exit(exit_code)
