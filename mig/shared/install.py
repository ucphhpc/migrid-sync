#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# install - MiG server install helpers
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

"""Install helpers:

Generate the configurations for a custom MiG server installation.
Creates MiG server and Apache configurations to fit the provided settings.

Create MiG developer account with dedicated web server and daemons.
"""

from __future__ import print_function
from __future__ import absolute_import

import ast
import base64
import crypt
import datetime
import grp
import os
import pwd
import random
import re
import socket
import subprocess
import sys

from mig.shared.defaults import default_http_port, default_https_port, \
    mig_user, mig_group, default_source, default_destination, \
    auth_openid_mig_db, auth_openid_ext_db, STRONG_TLS_CIPHERS, \
    STRONG_TLS_CURVES, STRONG_SSH_KEXALGOS, STRONG_SSH_LEGACY_KEXALGOS, \
    STRONG_SSH_CIPHERS, STRONG_SSH_LEGACY_CIPHERS, STRONG_SSH_MACS, \
    STRONG_SSH_LEGACY_MACS, CRACK_USERNAME_REGEX, CRACK_WEB_REGEX, \
    keyword_any, keyword_auto
from mig.shared.compat import ensure_native_string
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


def generate_confs(
    # NOTE: make sure command line args with white-space are properly wrapped
    generateconfs_command=subprocess.list2cmdline(sys.argv),
    source=default_source,
    destination=default_destination,
    destination_suffix="",
    base_fqdn='',
    public_fqdn='',
    public_alias_fqdn='',
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
    user=mig_user,
    group=mig_group,
    timezone=keyword_auto,
    apache_version='2.4',
    apache_etc='/etc/apache2',
    apache_run='/var/run',
    apache_lock='/var/lock',
    apache_log='/var/log/apache2',
    apache_worker_procs=256,
    openssh_version='7.4',
    mig_code='/home/mig/mig',
    mig_state='/home/mig/state',
    mig_certs='/home/mig/certs',
    auto_add_cert_user=False,
    auto_add_oid_user=False,
    auto_add_oidc_user=False,
    auto_add_filter_fields='',
    auto_add_filter_method='skip',
    auto_add_user_permit='distinguished_name:.*',
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
    daemon_pubkey='',
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
    freeze_to_tape='',
    status_system_match=keyword_any,
    duplicati_protocols='',
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
    _getpwnam=pwd.getpwnam,
):
    """Generate Apache and MiG server confs with specified variables"""

    # Read out dictionary of args with defaults and overrides

    expanded = dict(locals())

    # expand any directory path specific as "auto" relative to CWD
    if source == keyword_auto:
        expanded['source'] = os.path.dirname(sys.argv[0])
        source = expanded['source']
    if destination == keyword_auto:
        expanded['destination'] = os.path.dirname(sys.argv[0])
        destination = expanded['destination']

    # expand any user information marked as "auto" based on the environment
    if user == keyword_auto:
        user = pwd.getpwuid(os.getuid())[0]
    if group == keyword_auto:
        group = grp.getgrgid(os.getgid())[0]

    # finalize a destination path up-front
    expanded['destination_path'] = "%s%s" % (destination, destination_suffix)
    destination_path = expanded['destination_path']

    # Backwards compatibility with old name
    if public_port and not public_http_port:
        public_http_port = public_port

    user_dict = {}
    user_dict['__GENERATECONFS_COMMAND__'] = generateconfs_command
    user_dict['__BASE_FQDN__'] = base_fqdn
    user_dict['__PUBLIC_FQDN__'] = public_fqdn
    user_dict['__PUBLIC_ALIAS_FQDN__'] = public_alias_fqdn
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
    user_dict['__JUPYTER_REWRITES__'] = ''
    user_dict['__JUPYTER_PROXIES__'] = ''
    user_dict['__JUPYTER_SECTIONS__'] = ''
    user_dict['__CLOUD_SERVICES__'] = cloud_services
    user_dict['__CLOUD_SECTIONS__'] = ''
    user_dict['__USER__'] = user
    user_dict['__GROUP__'] = group
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
    user_dict['__DAEMON_KEYCERT_SHA256__'] = ''
    user_dict['__DAEMON_PUBKEY_MD5__'] = ''
    user_dict['__DAEMON_PUBKEY_SHA256__'] = ''
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
    user_dict['__FREEZE_TO_TAPE__'] = freeze_to_tape
    user_dict['__STATUS_SYSTEM_MATCH__'] = status_system_match
    user_dict['__IMNOTIFY_ADDRESS__'] = imnotify_address
    user_dict['__IMNOTIFY_CHANNEL__'] = imnotify_channel
    user_dict['__IMNOTIFY_USERNAME__'] = imnotify_username
    user_dict['__IMNOTIFY_PASSWORD__'] = imnotify_password
    user_dict['__GDP_DATA_CATEGORIES__'] = gdp_data_categories
    user_dict['__GDP_ID_SCRAMBLE__'] = gdp_id_scramble
    user_dict['__GDP_PATH_SCRAMBLE__'] = gdp_path_scramble
    user_dict['__PUBLIC_HTTPS_LISTEN__'] = listen_clause
    user_dict['__PUBLIC_ALIAS_HTTPS_LISTEN__'] = listen_clause
    user_dict['__QUOTA_BACKEND__'] = quota_backend
    user_dict['__QUOTA_USER_LIMIT__'] = "%s" % quota_user_limit
    user_dict['__QUOTA_VGRID_LIMIT__'] = "%s" % quota_vgrid_limit

    # Needed for PAM/NSS
    pw_info = _getpwnam(user)
    user_dict['__MIG_UID__'] = "%s" % (pw_info.pw_uid)
    user_dict['__MIG_GID__'] = "%s" % (pw_info.pw_gid)

    fail2ban_daemon_ports = []
    # Apache fails on duplicate Listen directives so comment in that case
    port_list = [mig_cert_port, ext_cert_port, mig_oid_port, ext_oid_port,
                 mig_oidc_port, ext_oidc_port, sid_port]
    fqdn_list = [mig_cert_fqdn, ext_cert_fqdn, mig_oid_fqdn, ext_oid_fqdn,
                 mig_oidc_fqdn, ext_oidc_fqdn, sid_fqdn]
    listen_list = zip(fqdn_list, port_list)
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
    if user_dict['__OPENSSH_VERSION__'] >= "7.3":
        # Use current strong Kex/Cipher/MAC settings for openssh >=7.3
        user_dict['__OPENSSH_KEXALGOS__'] = STRONG_SSH_KEXALGOS
        user_dict['__OPENSSH_CIPHERS__'] = STRONG_SSH_CIPHERS
        user_dict['__OPENSSH_MACS__'] = STRONG_SSH_MACS
    else:
        # Fall back to legacy Kex/Cipher/MAC for openssh <7.3
        user_dict['__OPENSSH_KEXALGOS__'] = STRONG_SSH_LEGACY_KEXALGOS
        user_dict['__OPENSSH_CIPHERS__'] = STRONG_SSH_LEGACY_CIPHERS
        user_dict['__OPENSSH_MACS__'] = STRONG_SSH_LEGACY_MACS

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

    if duplicati_protocols:
        prio_duplicati_protocols = duplicati_protocols.split()
    else:
        # NOTE: prioritized order based on performance and robustness
        prio_duplicati_protocols = []
        if enable_sftp_subsys or enable_sftp:
            prio_duplicati_protocols.append('sftp')
        if enable_ftps:
            prio_duplicati_protocols.append('ftps')
        if enable_davs:
            prio_duplicati_protocols.append('davs')
    user_dict['__DUPLICATI_PROTOCOLS__'] = ' '.join(prio_duplicati_protocols)

    if timezone == keyword_auto:
        # attempt to detect the timezone
        sys_timezone = None
        try:
            timezone_cmd = ["/usr/bin/timedatectl", "status"]
            timezone_proc = subprocess_popen(
                timezone_cmd, stdout=subprocess_pipe)
            for line in timezone_proc.stdout.readlines():
                line = ensure_native_string(line.strip())
                if not line.startswith("Time zone: "):
                    continue
                sys_timezone = line.replace("Time zone: ", "").split(" ", 1)[0]
        except OSError as exc:
            # warn about any issues executing the command but continue
            pass
        if sys_timezone is None:
            print("WARNING: failed to extract system time zone; defaulting to UTC")
            sys_timezone = 'UTC'

        timezone = sys_timezone

    user_dict['__SEAFILE_TIMEZONE__'] = timezone

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
        jupyter_sections, jupyter_proxies, jupyter_defs, \
            jupyter_openids, jupyter_rewrites = [], [], [], [], []
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

            # Setup apache openid template
            openid_template = gen_openid_template(url, def_name)
            jupyter_openids.append(openid_template)

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

    # Auto-fill fingerprints if daemon key is set
    if user_dict['__DAEMON_KEYCERT__']:
        if not os.path.isfile(os.path.expanduser("%(__DAEMON_KEYCERT__)s" %
                                                 user_dict)):
            print("ERROR: requested daemon keycert file not found!")
            print("""You can create it with:
openssl genrsa -out %(__DAEMON_KEYCERT__)s 2048""" % user_dict)
            sys.exit(1)

        key_path = os.path.expanduser(user_dict['__DAEMON_KEYCERT__'])
        openssl_cmd = ["openssl", "x509", "-noout", "-fingerprint", "-sha256",
                       "-in", key_path]
        try:
            openssl_proc = subprocess_popen(
                openssl_cmd, stdout=subprocess_pipe)
            raw_sha256 = openssl_proc.stdout.read().strip()
            daemon_keycert_sha256 = raw_sha256.replace("SHA256 Fingerprint=",
                                                       "")
        except Exception as exc:
            print("ERROR: failed to extract sha256 fingerprint of %s: %s" %
                  (key_path, exc))
            daemon_keycert_sha256 = ''
        user_dict['__DAEMON_KEYCERT_SHA256__'] = daemon_keycert_sha256
    if user_dict['__DAEMON_PUBKEY__']:
        if not os.path.isfile(os.path.expanduser("%(__DAEMON_PUBKEY__)s" %
                                                 user_dict)):
            print("ERROR: requested daemon pubkey file not found!")
            print("""You can create it with:
ssh-keygen -f %(__DAEMON_KEYCERT__)s -y > %(__DAEMON_PUBKEY__)s""" % user_dict)
            sys.exit(1)

        pubkey_path = os.path.expanduser(user_dict['__DAEMON_PUBKEY__'])
        pubkey = read_file(pubkey_path, None)
        if pubkey is None:
            print("Failed to read provided daemon key: %s" % pubkey_path)
        # The desired values are hashes of the base64 encoded actual key
        try:
            b64_key = base64.b64decode(
                pubkey.strip().split()[1].encode('ascii'))
            raw_md5 = make_simple_hash(b64_key)
            # reformat into colon-spearated octets
            daemon_pubkey_md5 = ':'.join(a + b for a, b in zip(raw_md5[::2],
                                                               raw_md5[1::2]))
            raw_sha256 = make_safe_hash(b64_key, False)
            daemon_pubkey_sha256 = base64.b64encode(raw_sha256).rstrip('=')
        except Exception as exc:
            print("ERROR: failed to extract fingerprints of %s : %s" %
                  (pubkey_path, exc))
            daemon_pubkey_sha256 = ''
        user_dict['__DAEMON_PUBKEY_MD5__'] = daemon_pubkey_md5
        user_dict['__DAEMON_PUBKEY_SHA256__'] = daemon_pubkey_sha256

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

    if not os.path.islink(destination) and os.path.isdir(destination):
        print("ERROR: Legacy %s dir in the way - please remove first" %
              destination)
        sys.exit(1)
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
        digest_salt = ensure_native_string(base64.b16encode(os.urandom(16)))
    user_dict['__DIGEST_SALT__'] = digest_salt

    if crypto_salt == keyword_auto:
        # Generate random hex salt for various crypto helpers
        crypto_salt = ensure_native_string(base64.b16encode(os.urandom(16)))
    user_dict['__CRYPTO_SALT__'] = crypto_salt

    # Greedy match trailing space for all the values to uncomment stuff
    strip_trailing_space = ['__IF_SEPARATE_PORTS__', '__APACHE_PRE2.4__',
                            '__APACHE_RECENT__']
    for key in user_dict:
        if key.endswith('_COMMENTED__'):
            strip_trailing_space.append(key)

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
        ("apache-init.d-deb-template", "apache-%s" % user),
        ("apache-service-template.conf", "apache2.service"),
        ("apache-MiG-jupyter-def-template.conf", "MiG-jupyter-def.conf"),
        ("apache-MiG-jupyter-openid-template.conf", "MiG-jupyter-openid.conf"),
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
    ]
    for (in_name, out_name) in replacement_list:
        in_path = os.path.join(source, in_name)
        out_path = os.path.join(destination_path, out_name)
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

    instructions = '''Configurations for MiG and Apache were generated in
%(destination)s%(destination_suffix)s/ and symlinked to %(destination)s .
For a default setup you will probably want to copy the MiG daemon conf to the
server code directory:
cp %(destination)s%(destination_suffix)s/MiGserver.conf %(mig_code)s/server/
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

The migcheckssl, migverifyarchives and migacctexpire files are cron scripts to
automatically check for LetsEncrypt certificate renewal, run pending archive
verification before sending a copy to tape and to generate account expire stats.
You can install them with:
chmod 700 %(destination)s/migcheckssl
sudo cp %(destination)s/migcheckssl /etc/cron.daily/
chmod 700 %(destination)s/migverifyarchives
sudo cp %(destination)s/migverifyarchives /etc/cron.hourly/
chmod 700 %(destination)s/migacctexpire
sudo cp %(destination)s/migacctexpire /etc/cron.monthly/

''' % expanded
    instructions_path = "%s/instructions.txt" % destination_path
    if not write_file(instructions, instructions_path, None):
        print("could not write instructions ot %s" % instructions_path)
    return expanded


