#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# install - MiG server install helpers
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Install helpers:

Generate the configurations for a custom MiG server installation.
Creates MiG server and Apache configurations to fit the provided settings.

Create MiG developer account with dedicated web server and daemons.
"""

from __future__ import print_function
from __future__ import absolute_import
from past.builtins import basestring

from builtins import zip
from builtins import range
from past.builtins import basestring
import ast
import base64
import grp
import os
import pwd
import re
import subprocess
import sys

from mig.shared.base import force_native_str, force_utf8
from mig.shared.compat import ensure_native_string, inspect_args, \
    SimpleNamespace
from mig.shared.defaults import default_http_port, default_https_port, \
    auth_openid_mig_db, auth_openid_ext_db, MIG_BASE, STRONG_TLS_CIPHERS, \
    STRONG_TLS_CURVES, STRONG_SSH_HOSTKEYALGOS, STRONG_SSH_KEXALGOS, \
    STRONG_SSH_CIPHERS, STRONG_SSH_MACS, LEGACY_SSH_HOSTKEYALGOS, \
    LEGACY_SSH_KEXALGOS, LEGACY_SSH_CIPHERS, LEGACY_SSH_MACS, \
    FALLBACK_SSH_HOSTKEYALGOS, FALLBACK_SSH_KEXALGOS, FALLBACK_SSH_CIPHERS, \
    FALLBACK_SSH_MACS, CRACK_USERNAME_REGEX, CRACK_WEB_REGEX, \
    keyword_any, keyword_auto
from mig.shared.fileio import read_file, read_file_lines, write_file, \
    write_file_lines
from mig.shared.htmlgen import menu_items
from mig.shared.jupyter import gen_balancer_proxy_template, gen_openid_template, \
    gen_rewrite_template
from mig.shared.pwcrypto import password_requirements, make_simple_hash, \
    make_safe_hash
from mig.shared.safeeval import subprocess_call, subprocess_popen, subprocess_pipe
from mig.shared.safeinput import valid_alphanumeric, InputException
from mig.shared.url import urlparse


def _override_apache_initd(template_name, user_dict):
    file_name, _ = os.path.splitext(template_name)
    return "%s-%s" % (file_name, user_dict['__MIG_USER__'])


def abspath(path, start):
    """Return an absolute path as per os.path.abspath() - from an explicit
    starting cwd if necessary.
    """
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(start, path))


def determine_timezone(_environ=os.environ, _path_exists=os.path.exists, _print=print):
    """Attempt to detect the timezone in various known portable ways."""

    sys_timezone = None

    timezone_link = '/etc/localtime'
    timezone_cmd = ["/usr/bin/timedatectl", "status"]

    env_timezone = _environ.get('TZ', None)
    if env_timezone:
        # Use TZ env value directly if set
        return env_timezone

    if _path_exists(timezone_link):
        zoneinfo_absolute = os.path.realpath(timezone_link)
        # Convert /etc/localtime link to e.g. /.../zoneinfo/Europe/Rome
        # then remove leading directories leaving TZ e.g. Europe/Rome
        zoneinfo_path_parts = zoneinfo_absolute.split('/')
        try:
            zoneinfo_index = zoneinfo_path_parts.index('zoneinfo')
            # the last path parts are at least .../zoneinfo/ which
            # is good enough for us here - treat them as the timezone
            localtime_timezone = '/'.join(
                zoneinfo_path_parts[zoneinfo_index + 1:])
            return localtime_timezone
        except IndexError:
            pass
        except ValueError:
            # The attempt to reassemble a timezone string based on searching
            # split path data is brittle and can fail if the locale information
            # happen to be located elsewhere on disk - as is the case on e.g.
            # FreeBSD.
            # Rather than fail hard we catch the exception such that fallback
            # logic below can still run and thus failing to decode the timezone
            # does not prevent the installation routine running to completion.
            pass

        _print("WARNING: ignoring non-standard /etc/localtime")

    if _path_exists(timezone_cmd[0]):
        # Parse Time zone: LOCATION (ALIAS, OFFSET) output of timedatectl
        # into just LOCATION
        try:
            timezone_proc = subprocess_popen(
                timezone_cmd, stdout=subprocess_pipe)
            for line in timezone_proc.stdout.readlines():
                line = ensure_native_string(line.strip())
                if not line.startswith("Time zone: "):
                    continue
                timedatectl_parts = line.replace(
                    "Time zone: ", "").split(" ", 1)
                return timedatectl_parts[0]
        except IndexError:
            pass
        except OSError as exc:
            # warn about any issues executing the command but continue
            _print("WARNING: failed to extract time zone with %s : %s" %
                   (' '.join(timezone_cmd), exc))

    # none of the standard extraction methods succeeded by this point
    _print("WARNING: failed to extract system time zone; defaulting to UTC")
    return 'UTC'


def fill_template(template_file, output_file, settings, eat_trailing_space=[],
                  additional=None):
    """Fill a configuration template using provided settings dictionary"""
    contents = read_file(template_file, None)
    if contents is None:
        print('Error: reading template file %s' % template_file)
        return False

    # print "template read:\n", output

    for (variable, value) in settings.items():
        suffix = ''
        if variable in eat_trailing_space:
            suffix = '\s{0,1}'
        try:
            contents = re.sub(variable + suffix, value, contents)
        except Exception as exc:
            print("Error stripping %s: %s" % (variable, [value]))
            raise exc
    # print "output:\n", contents

    # print "writing specific contents to %s" % (output_file)

    if not write_file(contents, output_file, None):
        print('Error: writing output file %s' % output_file)
        return False
    return True


def template_insert(template_file, insert_identifiers, unique=False):
    """ Insert into a configuration template using provided settings dictionary
    :param template_file: path to the template configuration file that should be
    modified with inserts
    :param insert_identifiers: dictionary, where the keys are used as search strings
    to find the index where the insert should take place. The values can either be a list
    of a single string
    :param unique: Whether the function should check whether the supplied value is
    already present in the template_file, if so it won't insert it
    :return: True/False based on whether an insert took place
    """

    contents = read_file_lines(template_file, None)
    if contents is None:
        print('Error: reading template file %s' % template_file)
        return False

    # print "template read:\n", output
    for (variable, value) in insert_identifiers.items():
        try:
            # identifier index
            f_index = [i for i in range(
                len(contents)) if variable in contents[i]][0]
        except IndexError as err:
            print(
                "Template insert, Identifer: %s not found in %s: %s"
                % (variable, template_file, err))
            return False

        if isinstance(value, basestring):
            if unique and [line for line in contents if value in line]:
                break
            contents.insert(f_index + 1, value)
        elif isinstance(value, list):
            for v in value:
                if unique and [line for line in contents if v in line]:
                    continue
                f_index += 1
                contents.insert(f_index, v)
        elif isinstance(value, dict):
            for k, v in value.items():
                if unique and [line for line in contents if v in line]:
                    continue
                f_index += 1
                contents.insert(f_index, v)
        else:
            print("A non-valid insert identifer dictionary value was supplied, "
                  "supports string and list")
            return False
    if not write_file_lines(contents, template_file, None):
        print('Error: writing output file %s' % template_file)
        return False
    return True


def template_remove(template_file, remove_pattern):
    """
    Removes a line from a template_file based on the supplied remove_pattern.
    :param template_file: Path to the template configuration file that should have a
    pattern removed
    :param remove_pattern: Expects a type that supports an "in" statement condition check
    :return: True/False based on whether the removal was successful.
    """
    contents = read_file_lines(template_file, None)
    if contents is None:
        print('Error: reading template file %s' % template_file)
        return False

    try:
        # identifier indexes
        f_indexes = [i for i in range(
            len(contents)) if remove_pattern in contents[i]]
    except IndexError as err:
        print(
            "Template remove, Identifer: %s not found in %s: %s"
            % (remove_pattern, template_file, err))
        return False

    # Remove in reverse
    for f_i in sorted(f_indexes, reverse=True):
        del contents[f_i]

    if not write_file_lines(contents, template_file, None):
        print('Error: writing output file %s' % template_file)
        return False

    return True


_GENERATE_CONFS_NOFORWARD_KEYS = [
    'generateconfs_output_path',
    'generateconfs_command',
    'source',
    'destination',
    'destination_suffix',
    'group',
    'user',
    'timezone',
    '_getpwnam',
    '_prepare',
    '_writefiles',
    '_instructions',
]


_DEFAULTS = SimpleNamespace(
    base_fqdn='',
    public_fqdn='',
    public_alias_fqdn='',
    status_alias_fqdn='',
    public_sec_fqdn='',
    mig_cert_fqdn='',
    ext_cert_fqdn='',
    mig_oid_fqdn='',
    ext_oid_fqdn='',
    mig_oidc_fqdn='',
    ext_oidc_fqdn='',
    sid_fqdn='',
    io_fqdn='',
    cert_fqdn_extras='',
    cloud_fqdn='',
    seafile_fqdn='',
    seafile_base='/seafile',
    seafmedia_base='/seafmedia',
    seafhttp_base='/seafhttp',
    openid_address='',
    sftp_address='',
    sftp_subsys_address='',
    ftps_address='',
    davs_address='',
    jupyter_services='',
    jupyter_services_desc='{}',
    cloud_services='',
    cloud_services_desc='{}',
    apache_version='2.4',
    apache_etc='/etc/apache2',
    apache_run='/var/run',
    apache_lock='/var/lock',
    apache_log='/var/log/apache2',
    apache_worker_procs=256,
    openssh_version='7.4',
    mig_code=keyword_auto,
    mig_state=keyword_auto,
    mig_certs=keyword_auto,
    auto_add_cert_user=False,
    auto_add_oid_user=False,
    auto_add_oidc_user=False,
    auto_add_filter_fields='',
    auto_add_filter_method='skip',
    auto_add_user_permit='distinguished_name:.*',
    auto_add_user_with_peer='distinguished_name:.*',
    cert_valid_days=365,
    oid_valid_days=365,
    oidc_valid_days=365,
    generic_valid_days=365,
    enable_migadmin=False,
    enable_sftp=False,
    enable_sftp_subsys=False,
    sftp_subsys_auth_procs=10,
    enable_davs=False,
    enable_ftps=False,
    enable_wsgi=True,
    wsgi_procs=10,
    enable_gdp=False,
    enable_jobs=False,
    enable_resources=False,
    enable_workflows=False,
    enable_events=False,
    enable_sharelinks=True,
    enable_transfers=False,
    enable_freeze=True,
    enable_sandboxes=False,
    enable_vmachines=False,
    enable_preview=False,
    enable_jupyter=False,
    enable_cloud=False,
    enable_hsts=True,
    enable_vhost_certs=False,
    enable_verify_certs=False,
    enable_seafile=False,
    enable_duplicati=False,
    enable_crontab=True,
    enable_notify=False,
    enable_imnotify=False,
    enable_dev_accounts=False,
    enable_twofactor=True,
    twofactor_mandatory_protos='',
    enable_twofactor_strict_address=False,
    twofactor_auth_apps='',
    enable_peers=False,
    peers_mandatory=False,
    peers_explicit_fields='',
    peers_contact_hint='employed here and authorized to invite external users',
    enable_cracklib=False,
    enable_openid=False,
    enable_gravatars=False,
    enable_sitestatus=True,
    enable_quota=False,
    prefer_python3=False,
    io_account_expire=False,
    gdp_email_notify=False,
    user_interface="V3 V2",
    mig_oid_title='MiG',
    mig_oid_provider='',
    ext_oid_title='External',
    ext_oid_provider='',
    mig_oidc_title='MiG',
    mig_oidc_provider_meta_url='',
    ext_oidc_title='External',
    ext_oidc_provider_meta_url='',
    ext_oidc_provider_issuer='',
    ext_oidc_provider_authorization_endpoint='',
    ext_oidc_provider_verify_cert_files='',
    ext_oidc_provider_token_endpoint='',
    ext_oidc_provider_token_endpoint_auth='',
    ext_oidc_provider_user_info_endpoint='',
    ext_oidc_scope='profile email',
    ext_oidc_user_info_token_method='',
    ext_oidc_public_key_files='',
    ext_oidc_private_key_files='',
    ext_oidc_response_type='id_token',
    ext_oidc_response_mode='',
    ext_oidc_client_id='',
    ext_oidc_client_name='',
    ext_oidc_pkce_method='',
    ext_oidc_id_token_encrypted_response_alg='',
    ext_oidc_id_token_encrypted_response_enc='',
    ext_oidc_user_info_signed_response_alg='',
    ext_oidc_cookie_same_site='',
    ext_oidc_pass_cookies='',
    ext_oidc_remote_user_claim='sub',
    ext_oidc_pass_claim_as='both',
    ext_oidc_rewrite_cookie='',
    dhparams_path='',
    daemon_keycert='',
    daemon_keycert_sha256=keyword_auto,
    daemon_pubkey='',
    daemon_pubkey_md5=keyword_auto,
    daemon_pubkey_sha256=keyword_auto,
    daemon_pubkey_from_dns=False,
    daemon_show_address='',
    alias_field='',
    peers_permit='distinguished_name:.*',
    vgrid_creators='distinguished_name:.*',
    vgrid_managers='distinguished_name:.*',
    signup_methods='extcert',
    login_methods='extcert',
    digest_salt=keyword_auto,
    crypto_salt=keyword_auto,
    csrf_protection='MEDIUM',
    password_policy='MEDIUM',
    password_legacy_policy='',
    hg_path='',
    hgweb_scripts='',
    trac_admin_path='',
    trac_ini_path='',
    public_port=default_http_port,
    public_http_port=default_http_port,
    public_https_port=default_https_port,
    mig_cert_port=default_https_port,
    ext_cert_port=default_https_port,
    mig_oid_port=default_https_port,
    ext_oid_port=default_https_port,
    mig_oidc_port=default_https_port,
    ext_oidc_port=default_https_port,
    sid_port=default_https_port,
    sftp_port=2222,
    sftp_subsys_port=22,
    sftp_show_port='',
    sftp_max_sessions=-1,
    davs_port=4443,
    davs_show_port='',
    ftps_ctrl_port=8021,
    ftps_ctrl_show_port='',
    ftps_pasv_ports='8100:8400',
    openid_port=8443,
    openid_show_port='',
    openid_session_lifetime=43200,
    seafile_secret=keyword_auto,
    seafile_ccnetid=keyword_auto,
    seafile_seahub_port=8000,
    seafile_seafhttp_port=8082,
    seafile_client_port=13419,
    seafile_quota=2,
    seafile_ro_access=True,
    public_use_https=True,
    user_clause='User',
    group_clause='Group',
    listen_clause='#Listen',
    serveralias_clause='#ServerAlias',
    distro='Debian',
    autolaunch_page=None,
    landing_page=None,
    skin='migrid-basic',
    title='Minimum intrusion Grid',
    short_title='MiG',
    extra_userpage_scripts='',
    extra_userpage_styles='',
    external_doc='https://sourceforge.net/p/migrid/wiki',
    vgrid_label='VGrid',
    secscan_addr='UNSET',
    default_menu='',
    user_menu='',
    collaboration_links='default advanced',
    default_vgrid_links='files web',
    advanced_vgrid_links='files web scm tracker workflows monitor',
    support_email='',
    admin_email='mig',
    admin_list='',
    smtp_server='localhost',
    smtp_sender='',
    log_level='info',
    permanent_freeze='no',
    freeze_to_tape='',
    status_system_match=keyword_any,
    storage_protocols=keyword_auto,
    duplicati_protocols=keyword_auto,
    imnotify_address='',
    imnotify_channel='',
    imnotify_username='',
    imnotify_password='',
    gdp_data_categories='data_categories.json',
    gdp_id_scramble='safe_hash',
    gdp_path_scramble='safe_encrypt',
    quota_backend='lustre',
    quota_user_limit=(1024**4),
    quota_vgrid_limit=(1024**4),
    ca_fqdn='',
    ca_user='mig-ca',
    ca_smtp='localhost',
    datasafety_link='',
    datasafety_text='',
    wwwserve_max_bytes=-1,
)


def generate_confs(
    generateconfs_output_path,
    # NOTE: make sure command line args with white-space are properly wrapped
    generateconfs_command=subprocess.list2cmdline(sys.argv),
    source=keyword_auto,
    destination=keyword_auto,
    user=keyword_auto,
    group=keyword_auto,
    timezone=keyword_auto,
    destination_suffix="",
    base_fqdn=_DEFAULTS.base_fqdn,
    public_fqdn=_DEFAULTS.public_fqdn,
    public_alias_fqdn=_DEFAULTS.public_alias_fqdn,
    public_sec_fqdn=_DEFAULTS.public_sec_fqdn,
    status_alias_fqdn=_DEFAULTS.status_alias_fqdn,
    mig_cert_fqdn=_DEFAULTS.mig_cert_fqdn,
    ext_cert_fqdn=_DEFAULTS.ext_cert_fqdn,
    mig_oid_fqdn=_DEFAULTS.mig_oid_fqdn,
    ext_oid_fqdn=_DEFAULTS.ext_oid_fqdn,
    mig_oidc_fqdn=_DEFAULTS.mig_oidc_fqdn,
    ext_oidc_fqdn=_DEFAULTS.ext_oidc_fqdn,
    sid_fqdn=_DEFAULTS.sid_fqdn,
    io_fqdn=_DEFAULTS.io_fqdn,
    cert_fqdn_extras=_DEFAULTS.cert_fqdn_extras,
    cloud_fqdn=_DEFAULTS.cloud_fqdn,
    seafile_fqdn=_DEFAULTS.seafile_fqdn,
    seafile_base=_DEFAULTS.seafile_base,
    seafmedia_base=_DEFAULTS.seafmedia_base,
    seafhttp_base=_DEFAULTS.seafhttp_base,
    openid_address=_DEFAULTS.openid_address,
    sftp_address=_DEFAULTS.sftp_address,
    sftp_subsys_address=_DEFAULTS.sftp_subsys_address,
    ftps_address=_DEFAULTS.ftps_address,
    davs_address=_DEFAULTS.davs_address,
    jupyter_services=_DEFAULTS.jupyter_services,
    jupyter_services_desc=_DEFAULTS.jupyter_services_desc,
    cloud_services=_DEFAULTS.cloud_services,
    cloud_services_desc=_DEFAULTS.cloud_services_desc,
    apache_version=_DEFAULTS.apache_version,
    apache_etc=_DEFAULTS.apache_etc,
    apache_run=_DEFAULTS.apache_run,
    apache_lock=_DEFAULTS.apache_lock,
    apache_log=_DEFAULTS.apache_log,
    apache_worker_procs=_DEFAULTS.apache_worker_procs,
    openssh_version=_DEFAULTS.openssh_version,
    mig_code=_DEFAULTS.mig_code,
    mig_state=_DEFAULTS.mig_state,
    mig_certs=_DEFAULTS.mig_certs,
    auto_add_cert_user=_DEFAULTS.auto_add_cert_user,
    auto_add_oid_user=_DEFAULTS.auto_add_oid_user,
    auto_add_oidc_user=_DEFAULTS.auto_add_oidc_user,
    auto_add_filter_fields=_DEFAULTS.auto_add_filter_fields,
    auto_add_filter_method=_DEFAULTS.auto_add_filter_method,
    auto_add_user_permit=_DEFAULTS.auto_add_user_permit,
    auto_add_user_with_peer=_DEFAULTS.auto_add_user_with_peer,
    cert_valid_days=_DEFAULTS.cert_valid_days,
    oid_valid_days=_DEFAULTS.oid_valid_days,
    oidc_valid_days=_DEFAULTS.oidc_valid_days,
    generic_valid_days=_DEFAULTS.generic_valid_days,
    enable_migadmin=_DEFAULTS.enable_migadmin,
    enable_sftp=_DEFAULTS.enable_sftp,
    enable_sftp_subsys=_DEFAULTS.enable_sftp_subsys,
    sftp_subsys_auth_procs=_DEFAULTS.sftp_subsys_auth_procs,
    enable_davs=_DEFAULTS.enable_davs,
    enable_ftps=_DEFAULTS.enable_ftps,
    enable_wsgi=_DEFAULTS.enable_wsgi,
    wsgi_procs=_DEFAULTS.wsgi_procs,
    enable_gdp=_DEFAULTS.enable_gdp,
    enable_jobs=_DEFAULTS.enable_jobs,
    enable_resources=_DEFAULTS.enable_resources,
    enable_workflows=_DEFAULTS.enable_workflows,
    enable_events=_DEFAULTS.enable_events,
    enable_sharelinks=_DEFAULTS.enable_sharelinks,
    enable_transfers=_DEFAULTS.enable_transfers,
    enable_freeze=_DEFAULTS.enable_freeze,
    enable_sandboxes=_DEFAULTS.enable_sandboxes,
    enable_vmachines=_DEFAULTS.enable_vmachines,
    enable_preview=_DEFAULTS.enable_preview,
    enable_jupyter=_DEFAULTS.enable_jupyter,
    enable_cloud=_DEFAULTS.enable_cloud,
    enable_hsts=_DEFAULTS.enable_hsts,
    enable_vhost_certs=_DEFAULTS.enable_vhost_certs,
    enable_verify_certs=_DEFAULTS.enable_verify_certs,
    enable_seafile=_DEFAULTS.enable_seafile,
    enable_duplicati=_DEFAULTS.enable_duplicati,
    enable_crontab=_DEFAULTS.enable_crontab,
    enable_notify=_DEFAULTS.enable_notify,
    enable_imnotify=_DEFAULTS.enable_imnotify,
    enable_dev_accounts=_DEFAULTS.enable_dev_accounts,
    enable_twofactor=_DEFAULTS.enable_twofactor,
    twofactor_mandatory_protos=_DEFAULTS.twofactor_mandatory_protos,
    enable_twofactor_strict_address=_DEFAULTS.enable_twofactor_strict_address,
    twofactor_auth_apps=_DEFAULTS.twofactor_auth_apps,
    enable_peers=_DEFAULTS.enable_peers,
    peers_mandatory=_DEFAULTS.peers_mandatory,
    peers_explicit_fields=_DEFAULTS.peers_explicit_fields,
    peers_contact_hint=_DEFAULTS.peers_contact_hint,
    enable_cracklib=_DEFAULTS.enable_cracklib,
    enable_openid=_DEFAULTS.enable_openid,
    enable_gravatars=_DEFAULTS.enable_gravatars,
    enable_sitestatus=_DEFAULTS.enable_sitestatus,
    enable_quota=_DEFAULTS.enable_quota,
    prefer_python3=_DEFAULTS.prefer_python3,
    io_account_expire=_DEFAULTS.io_account_expire,
    gdp_email_notify=_DEFAULTS.gdp_email_notify,
    user_interface=_DEFAULTS.user_interface,
    mig_oid_title=_DEFAULTS.mig_oid_title,
    mig_oid_provider=_DEFAULTS.mig_oid_provider,
    ext_oid_title=_DEFAULTS.ext_oid_title,
    ext_oid_provider=_DEFAULTS.ext_oid_provider,
    mig_oidc_title=_DEFAULTS.mig_oidc_title,
    mig_oidc_provider_meta_url=_DEFAULTS.mig_oidc_provider_meta_url,
    ext_oidc_title=_DEFAULTS.ext_oidc_title,
    ext_oidc_provider_meta_url=_DEFAULTS.ext_oidc_provider_meta_url,
    ext_oidc_provider_issuer=_DEFAULTS.ext_oidc_provider_issuer,
    ext_oidc_provider_authorization_endpoint=_DEFAULTS.ext_oidc_provider_authorization_endpoint,
    ext_oidc_provider_verify_cert_files=_DEFAULTS.ext_oidc_provider_verify_cert_files,
    ext_oidc_provider_token_endpoint=_DEFAULTS.ext_oidc_provider_token_endpoint,
    ext_oidc_provider_token_endpoint_auth=_DEFAULTS.ext_oidc_provider_token_endpoint_auth,
    ext_oidc_provider_user_info_endpoint=_DEFAULTS.ext_oidc_provider_user_info_endpoint,
    ext_oidc_scope=_DEFAULTS.ext_oidc_scope,
    ext_oidc_user_info_token_method=_DEFAULTS.ext_oidc_user_info_token_method,
    ext_oidc_public_key_files=_DEFAULTS.ext_oidc_public_key_files,
    ext_oidc_private_key_files=_DEFAULTS.ext_oidc_private_key_files,
    ext_oidc_response_type=_DEFAULTS.ext_oidc_response_type,
    ext_oidc_response_mode=_DEFAULTS.ext_oidc_response_mode,
    ext_oidc_client_id=_DEFAULTS.ext_oidc_client_id,
    ext_oidc_client_name=_DEFAULTS.ext_oidc_client_name,
    ext_oidc_pkce_method=_DEFAULTS.ext_oidc_pkce_method,
    ext_oidc_id_token_encrypted_response_alg=_DEFAULTS.ext_oidc_id_token_encrypted_response_alg,
    ext_oidc_id_token_encrypted_response_enc=_DEFAULTS.ext_oidc_id_token_encrypted_response_enc,
    ext_oidc_user_info_signed_response_alg=_DEFAULTS.ext_oidc_user_info_signed_response_alg,
    ext_oidc_cookie_same_site=_DEFAULTS.ext_oidc_cookie_same_site,
    ext_oidc_pass_cookies=_DEFAULTS.ext_oidc_pass_cookies,
    ext_oidc_remote_user_claim=_DEFAULTS.ext_oidc_remote_user_claim,
    ext_oidc_pass_claim_as=_DEFAULTS.ext_oidc_pass_claim_as,
    ext_oidc_rewrite_cookie=_DEFAULTS.ext_oidc_rewrite_cookie,
    dhparams_path=_DEFAULTS.dhparams_path,
    daemon_keycert=_DEFAULTS.daemon_keycert,
    daemon_keycert_sha256=_DEFAULTS.daemon_keycert_sha256,
    daemon_pubkey=_DEFAULTS.daemon_pubkey,
    daemon_pubkey_from_dns=_DEFAULTS.daemon_pubkey_from_dns,
    daemon_pubkey_md5=_DEFAULTS.daemon_pubkey_md5,
    daemon_pubkey_sha256=_DEFAULTS.daemon_pubkey_sha256,
    daemon_show_address=_DEFAULTS.daemon_show_address,
    alias_field=_DEFAULTS.alias_field,
    peers_permit=_DEFAULTS.peers_permit,
    vgrid_creators=_DEFAULTS.vgrid_creators,
    vgrid_managers=_DEFAULTS.vgrid_managers,
    signup_methods=_DEFAULTS.signup_methods,
    login_methods=_DEFAULTS.login_methods,
    digest_salt=_DEFAULTS.digest_salt,
    crypto_salt=_DEFAULTS.crypto_salt,
    csrf_protection=_DEFAULTS.csrf_protection,
    password_policy=_DEFAULTS.password_policy,
    password_legacy_policy=_DEFAULTS.password_legacy_policy,
    hg_path=_DEFAULTS.hg_path,
    hgweb_scripts=_DEFAULTS.hgweb_scripts,
    trac_admin_path=_DEFAULTS.trac_admin_path,
    trac_ini_path=_DEFAULTS.trac_ini_path,
    public_port=_DEFAULTS.public_port,
    public_http_port=_DEFAULTS.public_http_port,
    public_https_port=_DEFAULTS.public_https_port,
    mig_cert_port=_DEFAULTS.mig_cert_port,
    ext_cert_port=_DEFAULTS.ext_cert_port,
    mig_oid_port=_DEFAULTS.mig_oid_port,
    ext_oid_port=_DEFAULTS.ext_oid_port,
    mig_oidc_port=_DEFAULTS.mig_oidc_port,
    ext_oidc_port=_DEFAULTS.ext_oidc_port,
    sid_port=_DEFAULTS.sid_port,
    sftp_port=_DEFAULTS.sftp_port,
    sftp_subsys_port=_DEFAULTS.sftp_subsys_port,
    sftp_show_port=_DEFAULTS.sftp_show_port,
    sftp_max_sessions=_DEFAULTS.sftp_max_sessions,
    davs_port=_DEFAULTS.davs_port,
    davs_show_port=_DEFAULTS.davs_show_port,
    ftps_ctrl_port=_DEFAULTS.ftps_ctrl_port,
    ftps_ctrl_show_port=_DEFAULTS.ftps_ctrl_show_port,
    ftps_pasv_ports=_DEFAULTS.ftps_pasv_ports,
    openid_port=_DEFAULTS.openid_port,
    openid_show_port=_DEFAULTS.openid_show_port,
    openid_session_lifetime=_DEFAULTS.openid_session_lifetime,
    seafile_secret=_DEFAULTS.seafile_secret,
    seafile_ccnetid=_DEFAULTS.seafile_ccnetid,
    seafile_seahub_port=_DEFAULTS.seafile_seahub_port,
    seafile_seafhttp_port=_DEFAULTS.seafile_seafhttp_port,
    seafile_client_port=_DEFAULTS.seafile_client_port,
    seafile_quota=_DEFAULTS.seafile_quota,
    seafile_ro_access=_DEFAULTS.seafile_ro_access,
    public_use_https=_DEFAULTS.public_use_https,
    user_clause=_DEFAULTS.user_clause,
    group_clause=_DEFAULTS.group_clause,
    listen_clause=_DEFAULTS.listen_clause,
    serveralias_clause=_DEFAULTS.serveralias_clause,
    distro=_DEFAULTS.distro,
    autolaunch_page=_DEFAULTS.autolaunch_page,
    landing_page=_DEFAULTS.landing_page,
    skin=_DEFAULTS.skin,
    title=_DEFAULTS.title,
    short_title=_DEFAULTS.short_title,
    extra_userpage_scripts=_DEFAULTS.extra_userpage_scripts,
    extra_userpage_styles=_DEFAULTS.extra_userpage_styles,
    external_doc=_DEFAULTS.external_doc,
    vgrid_label=_DEFAULTS.vgrid_label,
    secscan_addr=_DEFAULTS.secscan_addr,
    default_menu=_DEFAULTS.default_menu,
    user_menu=_DEFAULTS.user_menu,
    collaboration_links=_DEFAULTS.collaboration_links,
    default_vgrid_links=_DEFAULTS.default_vgrid_links,
    advanced_vgrid_links=_DEFAULTS.advanced_vgrid_links,
    support_email=_DEFAULTS.support_email,
    admin_email=_DEFAULTS.admin_email,
    admin_list=_DEFAULTS.admin_list,
    smtp_server=_DEFAULTS.smtp_server,
    smtp_sender=_DEFAULTS.smtp_sender,
    permanent_freeze=_DEFAULTS.permanent_freeze,
    log_level=_DEFAULTS.log_level,
    freeze_to_tape=_DEFAULTS.freeze_to_tape,
    status_system_match=_DEFAULTS.status_system_match,
    storage_protocols=_DEFAULTS.storage_protocols,
    duplicati_protocols=_DEFAULTS.duplicati_protocols,
    imnotify_address=_DEFAULTS.imnotify_address,
    imnotify_channel=_DEFAULTS.imnotify_channel,
    imnotify_username=_DEFAULTS.imnotify_username,
    imnotify_password=_DEFAULTS.imnotify_password,
    gdp_data_categories=_DEFAULTS.gdp_data_categories,
    gdp_id_scramble=_DEFAULTS.gdp_id_scramble,
    gdp_path_scramble=_DEFAULTS.gdp_path_scramble,
    quota_backend=_DEFAULTS.quota_backend,
    quota_user_limit=_DEFAULTS.quota_user_limit,
    quota_vgrid_limit=_DEFAULTS.quota_vgrid_limit,
    ca_fqdn=_DEFAULTS.ca_fqdn,
    ca_user=_DEFAULTS.ca_user,
    ca_smtp=_DEFAULTS.ca_smtp,
    datasafety_link=_DEFAULTS.datasafety_link,
    datasafety_text=_DEFAULTS.datasafety_text,
    wwwserve_max_bytes=_DEFAULTS.wwwserve_max_bytes,
    _getpwnam=pwd.getpwnam,
    _prepare=None,
    _writefiles=None,
    _instructions=None,
):
    """Generate Apache and MiG server confs with specified variables"""

    assert os.path.isabs(
        generateconfs_output_path), "output directory must be an absolute path"

    # TODO: override in signature as a non-functional follow-up change
    if _prepare is None:
        _prepare = _generate_confs_prepare
    if _writefiles is None:
        _writefiles = _generate_confs_writefiles
    if _instructions is None:
        _instructions = _generate_confs_instructions

    # Read out dictionary of args with defaults and overrides

    thelocals = locals()
    expanded = {k: v for k, v in thelocals.items() if k not in
                _GENERATE_CONFS_NOFORWARD_KEYS}

    # expand any directory path specific as "auto" relative to CWD

    if source == keyword_auto:
        # use the templates from this copy of the code tree
        template_dir = os.path.join(MIG_BASE, "mig/install")
    else:
        # construct a path using the supplied value made absolute
        template_dir = abspath(source, start=generateconfs_output_path)

    if destination == keyword_auto:
        # write output into a confs folder within the CWD
        destination = os.path.join(generateconfs_output_path, 'confs')
    elif os.path.isabs(destination):
        # take the caller at face-value and do not change the path
        pass
    else:
        # construct a path from the supplied value made absolute
        destination = abspath(destination, start=generateconfs_output_path)

    # finalize destination paths up-front
    destination_link = destination
    destination_dir = "%s%s" % (destination, destination_suffix)

    # expand mig, certs and state paths relative to base if left to "AUTO"

    if mig_code == keyword_auto:
        mig_code = expanded['mig_code'] = os.path.join(MIG_BASE, 'mig')

    if mig_certs == keyword_auto:
        mig_certs = expanded['mig_certs'] = os.path.join(MIG_BASE, 'certs')

    if mig_state == keyword_auto:
        mig_state = expanded['mig_state'] = os.path.join(MIG_BASE, 'state')

    # expand any user information marked as "auto" based on the environment

    if user == keyword_auto:
        user = pwd.getpwuid(os.getuid())[0]

    if group == keyword_auto:
        group = grp.getgrgid(os.getgid())[0]

    # Backwards compatibility with old name
    if public_port and not public_http_port:
        public_http_port = public_port

    user_pw_info = _getpwnam(user)

    if timezone == keyword_auto:
        timezone = determine_timezone()

    options = {
        'command_line': generateconfs_command,
        'destination_dir': destination_dir,
        'destination_link': destination_link,
        'template_dir': template_dir,
        'timezone': timezone,
        'user_gid': user_pw_info.pw_gid,
        'user_group': group,
        'user_uid': user_pw_info.pw_uid,
        'user_uname': user,
    }
    user_dict = _prepare(options, **expanded)
    _writefiles(options, user_dict)
    _instructions(options, user_dict)
    return (options, user_dict)


_GENERATE_CONFS_PARAMETERS = set(inspect_args(generate_confs)) - set(_GENERATE_CONFS_NOFORWARD_KEYS)


def _generate_confs_prepare(
    options,
    # forwarded arguments
    base_fqdn,
    public_fqdn,
    public_alias_fqdn,
    status_alias_fqdn,
    public_sec_fqdn,
    mig_cert_fqdn,
    ext_cert_fqdn,
    mig_oid_fqdn,
    ext_oid_fqdn,
    mig_oidc_fqdn,
    ext_oidc_fqdn,
    sid_fqdn,
    io_fqdn,
    cert_fqdn_extras,
    cloud_fqdn,
    seafile_fqdn,
    seafile_base,
    seafmedia_base,
    seafhttp_base,
    openid_address,
    sftp_address,
    sftp_subsys_address,
    ftps_address,
    davs_address,
    jupyter_services,
    jupyter_services_desc,
    cloud_services,
    cloud_services_desc,
    apache_version,
    apache_etc,
    apache_run,
    apache_lock,
    apache_log,
    apache_worker_procs,
    openssh_version,
    mig_code,
    mig_state,
    mig_certs,
    auto_add_cert_user,
    auto_add_oid_user,
    auto_add_oidc_user,
    auto_add_filter_fields,
    auto_add_filter_method,
    auto_add_user_permit,
    auto_add_user_with_peer,
    cert_valid_days,
    oid_valid_days,
    oidc_valid_days,
    generic_valid_days,
    enable_migadmin,
    enable_sftp,
    enable_sftp_subsys,
    sftp_subsys_auth_procs,
    enable_davs,
    enable_ftps,
    enable_wsgi,
    wsgi_procs,
    enable_gdp,
    enable_jobs,
    enable_resources,
    enable_workflows,
    enable_events,
    enable_sharelinks,
    enable_transfers,
    enable_freeze,
    enable_sandboxes,
    enable_vmachines,
    enable_preview,
    enable_jupyter,
    enable_cloud,
    enable_hsts,
    enable_vhost_certs,
    enable_verify_certs,
    enable_seafile,
    enable_duplicati,
    enable_crontab,
    enable_notify,
    enable_imnotify,
    enable_dev_accounts,
    enable_twofactor,
    twofactor_mandatory_protos,
    enable_twofactor_strict_address,
    twofactor_auth_apps,
    enable_peers,
    peers_mandatory,
    peers_explicit_fields,
    peers_contact_hint,
    enable_cracklib,
    enable_openid,
    enable_gravatars,
    enable_sitestatus,
    enable_quota,
    prefer_python3,
    io_account_expire,
    gdp_email_notify,
    user_interface,
    mig_oid_title,
    mig_oid_provider,
    ext_oid_title,
    ext_oid_provider,
    mig_oidc_title,
    mig_oidc_provider_meta_url,
    ext_oidc_title,
    ext_oidc_provider_meta_url,
    ext_oidc_provider_issuer,
    ext_oidc_provider_authorization_endpoint,
    ext_oidc_provider_verify_cert_files,
    ext_oidc_provider_token_endpoint,
    ext_oidc_provider_token_endpoint_auth,
    ext_oidc_provider_user_info_endpoint,
    ext_oidc_scope,
    ext_oidc_user_info_token_method,
    ext_oidc_public_key_files,
    ext_oidc_private_key_files,
    ext_oidc_response_type,
    ext_oidc_response_mode,
    ext_oidc_client_id,
    ext_oidc_client_name,
    ext_oidc_pkce_method,
    ext_oidc_id_token_encrypted_response_alg,
    ext_oidc_id_token_encrypted_response_enc,
    ext_oidc_user_info_signed_response_alg,
    ext_oidc_cookie_same_site,
    ext_oidc_pass_cookies,
    ext_oidc_remote_user_claim,
    ext_oidc_pass_claim_as,
    ext_oidc_rewrite_cookie,
    dhparams_path,
    daemon_keycert,
    daemon_keycert_sha256,
    daemon_pubkey,
    daemon_pubkey_md5,
    daemon_pubkey_sha256,
    daemon_pubkey_from_dns,
    daemon_show_address,
    alias_field,
    peers_permit,
    vgrid_creators,
    vgrid_managers,
    signup_methods,
    login_methods,
    digest_salt,
    crypto_salt,
    csrf_protection,
    password_policy,
    password_legacy_policy,
    hg_path,
    hgweb_scripts,
    trac_admin_path,
    trac_ini_path,
    public_port,
    public_http_port,
    public_https_port,
    mig_cert_port,
    ext_cert_port,
    mig_oid_port,
    ext_oid_port,
    mig_oidc_port,
    ext_oidc_port,
    sid_port,
    sftp_port,
    sftp_subsys_port,
    sftp_show_port,
    sftp_max_sessions,
    davs_port,
    davs_show_port,
    ftps_ctrl_port,
    ftps_ctrl_show_port,
    ftps_pasv_ports,
    openid_port,
    openid_show_port,
    openid_session_lifetime,
    seafile_secret,
    seafile_ccnetid,
    seafile_seahub_port,
    seafile_seafhttp_port,
    seafile_client_port,
    seafile_quota,
    seafile_ro_access,
    public_use_https,
    user_clause,
    group_clause,
    listen_clause,
    serveralias_clause,
    distro,
    autolaunch_page,
    landing_page,
    skin,
    title,
    short_title,
    extra_userpage_scripts,
    extra_userpage_styles,
    external_doc,
    vgrid_label,
    secscan_addr,
    default_menu,
    user_menu,
    collaboration_links,
    default_vgrid_links,
    advanced_vgrid_links,
    support_email,
    admin_email,
    admin_list,
    smtp_server,
    smtp_sender,
    log_level,
    permanent_freeze,
    freeze_to_tape,
    status_system_match,
    storage_protocols,
    duplicati_protocols,
    imnotify_address,
    imnotify_channel,
    imnotify_username,
    imnotify_password,
    gdp_data_categories,
    gdp_id_scramble,
    gdp_path_scramble,
    quota_backend,
    quota_user_limit,
    quota_vgrid_limit,
    ca_fqdn,
    ca_user,
    ca_smtp,
    datasafety_link,
    datasafety_text,
    wwwserve_max_bytes,
):
    """Prepate conf generator run"""
    user_dict = {}
    user_dict['__GENERATECONFS_COMMAND__'] = options['command_line']
    user_dict['__BASE_FQDN__'] = base_fqdn
    user_dict['__PUBLIC_FQDN__'] = public_fqdn
    user_dict['__PUBLIC_ALIAS_FQDN__'] = public_alias_fqdn
    user_dict['__STATUS_ALIAS_FQDN__'] = status_alias_fqdn
    if public_use_https:
        if public_sec_fqdn:
            user_dict['__PUBLIC_SEC_FQDN__'] = public_sec_fqdn
        else:
            user_dict['__PUBLIC_SEC_FQDN__'] = public_fqdn
    user_dict['__MIG_CERT_FQDN__'] = mig_cert_fqdn
    user_dict['__EXT_CERT_FQDN__'] = ext_cert_fqdn
    user_dict['__MIG_OID_FQDN__'] = mig_oid_fqdn
    user_dict['__EXT_OID_FQDN__'] = ext_oid_fqdn
    user_dict['__MIG_OIDC_FQDN__'] = mig_oidc_fqdn
    user_dict['__EXT_OIDC_FQDN__'] = ext_oidc_fqdn
    user_dict['__SID_FQDN__'] = sid_fqdn
    user_dict['__IO_FQDN__'] = io_fqdn
    user_dict['__CERT_FQDN_EXTRAS__'] = cert_fqdn_extras
    user_dict['__CLOUD_FQDN__'] = cloud_fqdn
    user_dict['__SEAFILE_FQDN__'] = seafile_fqdn
    user_dict['__SEAFILE_BASE__'] = seafile_base
    user_dict['__SEAFMEDIA_BASE__'] = seafmedia_base
    user_dict['__SEAFHTTP_BASE__'] = seafhttp_base
    user_dict['__OPENID_ADDRESS__'] = openid_address
    user_dict['__SFTP_ADDRESS__'] = sftp_address
    user_dict['__SFTP_SUBSYS_ADDRESS__'] = sftp_subsys_address
    user_dict['__FTPS_ADDRESS__'] = ftps_address
    user_dict['__DAVS_ADDRESS__'] = davs_address
    user_dict['__JUPYTER_SERVICES__'] = jupyter_services
    user_dict['__JUPYTER_DEFS__'] = ''
    user_dict['__JUPYTER_OPENIDS__'] = ''
    user_dict['__JUPYTER_OIDCS__'] = ''
    user_dict['__JUPYTER_REWRITES__'] = ''
    user_dict['__JUPYTER_PROXIES__'] = ''
    user_dict['__JUPYTER_SECTIONS__'] = ''
    user_dict['__CLOUD_SERVICES__'] = cloud_services
    user_dict['__CLOUD_SECTIONS__'] = ''
    user_dict['__USER__'] = options['user_uname']
    user_dict['__GROUP__'] = options['user_group']
    user_dict['__PUBLIC_HTTP_PORT__'] = "%s" % public_http_port
    user_dict['__PUBLIC_HTTPS_PORT__'] = "%s" % public_https_port
    user_dict['__MIG_CERT_PORT__'] = "%s" % mig_cert_port
    user_dict['__EXT_CERT_PORT__'] = "%s" % ext_cert_port
    user_dict['__MIG_OID_PORT__'] = "%s" % mig_oid_port
    user_dict['__EXT_OID_PORT__'] = "%s" % ext_oid_port
    user_dict['__MIG_OIDC_PORT__'] = "%s" % mig_oidc_port
    user_dict['__EXT_OIDC_PORT__'] = "%s" % ext_oidc_port
    user_dict['__SID_PORT__'] = "%s" % sid_port
    user_dict['__MIG_BASE__'] = os.path.dirname(mig_code.rstrip(os.sep))
    user_dict['__MIG_CODE__'] = mig_code
    user_dict['__MIG_STATE__'] = mig_state
    user_dict['__MIG_CERTS__'] = mig_certs
    user_dict['__APACHE_VERSION__'] = apache_version
    user_dict['__APACHE_ETC__'] = apache_etc
    user_dict['__APACHE_RUN__'] = apache_run
    user_dict['__APACHE_LOCK__'] = apache_lock
    user_dict['__APACHE_LOG__'] = apache_log
    user_dict['__APACHE_WORKER_PROCS__'] = "%s" % apache_worker_procs
    user_dict['__OPENSSH_VERSION__'] = openssh_version
    user_dict['__AUTO_ADD_CERT_USER__'] = "%s" % auto_add_cert_user
    user_dict['__AUTO_ADD_OID_USER__'] = "%s" % auto_add_oid_user
    user_dict['__AUTO_ADD_OIDC_USER__'] = "%s" % auto_add_oidc_user
    user_dict['__AUTO_ADD_FILTER_FIELDS__'] = auto_add_filter_fields
    user_dict['__AUTO_ADD_FILTER_METHOD__'] = auto_add_filter_method
    user_dict['__AUTO_ADD_USER_PERMIT__'] = auto_add_user_permit
    user_dict['__AUTO_ADD_USER_WITH_PEER__'] = auto_add_user_with_peer
    user_dict['__CERT_VALID_DAYS__'] = "%s" % cert_valid_days
    user_dict['__OID_VALID_DAYS__'] = "%s" % oid_valid_days
    user_dict['__OIDC_VALID_DAYS__'] = "%s" % oidc_valid_days
    user_dict['__GENERIC_VALID_DAYS__'] = "%s" % generic_valid_days
    user_dict['__ENABLE_MIGADMIN__'] = "%s" % enable_migadmin
    user_dict['__ENABLE_SFTP__'] = "%s" % enable_sftp
    user_dict['__ENABLE_SFTP_SUBSYS__'] = "%s" % enable_sftp_subsys
    user_dict['__SFTP_SUBSYS_START_AUTH_PROCS__'] = "%s" % sftp_subsys_auth_procs
    user_dict['__SFTP_SUBSYS_MAX_AUTH_PROCS__'] = "%s" % max(
        4 * sftp_subsys_auth_procs, 100)
    user_dict['__ENABLE_DAVS__'] = "%s" % enable_davs
    user_dict['__ENABLE_FTPS__'] = "%s" % enable_ftps
    user_dict['__ENABLE_WSGI__'] = "%s" % enable_wsgi
    user_dict['__WSGI_PROCS__'] = "%s" % wsgi_procs
    user_dict['__ENABLE_GDP__'] = "%s" % enable_gdp
    user_dict['__ENABLE_JOBS__'] = "%s" % enable_jobs
    user_dict['__ENABLE_RESOURCES__'] = "%s" % enable_resources
    user_dict['__ENABLE_WORKFLOWS__'] = "%s" % enable_workflows
    user_dict['__ENABLE_EVENTS__'] = "%s" % enable_events
    user_dict['__ENABLE_SHARELINKS__'] = "%s" % enable_sharelinks
    user_dict['__ENABLE_TRANSFERS__'] = "%s" % enable_transfers
    user_dict['__ENABLE_FREEZE__'] = "%s" % enable_freeze
    user_dict['__ENABLE_SANDBOXES__'] = "%s" % enable_sandboxes
    user_dict['__ENABLE_VMACHINES__'] = "%s" % enable_vmachines
    user_dict['__ENABLE_PREVIEW__'] = "%s" % enable_preview
    user_dict['__ENABLE_JUPYTER__'] = "%s" % enable_jupyter
    user_dict['__ENABLE_CLOUD__'] = "%s" % enable_cloud
    user_dict['__ENABLE_HSTS__'] = "%s" % enable_hsts
    user_dict['__ENABLE_VHOST_CERTS__'] = "%s" % enable_vhost_certs
    user_dict['__ENABLE_VERIFY_CERTS__'] = "%s" % enable_verify_certs
    user_dict['__ENABLE_SEAFILE__'] = "%s" % enable_seafile
    user_dict['__ENABLE_DUPLICATI__'] = "%s" % enable_duplicati
    user_dict['__ENABLE_CRONTAB__'] = "%s" % enable_crontab
    user_dict['__ENABLE_NOTIFY__'] = "%s" % enable_notify
    user_dict['__ENABLE_IMNOTIFY__'] = "%s" % enable_imnotify
    user_dict['__ENABLE_DEV_ACCOUNTS__'] = "%s" % enable_dev_accounts
    user_dict['__ENABLE_TWOFACTOR__'] = "%s" % enable_twofactor
    user_dict['__TWOFACTOR_MANDATORY_PROTOS__'] = twofactor_mandatory_protos
    user_dict['__ENABLE_TWOFACTOR_STRICT_ADDRESS__'] = "%s" % enable_twofactor_strict_address
    user_dict['__TWOFACTOR_AUTH_APPS__'] = twofactor_auth_apps
    user_dict['__ENABLE_PEERS__'] = "%s" % enable_peers
    user_dict['__PEERS_MANDATORY__'] = "%s" % peers_mandatory
    user_dict['__PEERS_EXPLICIT_FIELDS__'] = peers_explicit_fields
    user_dict['__PEERS_CONTACT_HINT__'] = peers_contact_hint
    user_dict['__ENABLE_CRACKLIB__'] = "%s" % enable_cracklib
    user_dict['__ENABLE_OPENID__'] = "%s" % enable_openid
    user_dict['__ENABLE_GRAVATARS__'] = "%s" % enable_gravatars
    user_dict['__ENABLE_SITESTATUS__'] = "%s" % enable_sitestatus
    user_dict['__ENABLE_QUOTA__'] = "%s" % enable_quota
    user_dict['__PREFER_PYTHON3__'] = "%s" % prefer_python3
    user_dict['__IO_ACCOUNT_EXPIRE__'] = "%s" % io_account_expire
    user_dict['__GDP_EMAIL_NOTIFY__'] = "%s" % gdp_email_notify
    user_dict['__USER_INTERFACE__'] = user_interface
    user_dict['__MIG_OID_TITLE__'] = mig_oid_title
    user_dict['__MIG_OID_PROVIDER_BASE__'] = mig_oid_provider
    user_dict['__MIG_OID_PROVIDER_ID__'] = mig_oid_provider
    user_dict['__MIG_OID_AUTH_DB__'] = auth_openid_mig_db
    user_dict['__EXT_OID_TITLE__'] = ext_oid_title
    user_dict['__EXT_OID_PROVIDER_BASE__'] = ext_oid_provider
    user_dict['__EXT_OID_PROVIDER_ID__'] = ext_oid_provider
    user_dict['__EXT_OID_AUTH_DB__'] = auth_openid_ext_db
    # Fall-back to oid titles if not provided
    user_dict['__MIG_OIDC_TITLE__'] = mig_oidc_title or mig_oid_title
    user_dict['__MIG_OIDC_PROVIDER_META_URL__'] = mig_oidc_provider_meta_url
    user_dict['__EXT_OIDC_TITLE__'] = ext_oidc_title or ext_oid_title
    user_dict['__EXT_OIDC_PROVIDER_META_URL__'] = ext_oidc_provider_meta_url
    user_dict['__EXT_OIDC_PROVIDER_ISSUER__'] = ext_oidc_provider_issuer
    user_dict['__EXT_OIDC_PROVIDER_AUTHORIZATION_ENDPOINT__'] = ext_oidc_provider_authorization_endpoint
    user_dict['__EXT_OIDC_PROVIDER_VERIFY_CERT_FILES__'] = ext_oidc_provider_verify_cert_files
    user_dict['__EXT_OIDC_PROVIDER_TOKEN_ENDPOINT__'] = ext_oidc_provider_token_endpoint
    user_dict['__EXT_OIDC_PROVIDER_TOKEN_ENDPOINT_AUTH__'] = ext_oidc_provider_token_endpoint_auth
    user_dict['__EXT_OIDC_PROVIDER_USER_INFO_ENDPOINT__'] = ext_oidc_provider_user_info_endpoint
    user_dict['__EXT_OIDC_SCOPE__'] = ext_oidc_scope
    user_dict['__EXT_OIDC_USER_INFO_TOKEN_METHOD__'] = ext_oidc_user_info_token_method
    user_dict['__EXT_OIDC_PUBLIC_KEY_FILES__'] = ext_oidc_public_key_files
    user_dict['__EXT_OIDC_PRIVATE_KEY_FILES__'] = ext_oidc_private_key_files
    user_dict['__EXT_OIDC_RESPONSE_TYPE__'] = ext_oidc_response_type
    user_dict['__EXT_OIDC_RESPONSE_MODE__'] = ext_oidc_response_mode
    user_dict['__EXT_OIDC_CLIENT_ID__'] = ext_oidc_client_id
    user_dict['__EXT_OIDC_CLIENT_NAME__'] = ext_oidc_client_name
    user_dict['__EXT_OIDC_PKCE_METHOD__'] = ext_oidc_pkce_method
    user_dict['__EXT_OIDC_ID_TOKEN_ENCRYPTED_RESPONSE_ALG__'] = ext_oidc_id_token_encrypted_response_alg
    user_dict['__EXT_OIDC_ID_TOKEN_ENCRYPTED_RESPONSE_ENC__'] = ext_oidc_id_token_encrypted_response_enc
    user_dict['__EXT_OIDC_USER_INFO_SIGNED_RESPONSE_ALG__'] = ext_oidc_user_info_signed_response_alg
    user_dict['__EXT_OIDC_COOKIE_SAME_SITE__'] = ext_oidc_cookie_same_site
    user_dict['__EXT_OIDC_PASS_COOKIES__'] = ext_oidc_pass_cookies
    user_dict['__EXT_OIDC_REMOTE_USER_CLAIM__'] = ext_oidc_remote_user_claim
    user_dict['__EXT_OIDC_PASS_CLAIM_AS__'] = ext_oidc_pass_claim_as
    user_dict['__EXT_OIDC_REWRITE_COOKIE__'] = ext_oidc_rewrite_cookie
    user_dict['__PUBLIC_URL__'] = ''
    user_dict['__PUBLIC_ALIAS_URL__'] = ''
    user_dict['__PUBLIC_HTTP_URL__'] = ''
    user_dict['__PUBLIC_HTTPS_URL__'] = ''
    user_dict['__PUBLIC_ALIAS_HTTP_URL__'] = ''
    user_dict['__PUBLIC_ALIAS_HTTPS_URL__'] = ''
    user_dict['__MIG_CERT_URL__'] = ''
    user_dict['__EXT_CERT_URL__'] = ''
    user_dict['__MIG_OID_URL__'] = ''
    user_dict['__EXT_OID_URL__'] = ''
    user_dict['__MIG_OIDC_URL__'] = ''
    user_dict['__EXT_OIDC_URL__'] = ''
    user_dict['__SID_URL__'] = ''
    user_dict['__DHPARAMS_PATH__'] = dhparams_path
    user_dict['__DAEMON_KEYCERT__'] = daemon_keycert
    user_dict['__DAEMON_PUBKEY__'] = daemon_pubkey
    user_dict['__DAEMON_KEYCERT_SHA256__'] = daemon_keycert_sha256
    user_dict['__DAEMON_PUBKEY_MD5__'] = daemon_pubkey_md5
    user_dict['__DAEMON_PUBKEY_SHA256__'] = daemon_pubkey_sha256
    user_dict['__DAEMON_PUBKEY_FROM_DNS__'] = "%s" % daemon_pubkey_from_dns
    user_dict['__SFTP_PORT__'] = "%s" % sftp_port
    user_dict['__SFTP_SUBSYS_PORT__'] = "%s" % sftp_subsys_port
    user_dict['__SFTP_MAX_SESSIONS__'] = "%s" % sftp_max_sessions
    user_dict['__DAVS_PORT__'] = "%s" % davs_port
    user_dict['__FTPS_CTRL_PORT__'] = "%s" % ftps_ctrl_port
    user_dict['__FTPS_PASV_PORTS__'] = ftps_pasv_ports
    user_dict['__OPENID_PORT__'] = "%s" % openid_port
    user_dict['__OPENID_SESSION_LIFETIME__'] = "%s" % openid_session_lifetime
    user_dict['__SEAFILE_SEAHUB_PORT__'] = "%s" % seafile_seahub_port
    user_dict['__SEAFILE_SEAFHTTP_PORT__'] = "%s" % seafile_seafhttp_port
    user_dict['__SEAFILE_CLIENT_PORT__'] = "%s" % seafile_client_port
    user_dict['__SEAFILE_QUOTA__'] = "%s" % seafile_quota
    user_dict['__SEAFILE_RO_ACCESS__'] = "%s" % seafile_ro_access
    user_dict['__PUBLIC_USE_HTTPS__'] = "%s" % public_use_https
    user_dict['__ALIAS_FIELD__'] = alias_field
    user_dict['__PEERS_PERMIT__'] = peers_permit
    user_dict['__VGRID_CREATORS__'] = vgrid_creators
    user_dict['__VGRID_MANAGERS__'] = vgrid_managers
    user_dict['__SIGNUP_METHODS__'] = signup_methods
    user_dict['__LOGIN_METHODS__'] = login_methods
    user_dict['__DIGEST_SALT__'] = digest_salt
    user_dict['__CRYPTO_SALT__'] = crypto_salt
    user_dict['__CSRF_PROTECTION__'] = csrf_protection
    user_dict['__PASSWORD_POLICY__'] = password_policy
    user_dict['__PASSWORD_LEGACY_POLICY__'] = password_legacy_policy
    user_dict['__HG_PATH__'] = hg_path
    user_dict['__HGWEB_SCRIPTS__'] = hgweb_scripts
    user_dict['__TRAC_ADMIN_PATH__'] = trac_admin_path
    user_dict['__TRAC_INI_PATH__'] = trac_ini_path
    user_dict['__USER_CLAUSE__'] = user_clause
    user_dict['__GROUP_CLAUSE__'] = group_clause
    user_dict['__LISTEN_CLAUSE__'] = listen_clause
    user_dict['__SERVERALIAS_CLAUSE__'] = serveralias_clause
    user_dict['__DISTRO__'] = distro
    user_dict['__SKIN__'] = skin
    user_dict['__TITLE__'] = title
    user_dict['__SHORT_TITLE__'] = short_title
    user_dict['__EXTRA_USERPAGE_SCRIPTS__'] = extra_userpage_scripts
    user_dict['__EXTRA_USERPAGE_STYLES__'] = extra_userpage_styles
    user_dict['__EXTERNAL_DOC__'] = external_doc
    user_dict['__VGRID_LABEL__'] = vgrid_label
    user_dict['__SECSCAN_ADDR__'] = secscan_addr
    user_dict['__DEFAULT_MENU__'] = default_menu
    user_dict['__USER_MENU__'] = user_menu
    user_dict['__COLLABORATION_LINKS__'] = collaboration_links
    user_dict['__DEFAULT_VGRID_LINKS__'] = default_vgrid_links
    user_dict['__ADVANCED_VGRID_LINKS__'] = advanced_vgrid_links
    user_dict['__SUPPORT_EMAIL__'] = support_email
    user_dict['__ADMIN_EMAIL__'] = admin_email
    user_dict['__ADMIN_LIST__'] = admin_list
    user_dict['__SMTP_SERVER__'] = smtp_server
    user_dict['__SMTP_SENDER__'] = smtp_sender
    user_dict['__LOG_LEVEL__'] = log_level
    user_dict['__PERMANENT_FREEZE__'] = permanent_freeze
    user_dict['__FREEZE_TO_TAPE__'] = freeze_to_tape
    user_dict['__STATUS_SYSTEM_MATCH__'] = status_system_match
    user_dict['__STORAGE_PROTOCOLS__'] = storage_protocols
    user_dict['__DUPLICATI_PROTOCOLS__'] = duplicati_protocols
    user_dict['__IMNOTIFY_ADDRESS__'] = imnotify_address
    user_dict['__IMNOTIFY_CHANNEL__'] = imnotify_channel
    user_dict['__IMNOTIFY_USERNAME__'] = imnotify_username
    user_dict['__IMNOTIFY_PASSWORD__'] = imnotify_password
    user_dict['__GDP_DATA_CATEGORIES__'] = gdp_data_categories
    user_dict['__GDP_ID_SCRAMBLE__'] = gdp_id_scramble
    user_dict['__GDP_PATH_SCRAMBLE__'] = gdp_path_scramble
    user_dict['__PUBLIC_HTTPS_LISTEN__'] = listen_clause
    user_dict['__PUBLIC_ALIAS_HTTPS_LISTEN__'] = listen_clause
    user_dict['__STATUS_ALIAS_HTTPS_LISTEN__'] = listen_clause
    user_dict['__QUOTA_BACKEND__'] = quota_backend
    user_dict['__QUOTA_USER_LIMIT__'] = "%s" % quota_user_limit
    user_dict['__QUOTA_VGRID_LIMIT__'] = "%s" % quota_vgrid_limit
    user_dict['__CA_FQDN__'] = ca_fqdn
    user_dict['__CA_USER__'] = ca_user
    user_dict['__CA_SMTP__'] = ca_smtp
    user_dict['__DATASAFETY_LINK__'] = datasafety_link
    user_dict['__DATASAFETY_TEXT__'] = datasafety_text
    user_dict['__WWWSERVE_MAX_BYTES__'] = "%d" % (wwwserve_max_bytes)

    user_dict['__MIG_USER__'] = "%s" % (options['user_uname'])
    user_dict['__MIG_GROUP__'] = "%s" % (options['user_group'])

    # Needed for PAM/NSS
    user_dict['__MIG_UID__'] = "%s" % (options['user_uid'])
    user_dict['__MIG_GID__'] = "%s" % (options['user_gid'])

    fail2ban_daemon_ports = []
    # Apache fails on duplicate Listen directives so comment in that case
    port_list = [mig_cert_port, ext_cert_port, mig_oid_port, ext_oid_port,
                 mig_oidc_port, ext_oidc_port, sid_port]
    fqdn_list = [mig_cert_fqdn, ext_cert_fqdn, mig_oid_fqdn, ext_oid_fqdn,
                 mig_oidc_fqdn, ext_oidc_fqdn, sid_fqdn]
    listen_list = list(zip(fqdn_list, port_list))
    enabled_list = [(i, j) for (i, j) in listen_list if i]
    enabled_ports = [j for (i, j) in enabled_list]
    enabled_fqdns = [i for (i, j) in enabled_list]
    same_port = (len(enabled_ports) != len(list(set(enabled_ports))))
    same_fqdn = (len(enabled_fqdns) != len(list(set(enabled_fqdns))))
    user_dict['__IF_SEPARATE_PORTS__'] = '#'
    if not same_port:
        user_dict['__IF_SEPARATE_PORTS__'] = ''

    user_dict['__IF_REQUIRE_CA__'] = '#'
    if mig_cert_fqdn or ext_cert_fqdn:
        user_dict['__IF_REQUIRE_CA__'] = ''

    if same_fqdn and same_port:
        print("""