def create_user(
    user,
    group,
    ssh_login_group='remotelogin',
    debug=False,
    base_fqdn=socket.getfqdn(),
    public_fqdn=socket.getfqdn(),
    mig_cert_fqdn=socket.getfqdn(),
    ext_cert_fqdn=socket.getfqdn(),
    mig_oid_fqdn=socket.getfqdn(),
    ext_oid_fqdn=socket.getfqdn(),
    mig_oidc_fqdn=socket.getfqdn(),
    ext_oidc_fqdn=socket.getfqdn(),
    sid_fqdn=socket.getfqdn(),
    io_fqdn=socket.getfqdn(),
):
    """Create MiG unix user with supplied user and group name and show
    commands to make it a MiG developer account.
    If X_fqdn values are all set to a fqdn different from the default fqdn of
    this host the apache web server configuration will use the same port for
    the individual https interfaces but on different IP adresses. Otherwise it
    will use N different ports on the same address.
    """

    # make sure not to wreak havoc if no user supplied

    if not user:
        print("no user supplied! can't continue")
        return False

    groupadd_cmd = ['groupadd', group]
    print(groupadd_cmd)
    # NOTE: we use command list here to avoid shell requirement
    status = subprocess_call(groupadd_cmd)
    if status != 0:
        print('Warning: groupadd exit code %d' % status)

    # Don't use 'o'/'0' and 'l'/'1' since they may confuse users

    valid_chars = 'abcdefghijkmnpqrstuvwxyz'\
        + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ23456789'
    pwlen = 8
    pw = ''
    for _ in range(pwlen):
        pw += random.choice(valid_chars)

    # TODO: python does not support md5 passwords - using DES ones
    # from crypt for now

    shell = '/bin/bash'
    enc_pw = crypt.crypt(pw, random.choice(valid_chars)
                         + random.choice(valid_chars))
    useradd_cmd = ['useradd', '-m', '-s %s' % shell, '-p %s' % enc_pw,
                   '-g %s' % group, user]
    print(useradd_cmd)
    # NOTE: we use command list here to avoid shell requirement
    status = subprocess_call(useradd_cmd)
    if status != 0:
        print('Warning: useradd exit code %d' % status)
    else:
        print('# Created %s in group %s with pw %s' % (user, group, pw))

    home = '/home/%s' % user

    chmod_cmd = ['chmod', '-R', 'g-rwx,o-rwx', home]
    print(chmod_cmd)
    # NOTE: we use command list here to avoid shell requirement
    status = subprocess_call(chmod_cmd)
    if status != 0:
        print('Warning: chmod exit code %d' % status)
    else:
        print('Removed global access to %s' % home)

    addgroup_cmd = ['addgroup', user, ssh_login_group]
    print(addgroup_cmd)
    # NOTE: we use command list here to avoid shell requirement
    status = subprocess_call(addgroup_cmd)
    if status != 0:
        print('Warning: login addgroup exit code %d' % status)
    else:
        print('# Added %s to login group %s' % (user, ssh_login_group))

    # NOTE: we use command list here to avoid shell requirement
    idu_proc = subprocess_popen(['id', '-u %s' % user], stdout=subprocess_pipe)
    idu_proc.wait()
    out = idu_proc.stdout.readlines()
    uid_str = out[0].strip()
    # NOTE: we use command list here to avoid shell requirement
    idg_proc = subprocess_popen(['id', '-g %s' % user], stdout=subprocess_pipe)
    idg_proc.wait()
    out = idg_proc.stdout.readlines()
    gid_str = out[0].strip()
    try:
        uid = int(uid_str)
        gid = int(gid_str)
    except Exception as err:
        print('Error: %s' % err)
        if not debug:
            return False

    # print "uid: %d, gid: %d" % (uid, gid)

    svc_ports = 6
    reserved_ports = range(svc_ports * uid, svc_ports * uid + svc_ports)
    public_http_port, mig_cert_port, ext_cert_port, mig_oid_port, ext_oid_port, sid_port = reserved_ports[
        :svc_ports]
    # Only one port for openid or openid connect
    mig_oidc_port = mig_oid_port
    ext_oidc_port = ext_oid_port

    mig_dir = os.path.join(home, 'mig')
    server_dir = os.path.join(mig_dir, 'server')
    state_dir = os.path.join(home, 'state')
    apache_version = '2.4'
    apache_etc = '/etc/apache2'
    apache_dir = '%s-%s' % (apache_etc, user)
    apache_run = '%s/run' % apache_dir
    apache_lock = '%s/lock' % apache_dir
    apache_log = '%s/log' % apache_dir
    apache_worker_procs = 256
    openssh_version = '7.4'
    cert_dir = '%s/MiG-certificates' % apache_dir
    auto_add_cert_user = False
    auto_add_oid_user = False
    auto_add_oidc_user = False
    auto_add_filter_fields = ''
    auto_add_filter_method = 'skip'
    auto_add_user_permit = 'distinguished_name:.*'
    cert_valid_days = 365
    oid_valid_days = 365
    oidc_valid_days = 365
    generic_valid_days = 365
    enable_migadmin = False
    # We don't necessarily have free ports for daemons
    enable_sftp = False
    enable_sftp_subsys = False
    sftp_subsys_auth_procs = 10
    enable_davs = False
    enable_ftps = False
    enable_twofactor = False
    twofactor_mandatory_protos = ''
    enable_twofactor_strict_address = False
    twofactor_auth_apps = ''
    enable_peers = False
    peers_mandatory = False
    peers_explicit_fields = ''
    peers_contact_hint = ''
    enable_cracklib = False
    enable_openid = False
    enable_gravatars = True
    enable_sitestatus = True
    enable_quota = False
    enable_wsgi = True
    wsgi_procs = 5
    enable_jobs = True
    enable_resources = True
    enable_workflows = False
    enable_events = True
    enable_sharelinks = True
    enable_transfers = True
    enable_freeze = False
    enable_sandboxes = False
    enable_vmachines = False
    enable_preview = False
    enable_jupyter = False
    enable_cloud = False
    enable_hsts = False
    enable_vhost_certs = False
    enable_verify_certs = False
    enable_seafile = False
    enable_duplicati = False
    enable_crontab = False
    enable_notify = False
    enable_imnotify = False
    enable_dev_accounts = False
    user_interface = "V3 V2"
    mig_oid_title = 'MiG'
    mig_oid_provider = ''
    ext_oid_title = 'External'
    ext_oid_provider = ''
    mig_oidc_provider_meta_url = ''
    ext_oidc_provider_meta_url = ''
    ext_oidc_client_name = ''
    ext_oidc_client_id = ''
    ext_oidc_scope = ''
    ext_oidc_remote_user_claim = ''
    ext_oidc_pass_claim_as = ''
    dhparams_path = ''
    daemon_keycert = ''
    daemon_pubkey = ''
    daemon_pubkey_from_dns = False
    daemon_show_address = ''
    alias_field = 'email'
    hg_path = '/usr/bin/hg'
    hgweb_scripts = '/usr/share/doc/mercurial-common/examples/'
    trac_admin_path = '/usr/bin/trac-admin'
    trac_ini_path = '%s/trac.ini' % server_dir

    firewall_script = '/root/scripts/firewall'
    print('# Add the next line to %s and run the script:'
          % firewall_script)
    print('iptables -A INPUT -p tcp --dport %d:%d -j ACCEPT # webserver: %s'
          % (reserved_ports[0], reserved_ports[-1], user))

    sshd_conf = '/etc/ssh/sshd_config'
    print("""# Unless 'AllowGroups %s' is already included, append %s
# to the AllowUsers line in %s and restart sshd."""
          % (ssh_login_group, user, sshd_conf))
    print("""# Add %s to the sudoers file (visudo) with privileges
# to run apache init script in %s
visudo""" % (user, apache_dir))
    print("""# Set disk quotas for %s using reference user quota:
edquota -u %s -p LOGIN_OF_SIMILAR_USER"""
          % (user, user))
    expire = datetime.date.today()
    expire = expire.replace(year=expire.year + 1)
    print("""# Optionally set account expire date for user:
chage -E %s %s"""
          % (expire, user))
    print("""# Attach full name of user to login:
usermod -c 'INSERT FULL NAME HERE' %s"""
          % user)
    print("""# Add mount point for sandbox generator:
echo '/home/%s/state/sss_home/MiG-SSS/hda.img      /home/%s/state/sss_home/mnt  auto    user,loop       0       0' >> /etc/fstab"""
          % (user, user))

    src = os.path.abspath(os.path.dirname(sys.argv[0]))
    dst = os.path.join(src, '%s-confs' % user)
    dst_suffix = ""

    server_alias = '#ServerAlias'
    https_fqdns = [mig_cert_fqdn, ext_cert_fqdn, mig_oid_fqdn, ext_oid_fqdn,
                   mig_oidc_fqdn, ext_oidc_fqdn, sid_fqdn]
    https_resolved = [socket.gethostbyname(fqdn) for fqdn in https_fqdns]
    uniq_resolved = []
    for fqdn in https_resolved:
        if fqdn not in uniq_resolved:
            uniq_resolved.append(fqdn)
    if len(uniq_resolved) == len(https_fqdns):
        mig_cert_port = ext_cert_port = mig_oid_port = ext_oid_port = mig_oidc_port = ext_oidc_port = sid_port
        server_alias = 'ServerAlias'
    generate_confs(
        ' '.join(sys.argv),
        src,
        dst,
        dst_suffix,
        base_fqdn,
        public_fqdn,
        '',
        mig_cert_fqdn,
        ext_cert_fqdn,
        mig_oid_fqdn,
        ext_oid_fqdn,
        mig_oidc_fqdn,
        ext_oidc_fqdn,
        sid_fqdn,
        io_fqdn,
        user,
        group,
        apache_version,
        apache_dir,
        apache_run,
        apache_lock,
        apache_log,
        apache_worker_procs,
        openssh_version,
        mig_dir,
        state_dir,
        cert_dir,
        auto_add_cert_user,
        auto_add_oid_user,
        auto_add_oidc_user,
        auto_add_filter_fields,
        auto_add_filter_method,
        auto_add_user_permit,
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
        user_interface,
        mig_oid_title,
        mig_oid_provider,
        ext_oid_title,
        ext_oid_provider,
        mig_oidc_provider_meta_url,
        ext_oidc_provider_meta_url,
        ext_oidc_client_name,
        ext_oidc_client_id,
        ext_oidc_scope,
        ext_oidc_remote_user_claim,
        ext_oidc_pass_claim_as,
        dhparams_path,
        daemon_keycert,
        daemon_pubkey,
        daemon_pubkey_from_dns,
        daemon_show_address,
        alias_field,
        hg_path,
        hgweb_scripts,
        trac_admin_path,
        trac_ini_path,
        public_http_port,
        '',
        '',
        mig_cert_port,
        ext_cert_port,
        mig_oid_port,
        ext_oid_port,
        mig_oidc_port,
        ext_oidc_port,
        sid_port,
        'User',
        'Group',
        '#Listen',
        server_alias,
    )
    apache_envs_conf = os.path.join(dst, 'envvars')
    apache_apache2_conf = os.path.join(dst, 'apache2.conf')
    apache_httpd_conf = os.path.join(dst, 'httpd.conf')
    apache_ports_conf = os.path.join(dst, 'ports.conf')
    apache_mig_conf = os.path.join(dst, 'MiG.conf')
    apache_jupyter_def = os.path.join(dst, 'MiG-jupyter-def.conf')
    apache_jupyter_openid = os.path.join(dst, 'MiG-jupyter-openid.conf')
    apache_jupyter_proxy = os.path.join(dst, 'MiG-jupyter-proxy.conf')
    apache_jupyter_rewrite = os.path.join(dst, 'MiG-jupyter-rewrite.conf')
    server_conf = os.path.join(dst, 'MiGserver.conf')
    trac_ini = os.path.join(dst, 'trac.ini')
    apache_initd_script = os.path.join(dst, 'apache-%s' % user)

    settings = {'user': user, 'group': group, 'server_conf': server_conf,
                'trac_ini': trac_ini, 'home': home, 'server_dir': server_dir,
                'base_fqdn': base_fqdn, 'public_fqdn': public_fqdn}
    settings['sudo_cmd'] = 'sudo su - %(user)s -c' % settings

    print('# Clone %s to %s and put config files there:' % (apache_etc,
                                                            apache_dir))
    print('sudo cp -r -u -d -x %s %s' % (apache_etc, apache_dir))
    print('sudo rm -f %s/envvars' % apache_dir)
    print('sudo rm -f %s/apache2.conf' % apache_dir)
    print('sudo rm -f %s/httpd.conf' % apache_dir)
    print('sudo rm -f %s/ports.conf' % apache_dir)
    print('sudo rm -f %s/sites-enabled/*' % apache_dir)
    print('sudo rm -f %s/conf.d/*' % apache_dir)
    print('sudo cp -f -d %s %s/' % (apache_envs_conf, apache_dir))
    print('sudo cp -f -d %s %s/' % (apache_apache2_conf, apache_dir))
    print('sudo cp -f -d %s %s/' % (apache_httpd_conf, apache_dir))
    print('sudo cp -f -d %s %s/' % (apache_ports_conf, apache_dir))
    print('sudo cp -f -d %s %s/conf.d/' % (apache_mig_conf, apache_dir))
    print('sudo mkdir -p %s/conf.extras.d' % (apache_dir))
    print('sudo cp -f -d %s %s/conf.extras.d/' % (
        apache_jupyter_def, apache_dir))
    print('sudo cp -f -d %s %s/conf.extras.d/' % (apache_jupyter_openid,
                                                  apache_dir))
    print('sudo cp -f -d %s %s/conf.extras.d/' % (apache_jupyter_proxy,
                                                  apache_dir))
    print('sudo cp -f -d %s %s/conf.extras.d/' % (apache_jupyter_rewrite,
                                                  apache_dir))
    print('sudo cp -f -d %s %s/' % (apache_initd_script, apache_dir))
    print('sudo mkdir -p %s %s %s ' % (apache_run, apache_lock, apache_log))

    # allow read access to logs

    print('sudo chgrp -R %s %s' % (user, apache_log))
    print('sudo chmod 2755 %s' % apache_log)

    print("""# Setup MiG for %(user)s:
%(sudo_cmd)s 'ssh-keygen -t rsa -N \"\" -q -f \\
    %(home)s/.ssh/id_rsa'
%(sudo_cmd)s 'cp -f -x \\
    %(home)s/.ssh/{id_rsa.pub,authorized_keys}'
%(sudo_cmd)s 'ssh -o StrictHostKeyChecking=no \\
    %(user)s@%(base_fqdn)s pwd >/dev/null'
%(sudo_cmd)s 'svn checkout https://svn.code.sf.net/p/migrid/code/trunk/ %(home)s'
sudo chown %(user)s:%(group)s %(server_conf)s %(trac_ini)s
sudo cp -f -p %(server_conf)s %(trac_ini)s %(server_dir)s/
""" % settings)

    # Only add non-directory paths manually and leave the rest to
    # checkconf.py below

    print("""%(sudo_cmd)s 'mkfifo %(server_dir)s/server.stdin'
%(sudo_cmd)s 'mkfifo %(server_dir)s/notify.stdin'
%(sudo_cmd)s '%(server_dir)s/checkconf.py'
""" % settings)

    used_ports = [public_http_port, mig_cert_port, ext_cert_port, mig_oid_port,
                  ext_oid_port, mig_oidc_port, ext_oidc_port, sid_port]
    extra_ports = [port for port in reserved_ports if not port in used_ports]
    print("""
#############################################################
Created %s in group %s with pw %s
Reserved ports:
HTTP:\t\t%d
HTTPS internal certificate users:\t\t%d
HTTPS external certificate users:\t\t%d
HTTPS Internal openid users:\t\t%d
HTTPS external openid users:\t\t%d
HTTPS internal openid connect users:\t\t%d
HTTPS external openid connect users:\t\t%d
HTTPS resources:\t\t%d
Extra ports:\t\t%s

The dedicated apache server can be started with the command:
sudo %s/%s start

#############################################################
"""
          % (
              user,
              group,
              pw,
              public_http_port,
              mig_cert_port,
              ext_cert_port,
              mig_oid_port,
              ext_oid_port,
              mig_oidc_port,
              ext_oidc_port,
              sid_port,
              ', '.join(["%d" % port for port in extra_ports]),
              apache_dir,
              os.path.basename(apache_initd_script),
          ))
    return True