WARNING: you probably have to use either different fqdn or port settings for
cert, oid and sid based https!
""")

    # All web ports for Fail2Ban jail
    fail2ban_daemon_ports += enabled_ports

    # List of (file, remove_identifers) used to dynamically remove lines from template
    # configurations files
    cleanup_list = []
    # List of (file, insert_identifiers) used to dynamically add to template
    # configuration files
    insert_list = []

    # Paraview and Jupyter require websockets proxy - enable conditionally
    user_dict['__WEBSOCKETS_COMMENTED__'] = '#'
    # OpenID, Seafile, etc. require http(s) proxy - enable conditionally
    user_dict['__PROXY_HTTP_COMMENTED__'] = '#'
    user_dict['__PROXY_HTTPS_COMMENTED__'] = '#'

    # Switch between apache 2.2 and 2.4 directives to match requested version
    user_dict['__APACHE_RECENT_ONLY__'] = 'Only for apache>=2.4'
    user_dict['__APACHE_PRE2.4_ONLY__'] = 'Only for apache<2.4'
    # We use raw string comparison here which seems to work alright for X.Y.Z
    if user_dict['__APACHE_VERSION__'] >= "2.4":
        user_dict['__APACHE_RECENT__'] = ''
        user_dict['__APACHE_PRE2.4__'] = '#'
    else:
        user_dict['__APACHE_PRE2.4__'] = ''
        user_dict['__APACHE_RECENT__'] = '#'

    # We use strong Apache and OpenSSH settings from mig.shared.defaults everywhere
    user_dict['__APACHE_CIPHERS__'] = STRONG_TLS_CIPHERS
    # TODO: Actually enforce curves for apache 2.4.8+ with OpenSSL 1.0.2+
    user_dict['__APACHE_CURVES__'] = STRONG_TLS_CURVES

    # We use raw string comparison here which seems to work alright for X.Y.Z
    if user_dict['__OPENSSH_VERSION__'] >= "8.0":
        # Use current strong HostKey/Kex/Cipher/MAC settings for openssh >=8.0
        user_dict['__OPENSSH_HOSTKEYALGOS__'] = STRONG_SSH_HOSTKEYALGOS
        user_dict['__OPENSSH_KEXALGOS__'] = STRONG_SSH_KEXALGOS
        user_dict['__OPENSSH_CIPHERS__'] = STRONG_SSH_CIPHERS
        user_dict['__OPENSSH_MACS__'] = STRONG_SSH_MACS
    elif user_dict['__OPENSSH_VERSION__'] >= "7.4":
        # Fall back to best legacy HostKey/Kex/Cipher/MAC for openssh >=7.4
        user_dict['__OPENSSH_HOSTKEYALGOS__'] = LEGACY_SSH_HOSTKEYALGOS
        user_dict['__OPENSSH_KEXALGOS__'] = LEGACY_SSH_KEXALGOS
        user_dict['__OPENSSH_CIPHERS__'] = LEGACY_SSH_CIPHERS
        user_dict['__OPENSSH_MACS__'] = LEGACY_SSH_MACS
    else:
        # Fall back to best available HostKey/Kex/Cipher/MAC for openssh <7.4
        user_dict['__OPENSSH_HOSTKEYALGOS__'] = FALLBACK_SSH_HOSTKEYALGOS
        user_dict['__OPENSSH_KEXALGOS__'] = FALLBACK_SSH_KEXALGOS
        user_dict['__OPENSSH_CIPHERS__'] = FALLBACK_SSH_CIPHERS
        user_dict['__OPENSSH_MACS__'] = FALLBACK_SSH_MACS

    # We know that login with one of these common usernames is a password
    # cracking attempt since our own username format differs.
    user_dict['__CRACK_USERNAME_REGEX__'] = CRACK_USERNAME_REGEX
    # We know that when a web request for one of these addresses fails it is a
    # clear sign of someone scanning for web vulnerabilities to abuse.
    user_dict['__CRACK_WEB_REGEX__'] = CRACK_WEB_REGEX

    # Insert min password length based on policy
    min_len, min_classes, errors = password_requirements(password_policy)
    if errors:
        print("Invalid password policy %s: %s" % (password_policy,
                                                  '\n'.join(errors)))
        sys.exit(1)
    # Values must be strings
    user_dict['__PASSWORD_MIN_LEN__'] = "%d" % min_len
    user_dict['__PASSWORD_MIN_CLASSES__'] = "%d" % min_classes

    # Just check that password_legacy_policy is unset or valid here
    if password_legacy_policy:
        _, _, errors = password_requirements(password_legacy_policy)
        if errors:
            print("Invalid password legacy policy %s: %s" %
                  (password_legacy_policy, '\n'.join(errors)))
            sys.exit(1)

    # Define some FQDN helpers if set
    user_dict['__IFDEF_BASE_FQDN__'] = 'UnDefine'
    if user_dict['__BASE_FQDN__']:
        user_dict['__IFDEF_BASE_FQDN__'] = 'Define'
    # No port for __BASE_FQDN__

    user_dict['__IFDEF_PUBLIC_FQDN__'] = 'UnDefine'
    if user_dict['__PUBLIC_FQDN__']:
        user_dict['__IFDEF_PUBLIC_FQDN__'] = 'Define'
    user_dict['__IFDEF_PUBLIC_HTTP_PORT__'] = 'UnDefine'
    if user_dict['__PUBLIC_HTTP_PORT__']:
        user_dict['__IFDEF_PUBLIC_HTTP_PORT__'] = 'Define'
    user_dict['__IFDEF_PUBLIC_HTTPS_PORT__'] = 'UnDefine'
    if user_dict['__PUBLIC_HTTPS_PORT__']:
        user_dict['__IFDEF_PUBLIC_HTTPS_PORT__'] = 'Define'

    user_dict['__IFDEF_PUBLIC_ALIAS_FQDN__'] = 'UnDefine'
    if user_dict['__PUBLIC_ALIAS_FQDN__']:
        user_dict['__IFDEF_PUBLIC_ALIAS_FQDN__'] = 'Define'
    user_dict['__IFDEF_STATUS_ALIAS_FQDN__'] = 'UnDefine'
    if user_dict['__STATUS_ALIAS_FQDN__']:
        user_dict['__IFDEF_STATUS_ALIAS_FQDN__'] = 'Define'

    user_dict['__IFDEF_MIG_CERT_FQDN__'] = 'UnDefine'
    if user_dict['__MIG_CERT_FQDN__']:
        user_dict['__IFDEF_MIG_CERT_FQDN__'] = 'Define'
    user_dict['__IFDEF_MIG_CERT_PORT__'] = 'UnDefine'
    if user_dict['__MIG_CERT_PORT__']:
        user_dict['__IFDEF_MIG_CERT_PORT__'] = 'Define'

    user_dict['__IFDEF_EXT_CERT_FQDN__'] = 'UnDefine'
    if user_dict['__EXT_CERT_FQDN__']:
        user_dict['__IFDEF_EXT_CERT_FQDN__'] = 'Define'
    user_dict['__IFDEF_EXT_CERT_PORT__'] = 'UnDefine'
    if user_dict['__EXT_CERT_PORT__']:
        user_dict['__IFDEF_EXT_CERT_PORT__'] = 'Define'

    user_dict['__IFDEF_MIG_OID_FQDN__'] = 'UnDefine'
    user_dict['__MIG_OID_PROXY_COMMENTED__'] = '#'
    if user_dict['__MIG_OID_FQDN__']:
        user_dict['__IFDEF_MIG_OID_FQDN__'] = 'Define'
        # Automatically enable proxy for MIG_OID_FQDN/openid/ to OpenID daemon
        user_dict['__MIG_OID_PROXY_COMMENTED__'] = ''
    user_dict['__IFDEF_MIG_OID_PORT__'] = 'UnDefine'
    if user_dict['__MIG_OID_PORT__']:
        user_dict['__IFDEF_MIG_OID_PORT__'] = 'Define'

    user_dict['__IFDEF_EXT_OID_FQDN__'] = 'UnDefine'
    if user_dict['__EXT_OID_FQDN__']:
        user_dict['__IFDEF_EXT_OID_FQDN__'] = 'Define'
    user_dict['__IFDEF_EXT_OID_PORT__'] = 'UnDefine'
    if user_dict['__EXT_OID_PORT__']:
        user_dict['__IFDEF_EXT_OID_PORT__'] = 'Define'

    user_dict['__IFDEF_MIG_OIDC_FQDN__'] = 'UnDefine'
    if user_dict['__MIG_OIDC_FQDN__']:
        user_dict['__IFDEF_MIG_OIDC_FQDN__'] = 'Define'
    user_dict['__IFDEF_MIG_OIDC_PORT__'] = 'UnDefine'
    if user_dict['__MIG_OIDC_PORT__']:
        user_dict['__IFDEF_MIG_OIDC_PORT__'] = 'Define'

    user_dict['__IFDEF_EXT_OIDC_FQDN__'] = 'UnDefine'
    if user_dict['__EXT_OIDC_FQDN__']:
        user_dict['__IFDEF_EXT_OIDC_FQDN__'] = 'Define'
    user_dict['__IFDEF_EXT_OIDC_PORT__'] = 'UnDefine'
    if user_dict['__EXT_OIDC_PORT__']:
        user_dict['__IFDEF_EXT_OIDC_PORT__'] = 'Define'

    user_dict['__IFDEF_SID_FQDN__'] = 'UnDefine'
    if user_dict['__SID_FQDN__']:
        user_dict['__IFDEF_SID_FQDN__'] = 'Define'
    user_dict['__IFDEF_SID_PORT__'] = 'UnDefine'
    if user_dict['__SID_PORT__']:
        user_dict['__IFDEF_SID_PORT__'] = 'Define'

    # TODO: Eliminate use of IO_FQDN in apache after switch to OPENID_ADDRESS
    user_dict['__IFDEF_IO_FQDN__'] = 'UnDefine'
    if user_dict['__IO_FQDN__']:
        user_dict['__IFDEF_IO_FQDN__'] = 'Define'
    # No port for __IO_FQDN__

    user_dict['__IFDEF_OPENID_ADDRESS__'] = 'UnDefine'
    if user_dict['__OPENID_ADDRESS__']:
        user_dict['__IFDEF_OPENID_ADDRESS__'] = 'Define'
    elif user_dict['__IO_FQDN__']:
        user_dict['__IFDEF_OPENID_ADDRESS__'] = 'Define'

    # Enable mercurial module in trackers if Trac is available
    user_dict['__HG_COMMENTED__'] = '#'
    if user_dict['__HG_PATH__']:
        user_dict['__HG_COMMENTED__'] = ''

    # TODO: switch to test input values directly now that they are bool?
    #       like e.g. in if enable_wsgi: BLA

    # Enable WSGI web interface only if explicitly requested
    if enable_wsgi:
        # WSGI shares auth and bin and only discriminates in backend
        xgi_bin = xgi_auth = 'wsgi-bin'
        user_dict['__WSGI_COMMENTED__'] = ''
        # Switch between python 2 and 3 wsgi module on request
        if prefer_python3:
            user_dict['__WSGI_PY3_COMMENTED__'] = ''
            user_dict['__WSGI_PY2_COMMENTED__'] = '#'
        else:
            user_dict['__WSGI_PY2_COMMENTED__'] = ''
            user_dict['__WSGI_PY3_COMMENTED__'] = '#'
    else:
        xgi_bin = 'cgi-bin'
        xgi_auth = 'cgi-auth'
        user_dict['__WSGI_COMMENTED__'] = '#'
        user_dict['__WSGI_PY2_COMMENTED__'] = '#'
        user_dict['__WSGI_PY3_COMMENTED__'] = '#'

    # Enable HSTS security improvement only if explicitly requested
    if user_dict['__ENABLE_HSTS__'].lower() == 'true':
        user_dict['__HSTS_COMMENTED__'] = ''
    else:
        user_dict['__HSTS_COMMENTED__'] = '#'

    # Enable vhost-specific certificates only if explicitly requested
    if user_dict['__ENABLE_VHOST_CERTS__'].lower() == 'true':
        user_dict['__VHOSTCERTS_COMMENTED__'] = ''
    else:
        user_dict['__VHOSTCERTS_COMMENTED__'] = '#'

    # Enable certificate verification only if explicitly requested
    if user_dict['__ENABLE_VERIFY_CERTS__'].lower() == 'true':
        user_dict['__IS_VERIFYCERTS_COMMENTED__'] = ''
        user_dict['__NOT_VERIFYCERTS_COMMENTED__'] = '#'
    else:
        user_dict['__IS_VERIFYCERTS_COMMENTED__'] = '#'
        user_dict['__NOT_VERIFYCERTS_COMMENTED__'] = ''

    if user_dict['__ENABLE_SFTP__'].lower() == 'true':
        fail2ban_daemon_ports.append(sftp_port)
        if sftp_show_port:
            fail2ban_daemon_ports.append(sftp_show_port)
    if user_dict['__ENABLE_SFTP_SUBSYS__'].lower() == 'true':
        fail2ban_daemon_ports.append(sftp_subsys_port)
        if sftp_show_port:
            fail2ban_daemon_ports.append(sftp_show_port)
    if user_dict['__ENABLE_FTPS__'].lower() == 'true':
        fail2ban_daemon_ports.append(ftps_ctrl_port)
        if ftps_ctrl_show_port:
            fail2ban_daemon_ports.append(ftps_ctrl_show_port)
    if user_dict['__ENABLE_DAVS__'].lower() == 'true':
        fail2ban_daemon_ports.append(davs_port)
        if davs_show_port:
            fail2ban_daemon_ports.append(davs_show_port)

    user_dict['__SEAFILE_TIMEZONE__'] = options['timezone']

    if seafile_secret == keyword_auto:
        seafile_secret = ensure_native_string(
            base64.b64encode(os.urandom(32))).lower()
    user_dict['__SEAFILE_SECRET_KEY__'] = seafile_secret

    if seafile_ccnetid == keyword_auto:
        seafile_ccnetid = ensure_native_string(
            base64.b64encode(os.urandom(20))).lower()
    user_dict['__SEAFILE_CCNET_ID__'] = seafile_ccnetid

    user_dict['__SEAFILE_SHORT_NAME__'] = short_title.replace(' ', '-')
    # IMPORTANT: we discriminate on local and remote seafile service
    #            for local ones we partly integrate directly with apache etc.
    #            while for remote we must securely proxy everything.
    # Assume localhost installation by default without need for protection
    seafile_local_instance = True
    seafile_proxy_proto = 'http'
    seafile_proxy_host = '127.0.0.1'
    # These three are the public addresses for the seahub, seafhttp and client
    # sync interfaces
    user_dict['__SEAHUB_URL__'] = '%s' % seafile_base
    user_dict['__SEAFHTTP_URL__'] = 'https://%s%s' % (sid_fqdn, seafhttp_base)
    user_dict['__SEAFILE_URL__'] = 'https://%s%s' % (sid_fqdn, seafile_base)
    user_dict['__SEAFMEDIA_URL__'] = 'https://%s%s' % (
        sid_fqdn, seafmedia_base)
    if not enable_seafile:
        seafile_local_instance = False
    elif seafile_fqdn and seafile_fqdn \
            not in ['127.0.0.1', 'localhost'] + fqdn_list:
        # Require https for all remote seafile host access
        seafile_local_instance = False
        seafile_proxy_proto = 'https'
        seafile_proxy_host = seafile_fqdn
        user_dict['__SEAHUB_URL__'] = 'https://%s%s' % (
            seafile_fqdn, seafile_base)
        user_dict['__SEAFILE_URL__'] = 'https://%s%s' % (seafile_fqdn,
                                                         seafile_base)
        user_dict['__SEAFMEDIA_URL__'] = 'https://%s%s' % (seafile_fqdn,
                                                           seafmedia_base)
        user_dict['__SEAFHTTP_URL__'] = 'https://%s%s' % (seafile_fqdn,
                                                          seafhttp_base)

    user_dict['__SEAFILE_LOCAL_INSTANCE__'] = "%s" % (seafile_local_instance)

    # These two are used for internal proxying of the backends in apache
    seahub_proxy_host_port = seafhttp_proxy_host_port = seafile_proxy_host
    if seafile_local_instance:
        seahub_proxy_host_port += ':%d' % seafile_seahub_port
        seafhttp_proxy_host_port += ':%d' % seafile_seafhttp_port
        # NOTE: local seafhttp maps to URL root without /seafhttp suffix
        seafhttp_proxy_base = ''
    else:
        seafhttp_proxy_base = seafhttp_base

    user_dict['__SEAFILE_PROXY_URL__'] = '%s://%s%s' % (
        seafile_proxy_proto, seahub_proxy_host_port, seafile_base)
    user_dict['__SEAFMEDIA_PROXY_URL__'] = '%s://%s%s' % (
        seafile_proxy_proto, seahub_proxy_host_port, seafmedia_base)
    user_dict['__SEAFHTTP_PROXY_URL__'] = '%s://%s%s' % (
        seafile_proxy_proto, seafhttp_proxy_host_port, seafhttp_proxy_base)

    user_dict['__SEAFILE_COMMENTED__'] = '#'
    user_dict['__SEAFILE_LOCAL_COMMENTED__'] = '#'
    user_dict['__SEAFILE_REMOTE_COMMENTED__'] = '#'
    # Enable Seafile integration only if explicitly requested
    if user_dict['__ENABLE_SEAFILE__'].lower() == 'true':
        user_dict['__SEAFILE_COMMENTED__'] = ''
        # Always requires reverse http proxy
        user_dict['__PROXY_HTTP_COMMENTED__'] = ''
        if seafile_local_instance:
            # Disable comment for local-only rules
            user_dict['__SEAFILE_REMOTE_COMMENTED__'] = ''
            # Add fail2ban target ports
            fail2ban_daemon_ports.append(seafile_seahub_port)
            fail2ban_daemon_ports.append(seafile_seafhttp_port)
        else:
            # Disable comment for remote-only rules
            user_dict['__SEAFILE_LOCAL_COMMENTED__'] = ''
            # Remote Seafile additionally requires reverse *https* proxy
            user_dict['__PROXY_HTTPS_COMMENTED__'] = ''

    # Default IO daemons to listen on io_fqdn unless explicitly overriden
    all_io_fqdns = []
    if io_fqdn:
        all_io_fqdns.append(io_fqdn)
    for daemon_prefix in ('OPENID', 'SFTP', 'SFTP_SUBSYS', 'FTPS', 'DAVS'):
        address_field = '__%s_ADDRESS__' % daemon_prefix
        daemon_address = user_dict[address_field]
        if daemon_address:
            if not daemon_address in all_io_fqdns:
                all_io_fqdns.append(daemon_address)
        elif io_fqdn:
            user_dict[address_field] = io_fqdn
    user_dict['__ALL_IO_FQDNS__'] = ' '.join(all_io_fqdns)

    # Enable alternative show ports only if explicitly requested.
    # Default is handled in configuration if the option is unset.

    user_dict['__SHOW_SFTP_PORT_COMMENTED__'] = '#'
    user_dict['__SHOW_DAVS_PORT_COMMENTED__'] = '#'
    user_dict['__SHOW_FTPS_CTRL_PORT_COMMENTED__'] = '#'
    user_dict['__SHOW_OPENID_PORT_COMMENTED__'] = '#'
    if sftp_show_port:
        user_dict['__SHOW_SFTP_PORT_COMMENTED__'] = ''
    if davs_show_port:
        user_dict['__SHOW_DAVS_PORT_COMMENTED__'] = ''
    if ftps_ctrl_show_port:
        user_dict['__SHOW_FTPS_CTRL_PORT_COMMENTED__'] = ''
    if openid_show_port:
        user_dict['__SHOW_OPENID_PORT_COMMENTED__'] = ''
    user_dict['__SFTP_SHOW_PORT__'] = "%s" % sftp_show_port
    user_dict['__DAVS_SHOW_PORT__'] = "%s" % davs_show_port
    user_dict['__FTPS_CTRL_SHOW_PORT__'] = "%s" % ftps_ctrl_show_port
    user_dict['__OPENID_SHOW_PORT__'] = "%s" % openid_show_port

    user_dict['__PREFER_HTTPS_COMMENTED__'] = '#'
    if public_use_https:
        user_dict['__PREFER_HTTPS_COMMENTED__'] = ''

    if user_dict['__ENABLE_JUPYTER__'].lower() == 'true':
        try:
            import requests
        except ImportError:
            print("ERROR: jupyter use requested but requests is not installed!")
            sys.exit(1)
        user_dict['__JUPYTER_COMMENTED__'] = ''
        # Jupyter requires websockets proxy
        user_dict['__WEBSOCKETS_COMMENTED__'] = ''

        # Dynamic apache configuration replacement lists
        jupyter_sections, jupyter_proxies, jupyter_defs = [], [], []
        jupyter_openids, jupyter_oidcs, jupyter_rewrites = [], [], []
        services = user_dict['__JUPYTER_SERVICES__'].split()

        try:
            descs = ast.literal_eval(jupyter_services_desc)
        except SyntaxError as err:
            print('Error: jupyter_services_desc '
                  'could not be intepreted correctly. Double check that your '
                  'formatting is correct, a dictionary formatted string is expected.')
            sys.exit(1)

        if not isinstance(descs, dict):
            print('Error: %s was incorrectly formatted,'
                  ' expects a string formatted as a dictionary' % descs)
            sys.exit(1)

        service_hosts = {}
        for service in services:
            # TODO, do more checks on format
            name_hosts = service.split(".", 1)
            if len(name_hosts) != 2:
                print('Error: You have not correctly formattet '
                      'the jupyter_services parameter, '
                      'expects --jupyter_services="service_name.'
                      'http(s)://jupyterhost-url-or-ip '
                      'other_service.http(s)://jupyterhost-url-or-ip"')
                sys.exit(1)
            name, host = name_hosts[0], name_hosts[1]
            try:
                valid_alphanumeric(name)
            except InputException as err:
                print('Error: The --jupyter_services name: %s was incorrectly '
                      'formatted, only allows alphanumeric characters %s' % (name,
                                                                             err))
            if name and host:
                if name not in service_hosts:
                    service_hosts[name] = {'hosts': []}
                service_hosts[name]['hosts'].append(host)

        for name, values in service_hosts.items():
            # Service definitions
            u_name = name.upper()
            url = '/' + name
            definition = 'Define'
            def_name = '%s_URL' % u_name
            def_value = url
            new_def = "%s %s %s\n" % (definition, def_name, def_value)
            if new_def not in jupyter_defs:
                jupyter_defs.append(new_def)

            # Prepare MiG conf template for jupyter sections
            section_header = '[__JUPYTER_%s__]\n' % u_name
            section_name = 'service_name=__JUPYTER_%s_NAME__\n' % u_name
            section_desc = 'service_desc=__JUPYTER_%s_DESC__\n' % u_name
            section_hosts = 'service_hosts=__JUPYTER_%s_HOSTS__\n' % u_name

            for section_item in (section_header, section_name, section_desc,
                                 section_hosts):
                if section_item not in jupyter_sections:
                    jupyter_sections.append(section_item)

            user_values = {
                '__JUPYTER_%s__' % u_name: 'JUPYTER_%s' % u_name,
                '__JUPYTER_%s_NAME__' % u_name: name,
                '__JUPYTER_%s_HOSTS__' % u_name: ' '.join(values['hosts'])
            }

            if name in descs:
                desc_value = descs[name] + "\n"
            else:
                desc_value = "\n"

            user_values.update({'__JUPYTER_%s_DESC__\n' % u_name: desc_value})

            # Update user_dict with definition values
            for u_k, u_v in user_values.items():
                if u_k not in user_dict:
                    user_dict[u_k] = u_v

            # Setup apache openid 2.0 and openid connect template
            openid_template = gen_openid_template(url, def_name,
                                                  auth_type="OpenID")
            jupyter_openids.append(openid_template)
            oidc_template = gen_openid_template(url, def_name,
                                                auth_type="openid-connect")
            jupyter_oidcs.append(oidc_template)

            # Setup apache rewrite template
            rewrite_template = gen_rewrite_template(url, def_name, name)
            jupyter_rewrites.append(rewrite_template)

            hosts, ws_hosts = [], []
            # Populate apache confs with hosts definitions and balancer members
            for i_h, host in enumerate(values['hosts']):
                name_index = '%s_%s' % (u_name, i_h)
                # https://httpd.apache.org/docs/2.4/mod/mod_proxy.html
                member = "BalancerMember %s route=%s retry=600 timeout=120 keepalive=On connectiontimeout=120\n" \
                    % ("${JUPYTER_%s}" % name_index, i_h)
                ws_member = member.replace("${JUPYTER_%s}" % name_index,
                                           "${WS_JUPYTER_%s}" % name_index)
                hosts.append(member)
                ws_hosts.append(ws_member)

                ws_host = host.replace(
                    "https://", "wss://").replace("http://", "ws://")
                member_def = "Define JUPYTER_%s %s" % (name_index, host)
                ws_member_def = "Define WS_JUPYTER_%s %s" % (name_index,
                                                             ws_host)

                # No user supplied port, assign based on url prefix
                if len(host.split(":")) < 3:
                    if host.startswith("https://"):
                        member_def += ":443\n"
                        ws_member_def += ":443\n"
                    else:
                        member_def += ":80\n"
                        ws_member_def += ":80\n"
                else:
                    # Else, use the user provided port
                    port = host.split(":")[2]
                    member_def += ":%s\n" % port
                    ws_member_def += ":%s\n" % port

                jupyter_defs.extend([member_def, ws_member_def])
            # Get proxy template and append to template conf
            proxy_template = gen_balancer_proxy_template(url, def_name, name,
                                                         hosts, ws_hosts)
            jupyter_proxies.append(proxy_template)

        user_dict['__JUPYTER_DEFS__'] = '\n'.join(jupyter_defs)
        user_dict['__JUPYTER_OPENIDS__'] = '\n'.join(jupyter_openids)
        user_dict['__JUPYTER_OIDCS__'] = '\n'.join(jupyter_oidcs)
        user_dict['__JUPYTER_REWRITES__'] = '\n'.join(jupyter_rewrites)
        user_dict['__JUPYTER_PROXIES__'] = '\n'.join(jupyter_proxies)
        user_dict['__JUPYTER_SECTIONS__'] = ''.join(jupyter_sections)

    else:
        user_dict['__JUPYTER_COMMENTED__'] = '#'

    if user_dict['__ENABLE_CLOUD__'].lower() == 'true':
        try:
            import openstack
        except ImportError:
            print("ERROR: cloud use requested but openstack is not installed!")
            sys.exit(1)
        user_dict['__CLOUD_COMMENTED__'] = ''

        # Dynamic apache configuration replacement lists
        cloud_sections = []
        cloud_services = user_dict['__CLOUD_SERVICES__'].split()

        try:
            descs = ast.literal_eval(cloud_services_desc)
        except SyntaxError as err:
            print('Error: cloud_services_desc '
                  'could not be intepreted correctly. Double check that your '
                  'formatting is correct, a dictionary formatted string is expected.')
            sys.exit(1)

        if not isinstance(descs, dict):
            print('Error: %s was incorrectly formatted,'
                  ' expects a string formatted as a dictionary' % descs)
            sys.exit(1)

        cloud_service_hosts = {}
        for service in cloud_services:
            # TODO: do more checks on format?
            name_hosts = service.split(".", 1)
            if len(name_hosts) != 2:
                print('Error: You have not correctly formattet '
                      'the cloud_services parameter, '
                      'expects --cloud_services="service_name.'
                      'http(s)://cloudhost-url-or-ip '
                      'other_service.http(s)://cloudhost-url-or-ip"')
                sys.exit(1)
            name, host = name_hosts[0], name_hosts[1]
            try:
                valid_alphanumeric(name)
            except InputException as err:
                print('Error: The --cloud_services name: %s was incorrectly '
                      'formatted, only allows alphanumeric characters %s' % (name,
                                                                             err))
            if name and host:
                if name not in cloud_service_hosts:
                    cloud_service_hosts[name] = {'hosts': []}
                cloud_service_hosts[name]['hosts'].append(host)

        for name, values in cloud_service_hosts.items():
            # Service definitions
            u_name = name.upper()

            # Prepare MiG conf template for cloud sections
            section_header = '[__CLOUD_%s__]\n' % u_name
            section_name = 'service_name=__CLOUD_%s_NAME__\n' % u_name
            section_desc = 'service_desc=__CLOUD_%s_DESC__\n' % u_name
            section_hosts = 'service_hosts=__CLOUD_%s_HOSTS__\n' % u_name

            for section_item in (section_header, section_name, section_desc,
                                 section_hosts):
                if section_item not in cloud_sections:
                    cloud_sections.append(section_item)

            user_values = {
                '__CLOUD_%s__' % u_name: 'CLOUD_%s' % u_name,
                '__CLOUD_%s_NAME__' % u_name: name,
                '__CLOUD_%s_HOSTS__' % u_name: ' '.join(values['hosts'])
            }

            if name in descs:
                desc_value = descs[name] + "\n"
            else:
                desc_value = "\n"

            user_values.update({'__CLOUD_%s_DESC__\n' % u_name: desc_value})

            # Update user_dict with definition values
            for u_k, u_v in user_values.items():
                if u_k not in user_dict:
                    user_dict[u_k] = u_v

        user_dict['__CLOUD_SECTIONS__'] = ''.join(cloud_sections)
    else:
        user_dict['__CLOUD_COMMENTED__'] = '#'

    # Enable Duplicati integration only if explicitly requested
    if user_dict['__ENABLE_DUPLICATI__'].lower() == 'true':
        user_dict['__DUPLICATI_COMMENTED__'] = ''
    else:
        user_dict['__DUPLICATI_COMMENTED__'] = '#'

    # Enable Paraview integration only if explicitly requested
    if user_dict['__ENABLE_PREVIEW__'].lower() == 'true':
        user_dict['__PREVIEW_COMMENTED__'] = ''
        # Paraview requires websockets and http proxy
        user_dict['__WEBSOCKETS_COMMENTED__'] = ''
        user_dict['__PROXY_HTTP_COMMENTED__'] = ''
    else:
        user_dict['__PREVIEW_COMMENTED__'] = '#'

    dev_suffix = '$(echo ${APACHE_CONFDIR} | sed "s@/etc/${APACHE_DAEMON}@@")'
    if user_dict['__ENABLE_DEV_ACCOUNTS__'].lower() == "true":
        user_dict['__APACHE_SUFFIX__'] = dev_suffix
    else:
        user_dict['__APACHE_SUFFIX__'] = ""

    # Helpers for the migstatecleanup cron job
    user_dict['__CRON_VERBOSE_CLEANUP__'] = '1'
    user_dict['__CRON_EVENT_CLEANUP__'] = '1'
    if 'migoid' in signup_methods or 'migcert' in signup_methods:
        user_dict['__CRON_REQ_CLEANUP__'] = '1'
    else:
        user_dict['__CRON_REQ_CLEANUP__'] = '0'

    if user_dict['__ENABLE_JOBS__'].lower() == 'true':
        user_dict['__CRON_JOB_CLEANUP__'] = '1'
    else:
        user_dict['__CRON_JOB_CLEANUP__'] = '0'
    user_dict['__CRON_SESSION_CLEANUP__'] = ''
    if user_dict['__ENABLE_SFTP_SUBSYS__'].lower() == 'true' or \
            user_dict['__ENABLE_SFTP__'].lower() == 'true':
        user_dict['__CRON_SESSION_CLEANUP__'] += "sftp "
    if user_dict['__ENABLE_DAVS__'].lower() == 'true':
        user_dict['__CRON_SESSION_CLEANUP__'] += "davs "
    if user_dict['__ENABLE_FTPS__'].lower() == 'true':
        user_dict['__CRON_SESSION_CLEANUP__'] += "ftps "
    user_dict['__CRON_SESSION_CLEANUP__'] \
        = user_dict['__CRON_SESSION_CLEANUP__'].strip()

    # Enable 2FA only if explicitly requested
    if user_dict['__ENABLE_TWOFACTOR__'].lower() == 'true':
        try:
            import pyotp
        except ImportError:
            print("ERROR: twofactor use requested but pyotp is not installed!")
            sys.exit(1)
        user_dict['__TWOFACTOR_COMMENTED__'] = ''
        user_dict['__CRON_TWOFACTOR_CLEANUP__'] = '1'
    else:
        user_dict['__TWOFACTOR_COMMENTED__'] = '#'
        user_dict['__CRON_TWOFACTOR_CLEANUP__'] = '0'

    # Enable 2FA mandatory protos only if explicitly requested
    if user_dict['__TWOFACTOR_MANDATORY_PROTOS__'].lower().strip():
        if not user_dict['__ENABLE_TWOFACTOR__'].lower() == 'true':
            print("ERROR: twofactor mandatory protos requested"
                  + " but twofactor is disabled!")
            sys.exit(1)

    # Enable 2FA strict address only if explicitly requested
    if user_dict['__ENABLE_TWOFACTOR_STRICT_ADDRESS__'].lower() == 'true':
        if not user_dict['__ENABLE_TWOFACTOR__'].lower() == 'true':
            print("ERROR: twofactor strict address use requested"
                  + " but twofactor is disabled!")
            sys.exit(1)
        user_dict['__TWOFACTOR_STRICT_ADDRESS_COMMENTED__'] = ''
    else:
        user_dict['__TWOFACTOR_STRICT_ADDRESS_COMMENTED__'] = '#'

    # Enable cracklib only if explicitly requested and installed
    if user_dict['__ENABLE_CRACKLIB__'].lower() == 'true':
        try:
            import cracklib
        except ImportError:
            print("ERROR: cracklib use requested but lib is not installed!")
            sys.exit(1)

    # Enable events daemon only if requested and deps are installed
    if user_dict['__ENABLE_WORKFLOWS__'].lower() == 'true':
        try:
            import nbformat
        except ImportError:
            print("ERROR: workflows use requested but "
                  "nbformat is not installed!")
            sys.exit(1)
        except SyntaxError:
            print("ERROR: workflows requires that the more-itertools package"
                  "is installed as version 5.0.0")
            sys.exit(1)
        try:
            import nbconvert
        except ImportError:
            print("ERROR: workflows use requested but "
                  "nbconvert is not installed!")
            sys.exit(1)

    # Enable events daemon only if requested and deps are installed
    if user_dict['__ENABLE_EVENTS__'].lower() == 'true':
        try:
            import watchdog
        except ImportError:
            print("ERROR: events use requested but watchdog is not installed!")
            sys.exit(1)

    # Enable OpenID auth daemon only if requested and installed
    if user_dict['__ENABLE_OPENID__'].lower() == 'true':
        try:
            import openid
        except ImportError:
            print("ERROR: openid use requested but lib is not installed!")
            sys.exit(1)
    # Enable OpenID 2.0 auth module only if openid_providers is given
    if user_dict['__EXT_OID_PROVIDER_BASE__'].strip() or \
            user_dict['__MIG_OID_PROVIDER_BASE__'].strip():
        user_dict['__OPENID_COMMENTED__'] = ''
        # Requires reverse http(s) proxy
        user_dict['__PROXY_HTTP_COMMENTED__'] = ''
        user_dict['__PROXY_HTTPS_COMMENTED__'] = ''
        fail2ban_daemon_ports.append(openid_port)
        if openid_show_port:
            fail2ban_daemon_ports.append(openid_show_port)
    else:
        user_dict['__OPENID_COMMENTED__'] = '#'
    mig_issuer_url, ext_issuer_url = '', ''
    issuer_split_mark = '/.well-known/'
    # Enable OpenID Connect auth module only if OpenID Connect providers are
    # given with meta service interface or explicitly.
    if user_dict['__EXT_OIDC_PROVIDER_META_URL__'].strip() or \
       user_dict['__EXT_OIDC_PROVIDER_ISSUER__'].strip() or \
            user_dict['__MIG_OIDC_PROVIDER_META_URL__'].strip():
        user_dict['__OPENIDCONNECT_COMMENTED__'] = ''
        if user_dict['__MIG_OIDC_PROVIDER_META_URL__'].strip():
            meta_url = user_dict['__MIG_OIDC_PROVIDER_META_URL__'].strip()
            if issuer_split_mark in meta_url:
                mig_issuer_url = meta_url.split(issuer_split_mark, 1)[0]
            else:
                parsed = urlparse(meta_url)
                mig_issuer_url = "%s://%s" % (parsed.scheme, parsed.netloc)
        # NOTE: prefer explictly provided issuer but fallback to meta parsing
        if user_dict['__EXT_OIDC_PROVIDER_ISSUER__'].strip():
            ext_issuer_url = user_dict['__EXT_OIDC_PROVIDER_ISSUER__']
        elif user_dict['__EXT_OIDC_PROVIDER_META_URL__'].strip():
            meta_url = user_dict['__EXT_OIDC_PROVIDER_META_URL__'].strip()
            if issuer_split_mark in meta_url:
                ext_issuer_url = meta_url.split(issuer_split_mark, 1)[0]
            else:
                parsed = urlparse(meta_url)
                ext_issuer_url = "%s://%s" % (parsed.scheme, parsed.netloc)

        # TODO: enable next lines if openid connect requires proxy for
        #       cert_redirect support
        # user_dict['__PROXY_HTTP_COMMENTED__'] = ''
        # user_dict['__PROXY_HTTPS_COMMENTED__'] = ''
        # TODO: enable next lines if implementing native openid connect service
        # fail2ban_daemon_ports.append(openidconnect_port)
        # if openidconnect_show_port:
        #     fail2ban_daemon_ports.append(openidconnect_show_port)
    else:
        user_dict['__OPENIDCONNECT_COMMENTED__'] = '#'

    user_dict['__MIG_OIDC_ISSUER_URL__'] = mig_issuer_url
    user_dict['__EXT_OIDC_ISSUER_URL__'] = ext_issuer_url

    optional_oidc_args = [
        ('__EXT_OIDC_PROVIDER_META_URL__', ext_oidc_provider_meta_url),
        ('__EXT_OIDC_PROVIDER_ISSUER__', ext_oidc_provider_issuer),
        ('__EXT_OIDC_PROVIDER_AUTHORIZATION_ENDPOINT__',
         ext_oidc_provider_authorization_endpoint),
        ('__EXT_OIDC_PROVIDER_VERIFY_CERT_FILES__',
         ext_oidc_provider_verify_cert_files),
        ('__EXT_OIDC_PROVIDER_TOKEN_ENDPOINT__', ext_oidc_provider_token_endpoint),
        ('__EXT_OIDC_PROVIDER_TOKEN_ENDPOINT_AUTH__',
         ext_oidc_provider_token_endpoint_auth),
        ('__EXT_OIDC_PROVIDER_USER_INFO_ENDPOINT__',
         ext_oidc_provider_user_info_endpoint),
        ('__EXT_OIDC_SCOPE__', ext_oidc_scope),
        ('__EXT_OIDC_USER_INFO_TOKEN_METHOD__', ext_oidc_user_info_token_method),
        ('__EXT_OIDC_PUBLIC_KEY_FILES__', ext_oidc_public_key_files),
        ('__EXT_OIDC_PRIVATE_KEY_FILES__', ext_oidc_private_key_files),
        ('__EXT_OIDC_RESPONSE_TYPE__', ext_oidc_response_type),
        ('__EXT_OIDC_RESPONSE_MODE__', ext_oidc_response_mode),
        ('__EXT_OIDC_CLIENT_ID__', ext_oidc_client_id),
        ('__EXT_OIDC_CLIENT_NAME__', ext_oidc_client_name),
        ('__EXT_OIDC_PKCE_METHOD__', ext_oidc_pkce_method),
        ('__EXT_OIDC_ID_TOKEN_ENCRYPTED_RESPONSE_ALG__',
         ext_oidc_id_token_encrypted_response_alg),
        ('__EXT_OIDC_ID_TOKEN_ENCRYPTED_RESPONSE_ENC__',
         ext_oidc_id_token_encrypted_response_enc),
        ('__EXT_OIDC_USER_INFO_SIGNED_RESPONSE_ALG__',
         ext_oidc_user_info_signed_response_alg),
        ('__EXT_OIDC_COOKIE_SAME_SITE__', ext_oidc_cookie_same_site),
        ('__EXT_OIDC_PASS_COOKIES__', ext_oidc_pass_cookies),
        ('__EXT_OIDC_REMOTE_USER_CLAIM__', ext_oidc_remote_user_claim),
        ('__EXT_OIDC_PASS_CLAIM_AS__', ext_oidc_pass_claim_as),
        ('__EXT_OIDC_REWRITE_COOKIE__', ext_oidc_rewrite_cookie),
    ]
    for (arg_name, arg_value) in optional_oidc_args:
        commented_tag = '%s_COMMENTED__' % arg_name.rstrip('_')
        user_dict[commented_tag] = '#'
        if arg_value:
            user_dict[commented_tag] = ''

    # Enable alternative daemon show address only if explicitly requested
    user_dict['__SHOW_IO_ADDRESS_COMMENTED__'] = '#'
    user_dict['__DAEMON_SHOW_ADDRESS__'] = ''
    if daemon_show_address:
        user_dict['__SHOW_IO_ADDRESS_COMMENTED__'] = ''
        user_dict['__DAEMON_SHOW_ADDRESS__'] = daemon_show_address

    # Enable openid proxy if implicitly requested with different OID provider
    user_dict['__SHOW_OPENID_ADDRESS_COMMENTED__'] = '#'
    if openid_address not in mig_oid_provider:
        user_dict['__SHOW_OPENID_ADDRESS_COMMENTED__'] = ''

    # Enable dhparams only if explicitly requested and file available
    if user_dict['__DHPARAMS_PATH__']:
        if not os.path.isfile(os.path.expanduser("%(__DHPARAMS_PATH__)s" %
                                                 user_dict)):
            print("ERROR: requested dhparams file not found!")
            print("""You can download a pre-generated strong one from
https://ssl-config.mozilla.org/ffdhe4096.txt
and save it into %(__DHPARAMS_PATH__)s or generate a unique one with:
openssl dhparam 2048 -out %(__DHPARAMS_PATH__)s""" % user_dict)
            sys.exit(1)

    # Auto-fill fingerprints if daemon key is set with AUTO fingerprint
    if user_dict['__DAEMON_KEYCERT__']:
        if not os.path.isfile(os.path.expanduser("%(__DAEMON_KEYCERT__)s" %
                                                 user_dict)):
            print("ERROR: requested daemon keycert file not found!")
            print("""You can create it e.g. with:
openssl genrsa -out %(__DAEMON_KEYCERT__)s 4096""" % user_dict)
            sys.exit(1)
    else:
        user_dict['__DAEMON_KEYCERT_SHA256__'] = ''

    if user_dict['__DAEMON_KEYCERT__'] and keyword_auto in \
            (daemon_keycert_sha256, ):
        key_path = os.path.expanduser(user_dict['__DAEMON_KEYCERT__'])
        openssl_cmd = ["openssl", "x509", "-noout", "-fingerprint", "-sha256",
                       "-in", key_path]
        try:
            openssl_proc = subprocess_popen(
                openssl_cmd, stdout=subprocess_pipe)
            # NOTE: subprocess output is expected to follow sys encoding
            raw_sha256 = force_native_str(openssl_proc.stdout.read()).strip()
            # NOTE: openssl outputs something like 'SHA256 Fingerprint=BLA'
            #       but algo part case may vary - split and take last part.
            cur_keycert_sha256 = raw_sha256.split(" Fingerprint=", 1)[-1]
        except Exception as exc:
            print("ERROR: failed to extract sha256 fingerprint of %s: %s" %
                  (key_path, exc))
            cur_keycert_sha256 = ''
        if daemon_keycert_sha256 == keyword_auto:
            user_dict['__DAEMON_KEYCERT_SHA256__'] = cur_keycert_sha256
    if user_dict['__DAEMON_PUBKEY__']:
        if not os.path.isfile(os.path.expanduser("%(__DAEMON_PUBKEY__)s" %
                                                 user_dict)):
            print("ERROR: requested daemon pubkey file not found!")
            print("""You can create it with:
ssh-keygen -f %(__DAEMON_KEYCERT__)s -y > %(__DAEMON_PUBKEY__)s""" % user_dict)
            sys.exit(1)
    else:
        user_dict['__DAEMON_PUBKEY_MD5__'] = ''
        user_dict['__DAEMON_PUBKEY_SHA256__'] = ''

    if user_dict['__DAEMON_PUBKEY__'] and keyword_auto in \
            (daemon_pubkey_md5, daemon_pubkey_sha256):
        pubkey_path = os.path.expanduser(user_dict['__DAEMON_PUBKEY__'])
        pubkey = read_file(pubkey_path, None)
        if pubkey is None:
            print("Failed to read provided daemon key: %s" % pubkey_path)
        # The desired values are hashes of the base64 encoded actual key
        try:
            # NOTE: b64decode takes bytes or string and returns bytes
            b64_key = base64.b64decode(pubkey.strip().split()[1])
            raw_md5 = make_simple_hash(b64_key)
            # reformat into colon-spearated octets
            cur_pubkey_md5 = ':'.join(a + b for a, b in zip(raw_md5[::2],
                                                            raw_md5[1::2]))
            raw_sha256 = make_safe_hash(b64_key, False)
            # NOTE: b64encode takes bytes and returns bytes
            cur_pubkey_sha256 = force_native_str(
                base64.b64encode(raw_sha256)).rstrip('=')
        except Exception as exc:
            print("ERROR: failed to extract fingerprints of %s : %s" %
                  (pubkey_path, exc))
            cur_pubkey_md5 = ''
            cur_pubkey_sha256 = ''
        if daemon_pubkey_md5 == keyword_auto:
            user_dict['__DAEMON_PUBKEY_MD5__'] = cur_pubkey_md5
        if daemon_pubkey_sha256 == keyword_auto:
            user_dict['__DAEMON_PUBKEY_SHA256__'] = cur_pubkey_sha256

    # Enable Debian/Ubuntu specific lines only there
    if user_dict['__DISTRO__'].lower() in ('ubuntu', 'debian'):
        user_dict['__NOT_DEB_COMMENTED__'] = ''
        user_dict['__IS_DEB_COMMENTED__'] = '#'
        user_dict['__APACHE_DAEMON__'] = 'apache2'
    else:
        user_dict['__NOT_DEB_COMMENTED__'] = '#'
        user_dict['__IS_DEB_COMMENTED__'] = ''
        user_dict['__APACHE_DAEMON__'] = 'httpd'

    # Only set ID sub url if any openid provider(s) is set
    # IMPORTANT: trailing slash matters!
    all_oid_provider_ids = []
    if user_dict['__MIG_OID_PROVIDER_BASE__']:
        mig_oid_provider_id = os.path.join(mig_oid_provider, 'id') + os.sep
        user_dict['__MIG_OID_PROVIDER_ID__'] = mig_oid_provider_id
        all_oid_provider_ids.append(mig_oid_provider_id)
    if user_dict['__EXT_OID_PROVIDER_BASE__']:
        ext_oid_provider_id = os.path.join(ext_oid_provider, 'id') + os.sep
        user_dict['__EXT_OID_PROVIDER_ID__'] = ext_oid_provider_id
        all_oid_provider_ids.append(ext_oid_provider_id)
    user_dict['__ALL_OID_PROVIDER_IDS__'] = ' '.join(all_oid_provider_ids)
    all_oidc_provider_meta_urls = []
    if user_dict['__MIG_OIDC_PROVIDER_META_URL__']:
        all_oidc_provider_meta_urls.append(mig_oidc_provider_meta_url)
    if user_dict['__EXT_OIDC_PROVIDER_META_URL__']:
        all_oidc_provider_meta_urls.append(ext_oidc_provider_meta_url)
    user_dict['__ALL_OIDC_PROVIDER_META_URLS__'] = ' '.join(
        all_oidc_provider_meta_urls)

    destination = options['destination_link']
    if not os.path.islink(destination) and os.path.isdir(destination):
        print("ERROR: Legacy %s dir in the way - please remove first" %
              destination)
        sys.exit(1)

    destination_path = options['destination_dir']
    try:
        os.makedirs(destination_path)
    except OSError:
        pass
    try:
        if os.path.lexists(destination):
            os.remove(destination)
        os.symlink(destination_path, destination)
    except OSError:
        pass

    # Implicit ports if they are standard: cleaner and removes double hg login
    if public_fqdn:
        user_dict['__PUBLIC_HTTP_URL__'] = 'http://%(__PUBLIC_FQDN__)s' % user_dict
        if "%s" % public_http_port != "%s" % default_http_port:
            print("adding explicit public port (%s)" % [public_http_port,
                                                        default_http_port])
            user_dict['__PUBLIC_HTTP_URL__'] += ':%(__PUBLIC_HTTP_PORT__)s' % user_dict
        if public_use_https:
            user_dict['__PUBLIC_HTTPS_URL__'] = 'https://%(__PUBLIC_SEC_FQDN__)s' \
                % user_dict
            if "%s" % public_https_port != "%s" % default_https_port:
                print("adding explicit public https port (%s)" %
                      [public_https_port, default_https_port])
                user_dict['__PUBLIC_HTTPS_URL__'] += ':%(__PUBLIC_HTTPS_PORT__)s' \
                                                     % user_dict
            user_dict['__PUBLIC_URL__'] = user_dict['__PUBLIC_HTTPS_URL__']
        else:
            user_dict['__PUBLIC_URL__'] = user_dict['__PUBLIC_HTTP_URL__']
            user_dict['__PUBLIC_HTTPS_URL__'] = ''
            user_dict['__PUBLIC_HTTPS_LISTEN__'] = "# %s" % listen_clause
    if public_alias_fqdn:
        user_dict['__PUBLIC_ALIAS_HTTP_URL__'] = 'http://%(__PUBLIC_ALIAS_FQDN__)s' \
            % user_dict
        user_dict['__PUBLIC_ALIAS_HTTPS_URL__'] = 'https://%(__PUBLIC_ALIAS_FQDN__)s' \
            % user_dict
        if "%s" % public_http_port != "%s" % default_http_port:
            print("adding explicit public alias port (%s)" % [public_http_port,
                                                              default_http_port])
            user_dict['__PUBLIC_ALIAS_HTTP_URL__'] += ':%(__PUBLIC_HTTP_PORT__)s' \
                % user_dict
        if "%s" % public_https_port != "%s" % default_https_port:
            print("adding explicit public alias https port (%s)" %
                  [public_https_port, default_https_port])
            user_dict['__PUBLIC_ALIAS_HTTPS_URL__'] += ':%(__PUBLIC_HTTPS_PORT__)s' \
                % user_dict
        if public_use_https:
            user_dict['__PUBLIC_ALIAS_URL__'] = user_dict['__PUBLIC_ALIAS_HTTPS_URL__']
        else:
            user_dict['__PUBLIC_ALIAS_URL__'] = user_dict['__PUBLIC_ALIAS_HTTP_URL__']
        # Apache fails on duplicate listen clauses
        if public_use_https and public_alias_fqdn == public_fqdn:
            user_dict['__PUBLIC_ALIAS_HTTPS_LISTEN__'] = "# %s" % listen_clause
    if status_alias_fqdn:
        # Apache fails on duplicate listen clauses
        if public_use_https and status_alias_fqdn in (public_fqdn,
                                                      public_alias_fqdn):
            user_dict['__STATUS_ALIAS_HTTPS_LISTEN__'] = "# %s" % listen_clause

    if mig_cert_fqdn:
        user_dict['__MIG_CERT_URL__'] = 'https://%(__MIG_CERT_FQDN__)s' % \
            user_dict
        if "%s" % mig_cert_port != "%s" % default_https_port:
            print("adding explicit mig cert port (%s)" % [mig_cert_port,
                                                          default_https_port])
            user_dict['__MIG_CERT_URL__'] += ':%(__MIG_CERT_PORT__)s' % \
                                             user_dict
    if ext_cert_fqdn:
        user_dict['__EXT_CERT_URL__'] = 'https://%(__EXT_CERT_FQDN__)s' % \
            user_dict
        if "%s" % ext_cert_port != "%s" % default_https_port:
            print("adding explicit ext cert port (%s)" % [ext_cert_port,
                                                          default_https_port])
            user_dict['__EXT_CERT_URL__'] += ':%(__EXT_CERT_PORT__)s' % \
                                             user_dict
    if mig_oid_fqdn:
        user_dict['__MIG_OID_URL__'] = 'https://%(__MIG_OID_FQDN__)s' % \
            user_dict
        if "%s" % mig_oid_port != "%s" % default_https_port:
            print("adding explicit ext oid port (%s)" % [mig_oid_port,
                                                         default_https_port])
            user_dict['__MIG_OID_URL__'] += ':%(__MIG_OID_PORT__)s' % user_dict
    if ext_oid_fqdn:
        user_dict['__EXT_OID_URL__'] = 'https://%(__EXT_OID_FQDN__)s' % \
            user_dict
        if "%s" % ext_oid_port != "%s" % default_https_port:
            print("adding explicit org oid port (%s)" % [ext_oid_port,
                                                         default_https_port])
            user_dict['__EXT_OID_URL__'] += ':%(__EXT_OID_PORT__)s' % user_dict
    if mig_oidc_fqdn:
        user_dict['__MIG_OIDC_URL__'] = 'https://%(__MIG_OIDC_FQDN__)s' % \
            user_dict
        if "%s" % ext_oidc_port != "%s" % default_https_port:
            print("adding explicit org oidc port (%s)" % [ext_oidc_port,
                                                          default_https_port])
            user_dict['__MIG_OIDC_URL__'] += ':%(__MIG_OIDC_PORT__)s' % user_dict
    if ext_oidc_fqdn:
        user_dict['__EXT_OIDC_URL__'] = 'https://%(__EXT_OIDC_FQDN__)s' % \
            user_dict
        if "%s" % ext_oidc_port != "%s" % default_https_port:
            print("adding explicit org oidc port (%s)" % [ext_oidc_port,
                                                          default_https_port])
            user_dict['__EXT_OIDC_URL__'] += ':%(__EXT_OIDC_PORT__)s' % user_dict
    if sid_fqdn:
        user_dict['__SID_URL__'] = 'https://%(__SID_FQDN__)s' % user_dict
        if "%s" % sid_port != "%s" % default_https_port:
            print("adding explicit sid port (%s)" % [sid_port,
                                                     default_https_port])
            user_dict['__SID_URL__'] += ':%(__SID_PORT__)s' % user_dict

    if digest_salt == keyword_auto:
        # Generate random hex salt for scrambling saved digest credentials
        # NOTE: b16encode takes bytes and returns bytes
        digest_salt = ensure_native_string(base64.b16encode(os.urandom(16)))
    user_dict['__DIGEST_SALT__'] = digest_salt

    if crypto_salt == keyword_auto:
        # Generate random hex salt for various crypto helpers
        # NOTE: b16encode takes bytes and returns bytes
        crypto_salt = ensure_native_string(base64.b16encode(os.urandom(16)))
    user_dict['__CRYPTO_SALT__'] = crypto_salt

    # Dynamically set ssh subsys auth key locations for enabled site features
    # NOTE: some percent variables must be preserved, namely %h for user home
    #       and %u for user id in ssh login.
    auth_key_locations = ['%h/.ssh/authorized_keys']
    if user_dict['__ENABLE_JOBS__'].lower() == 'true':
        auth_key_locations.append(os.path.join(mig_state, 'mig_system_files',
                                               'job_mount',
                                               '%u.authorized_keys'))
    if user_dict['__ENABLE_JUPYTER__'].lower() == 'true':
        auth_key_locations.append(os.path.join(mig_state, 'mig_system_files',
                                               'jupyter_mount',
                                               '%u.authorized_keys'))
    user_dict['__SSH_AUTH_KEY_LOCATIONS__'] = ' '.join(auth_key_locations)

    user_dict['__TWOFACTOR_PAGE__'] = os.path.join(
        '/', xgi_auth, 'twofactor.py')
    if autolaunch_page is None:
        if enable_gdp:
            backend = 'gdpman.py'
        else:
            backend = 'autolaunch.py'
        user_dict['__AUTOLAUNCH_PAGE__'] = os.path.join(
            '/', xgi_bin, backend)
    else:
        user_dict['__AUTOLAUNCH_PAGE__'] = autolaunch_page
    if landing_page is None:
        if enable_gdp:
            backend = 'gdpman.py'
        else:
            backend = 'home.py'
        user_dict['__LANDING_PAGE__'] = os.path.join(
            '/', xgi_bin, backend)
    else:
        user_dict['__LANDING_PAGE__'] = landing_page

    # Fill list of unique daemon ports to block on Fail2Ban trigger
    # Typically something like '21,22,2222,4443,8000,8020,8021,8082,8443'
    sorted_ports = list(set(fail2ban_daemon_ports))
    sorted_ports.sort()
    # print "fail2ban_daemon_ports %s sorted into %s" % (
    #    fail2ban_daemon_ports, sorted_ports)
    user_dict['__FAIL2BAN_DAEMON_PORTS__'] = ','.join(
        ["%s" % i for i in sorted_ports])

    # Alias vgrid_label variations as aliases for vgrid pub page URL
    vgrid_aliases = [vgrid_label, vgrid_label.lower(), vgrid_label.upper()]
    vgrid_aliases = [i for i in vgrid_aliases if i != 'vgrid']
    user_dict['__VGRID_ALIAS_REGEX__'] = '(%s)' % '|'.join(vgrid_aliases)

    secscan_addr_list = secscan_addr.split()
    secscan_addr_pattern = '(' + '|'.join(secscan_addr_list) + ')'
    user_dict['__SECSCAN_ADDR_PATTERN__'] = secscan_addr_pattern

    if not default_menu:
        default_menu = 'home files submitjob jobs vgrids resources ' \
            'runtimeenvs people settings downloads transfers ' \
            'sharelinks crontab docs logout'
    allow_menu = ' '.join([i for i in default_menu.split() if i in menu_items])
    user_dict['__DEFAULT_MENU__'] = allow_menu
    if not user_menu:
        user_menu = ''
    allow_menu = ' '.join([i for i in user_menu.split() if i in menu_items])
    user_dict['__USER_MENU__'] = allow_menu

    # Collect final variable values for log
    sorted_keys = list(user_dict)
    sorted_keys.sort()
    variable_lines = '\n'.join(["%s : %s" % (i.strip('_'), user_dict[i])
                                for i in sorted_keys])
    user_dict['__GENERATECONFS_VARIABLES__'] = variable_lines

    return user_dict


def _generate_confs_writefiles(options, user_dict, insert_list=[], cleanup_list=[]):
    """Actually write generated confs"""
    assert os.path.isabs(options['destination_dir'])
    assert os.path.isabs(options['template_dir'])

    # Insert lines into templates
    for (temp_file, insert_identifiers) in insert_list:
        template_insert(temp_file, insert_identifiers, unique=True)

    # modify this list when adding/removing template->target
    replacement_list = [
        ("generateconfs-template.log", "generateconfs.log"),
        ("apache-envs-template.conf", "envvars"),
        ("apache-apache2-template.conf", "apache2.conf"),
        ("apache-httpd-template.conf", "httpd.conf"),
        ("apache-ports-template.conf", "ports.conf"),
        ("apache-MiG-template.conf", "MiG.conf"),
        ("apache-production-mode-template.conf", "production-mode.conf"),
        ("apache-mimic-deb-template.conf", "mimic-deb.conf"),
        ("apache-init.d-deb-template", "apache.initd"),
        ("apache-service-template.conf", "apache2.service"),
        ("apache-MiG-jupyter-def-template.conf", "MiG-jupyter-def.conf"),
        ("apache-MiG-jupyter-openid-template.conf", "MiG-jupyter-openid.conf"),
        ("apache-MiG-jupyter-oidc-template.conf", "MiG-jupyter-oidc.conf"),
        ("apache-MiG-jupyter-proxy-template.conf", "MiG-jupyter-proxy.conf"),
        ("apache-MiG-jupyter-rewrite-template.conf",
         "MiG-jupyter-rewrite.conf"),
        ("trac-MiG-template.ini", "trac.ini"),
        ("logrotate-MiG-template", "logrotate-migrid"),
        ("MiGserver-template.conf", "MiGserver.conf"),
        ("static-skin-template.css", "static-skin.css"),
        ("index-template.html", "index.html"),
        ("openssh-MiG-sftp-subsys-template.conf",
         "sshd_config-MiG-sftp-subsys"),
        ("libnss_mig-template.conf", "libnss_mig.conf"),
        ("nsswitch-template.conf", "nsswitch.conf"),
        ("pam-sshd-template", "pam-sshd"),
        ("seafile-template.conf", "seafile.conf"),
        ("seafile-ccnet-template.conf", "ccnet.conf"),
        ("seafile-seahub_settings-template.py", "seahub_settings.py"),
        ("fail2ban-MiG-daemons-filter-template.conf",
         "MiG-daemons-filter.conf"),
        ("fail2ban-MiG-daemons-handshake-filter-template.conf",
         "MiG-daemons-handshake-filter.conf"),
        ("fail2ban-MiG-daemons-webscan-filter-template.conf",
         "MiG-daemons-webscan-filter.conf"),
        ("fail2ban-MiG-daemons-pw-crack-filter-template.conf",
         "MiG-daemons-pw-crack-filter.conf"),
        ("fail2ban-sshd-pw-crack-filter-template.conf",
         "sshd-pw-crack-filter.conf"),
        ("fail2ban-seafile-auth-filter-template.conf",
         "seafile-auth-filter.conf"),
        ("fail2ban-MiG-daemons-jail-template.conf", "MiG-daemons-jail.conf"),
        # service script for MiG daemons
        ("migrid-init.d-rh-template", "migrid-init.d-rh"),
        ("migrid-init.d-deb-template", "migrid-init.d-deb"),
        # cron helpers
        ("migerrors-template.sh.cronjob", "migerrors"),
        ("migsftpmon-template.sh.cronjob", "migsftpmon"),
        ("migimportdoi-template.sh.cronjob", "migimportdoi"),
        ("migindexdoi-template.sh.cronjob", "migindexdoi"),
        ("mignotifyexpire-template.sh.cronjob", "mignotifyexpire"),
        ("migstateclean-template.sh.cronjob", "migstateclean"),
        ("migcheckssl-template.sh.cronjob", "migcheckssl"),
        ("migacctexpire-template.sh.cronjob", "migacctexpire"),
        ("migverifyarchives-template.sh.cronjob", "migverifyarchives"),
        ("miglustrequota-template.sh.cronjob", "miglustrequota"),
    ]
    overrides_out_name = {
        'apache.initd': _override_apache_initd
    }

    # Greedy match trailing space for all the values to uncomment stuff
    strip_trailing_space = ['__IF_SEPARATE_PORTS__', '__APACHE_PRE2.4__',
                            '__APACHE_RECENT__']
    for key in user_dict:
        if key.endswith('_COMMENTED__'):
            strip_trailing_space.append(key)

    for (in_name, out_name) in replacement_list:
        in_path = os.path.join(options['template_dir'], in_name)

        if out_name in overrides_out_name:
            out_name = overrides_out_name[out_name](out_name, user_dict)

        out_path = os.path.join(options['destination_dir'], out_name)

        if os.path.exists(in_path):
            # print "DEBUG: fill template: %s" % in_path
            fill_template(in_path, out_path, user_dict, strip_trailing_space)
            # Sync permissions
            os.chmod(out_path, os.stat(in_path).st_mode)
        else:
            print("Skipping missing template: %s" % in_path)

    # Remove lines from templates
    for (temp_file, remove_pattern) in cleanup_list:
        template_remove(temp_file, remove_pattern)


def _generate_confs_instructions(options, user_dict):
    """Write additional instructions for further use of generated confs"""
    instructions_dict = {
        'destination': options['destination_link'],
        'destination_dir': options['destination_dir'],
        'apache_etc': user_dict['__APACHE_ETC__'],
        'mig_code': user_dict['__MIG_CODE__'],
        'mig_state': user_dict['__MIG_STATE__'],
        'user': user_dict['__MIG_USER__'],
        'group': user_dict['__MIG_GROUP__'],
    }

    instructions = '''Configurations for MiG and Apache were generated in
%(destination_dir)s/ and symlinked to %(destination)s .
For a default setup you will probably want to copy the MiG daemon conf to the
server code directory:
cp %(destination_dir)s/MiGserver.conf %(mig_code)s/server/
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
sudo cp %(destination)s/apache2.service /lib/systemd/system/httpd.service

You may also want to consider copying the generated apache2.conf, httpd.conf,
production-mode.conf, ports.conf and envvars to %(apache_etc)s/:
sudo cp %(destination)s/apache2.conf %(apache_etc)s/
sudo cp %(destination)s/httpd.conf %(apache_etc)s/
sudo cp %(destination)s/production-mode.conf %(apache_etc)s/
sudo cp %(destination)s/ports.conf %(apache_etc)s/
sudo cp %(destination)s/envvars %(apache_etc)s/

If jupyter is enabled, the following configuration directory must be created
 and subsequent configuration files copied as follows,
sudo mkdir -p %(apache_etc)s/conf.extras.d
sudo cp %(destination)s/MiG-jupyter-def.conf %(apache_etc)s/conf.extras.d
sudo cp %(destination)s/MiG-jupyter-openid.conf %(apache_etc)s/conf.extras.d
sudo cp %(destination)s/MiG-jupyter-oidc.conf %(apache_etc)s/conf.extras.d
sudo cp %(destination)s/MiG-jupyter-proxy.conf %(apache_etc)s/conf.extras.d
sudo cp %(destination)s/MiG-jupyter-rewrite.conf %(apache_etc)s/conf.extras.d

and if Trac is enabled, the generated trac.ini to %(mig_code)s/server/:
cp %(destination)s/trac.ini %(mig_code)s/server/

On a Debian/Ubuntu MiG developer server the dedicated apache init script is
added with:
sudo cp %(destination)s/apache-%(user)s /etc/init.d/apache-%(user)s

Please reload or restart your apache daemons afterwards to catch the
configuration changes.

If you enabled the MiG sftp subsystem for OpenSSH, you should setup PAM+NSS
as described in the mig/pam-mig and mig/libnss-mig READMEs and copy the
generated sshd_config-MiG-sftp-subsys to /etc/ssh/ for a parallel service:
sudo cp %(destination)s/sshd_config-MiG-sftp-subsys /etc/ssh/
sudo chown 0:0 /etc/ssh/sshd_config-MiG-sftp-subsys
sudo cp %(destination)s/libnss_mig.conf /etc/
then carefully sync or copy contents of PAM sshd service setup and NSS switch
to only allow password logins for the MiG sftp-subsys service
sudo cp %(destination)s/pam-sshd /etc/pam.d/sshd
sudo cp %(destination)s/nsswitch.conf /etc/
You may also need to reduce the system sshd to listen on a particular address
rather than claiming all available addresses and thus occupying the one for
the MiG sftp-susbsys instance.
We also recommend the moduli tuning to at least 2000 as mentioned on:
https://stribika.github.io/2015/01/04/secure-secure-shell.html
After making sure it fits your site you can start the openssh service with:
sudo /usr/sbin/sshd -f /etc/ssh/sshd_config-MiG-sftp-subsys

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

If running a local Seafile instance you may also want to copy confs to the
Seafile installation
cp %(destination)s/seafile.conf ~/seafile/conf/
cp %(destination)s/ccnet.conf ~/seafile/conf/
cp %(destination)s/seahub_settings.py ~/seafile/conf/

The MiG-daemons-filter.conf and sshd-pw-crack-filter.conf contain Fail2Ban
filters and MiG-daemons-jail.conf contains a matching Fail2Ban jail
configuration to automatically lock out clients after a number of consecutive
password errors to prevent brute-force scans for all MiG network daemons.
You can install them with:
sudo cp %(destination)s/MiG-daemons-filter.conf \\
        /etc/fail2ban/filter.d/MiG-daemons.conf
sudo cp %(destination)s/MiG-daemons-handshake-filter.conf \\
        /etc/fail2ban/filter.d/MiG-daemons-handshake.conf
sudo cp %(destination)s/MiG-daemons-webscan-filter.conf \\
        /etc/fail2ban/filter.d/MiG-daemons-webscan.conf
sudo cp %(destination)s/MiG-daemons-pw-crack-filter.conf \\
        /etc/fail2ban/filter.d/MiG-daemons-pw-crack.conf
sudo cp %(destination)s/sshd-pw-crack-filter.conf \\
        /etc/fail2ban/filter.d/sshd-pw-crack.conf
sudo cp %(destination)s/seafile-auth-filter.conf \\
        /etc/fail2ban/filter.d/seafile-auth.conf
sudo cp %(destination)s/MiG-daemons-jail.conf \\
        /etc/fail2ban/jails.local
After making sure they fit your site you can start the fail2ban service with:
sudo service fail2ban restart

The migstateclean, migerrors, migsftpmon, migimportdoi and mignotifyexpire
files are cron scripts to automatically clean up state files, grep for
important errors in all MiG log files, warn about possible sftp crypto issues,
download DOI metadata from upstream provider and inform local certificate and
openid users about upcoming account expiry.
You can install them with:
chmod 755 %(destination)s/mig{stateclean,errors,sftpmon,importdoi,notifyexpire}
sudo cp %(destination)s/mig{stateclean,errors,sftpmon,importdoi,notifyexpire} \\
        /etc/cron.daily/

The migcheckssl, migverifyarchives, migacctexpire and miglustrequota files
are cron scripts to automatically check for LetsEncrypt certificate renewal,
run pending archive verification before sending a copy to tape,
generate account expire stats and create/update lustre quota.
You can install them with:
chmod 700 %(destination)s/migcheckssl
sudo cp %(destination)s/migcheckssl /etc/cron.daily/
chmod 700 %(destination)s/migverifyarchives
sudo cp %(destination)s/migverifyarchives /etc/cron.hourly/
chmod 700 %(destination)s/migacctexpire
sudo cp %(destination)s/migacctexpire /etc/cron.monthly/
chmod 700 %(destination)s/miglustrequota
sudo cp %(destination)s/miglustrequota /etc/cron.hourly/

''' % instructions_dict
    instructions_path = os.path.join(
        options['destination_dir'], "instructions.txt")
    success = write_file(instructions, instructions_path, None)
    if not success:
        print("could not write instructions ot %s" % (instructions_path,))
    return success
