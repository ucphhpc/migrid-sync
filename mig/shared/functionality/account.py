#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# account - account page with info and account management options
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#


"""Account page with user details and account management options"""

from __future__ import absolute_import

import datetime
import os
import copy
import time

from mig.lib.accounting import get_usage
from mig.shared import returnvalues
from mig.shared.accountreq import renew_account_access_template
from mig.shared.accountstate import account_expire_info
from mig.shared.base import extract_field, requested_page
from mig.shared.defaults import csrf_field, user_home_label, AUTH_MIG_OID, \
    AUTH_MIG_OIDC, AUTH_MIG_CERT
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.htmlgen import html_user_messages, man_base_js
from mig.shared.httpsclient import detect_client_auth, find_auth_type_and_label
from mig.shared.init import find_entry, initialize_main_variables
from mig.shared.useradm import get_full_user_map, default_search, search_users, \
    verify_user_peers
from mig.shared.userdb import default_db_path

_account_field_order = [('full_name', 'Full Name'),
                        ('organization', 'Organization'),
                        ('email', 'Email Address'),
                        ('country', 'Country'),
                        ('role', 'Role'),
                        ('status', 'Account Status'),
                        ('expire', 'Expire'),
                        ('peers_full_name', 'Peer Full Name(s)'),
                        ('peers_email', 'Peer Email Address(es)'),
                        ]


def html_tmpl(configuration, client_id, environ, title_entry):
    """HTML page base: some account and manage actions depend on configuration
    and environ.
    """
    logger = configuration.logger
    user_msg, show_user_msg = '', 'hidden'
    if configuration.site_enable_user_messages:
        user_msg = html_user_messages(configuration, client_id)
        show_user_msg = ''
    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, {})
    user_account = ''
    if user_dict:
        # NOTE: set min days high enough to always return renew and extend_days
        (_, _, renew_days, extend_days) = account_expire_info(configuration,
                                                              client_id,
                                                              environ, 999999)
        user_account += '''
        <h3>Account Details</h3>
        <p class="sub-title">Your account has the following information
        registered:
        </p>
        '''
        show_account = {}
        for (field, label) in _account_field_order:
            field_hint = ''
            if not user_dict.get(field, False):
                continue
            show_account[field] = copy.deepcopy(user_dict[field])
            if field == 'expire':
                # NOTE: translate epoch to proper datetime string
                expire_dt = datetime.datetime.fromtimestamp(
                    show_account[field])
                # strip usec for user-friendly time stamp
                show_account[field] = expire_dt.replace(microsecond=0)
                if extend_days > 0:
                    field_hint = """(web login auto-extends access for %d days,
and sign up for %d days at a time)""" % (extend_days, renew_days)
                elif renew_days > 0:
                    field_hint = """(renewal may extend it for up to %d days
at a time depending on site policies)""" % renew_days
            user_account += '''%s: %s %s<br/>
            ''' % (label, show_account[field], field_hint)
    # NOTE: ID token is only available for openid connect
    claim_dump, user_token = '', ''
    for (key, val) in os.environ.items():
        if key.startswith('OIDC_CLAIM_'):
            claim_dump += "%s: %s<br/>" % (key, val)
    if claim_dump:
        user_token = '''
        <h3>ID Token</h3>
        <p class="sub-title">Your current login session provides the following
        additional information:
        </p>'''
        user_token += claim_dump
    fill_helpers = {'short_title': configuration.short_title,
                    'user_msg': user_msg,
                    'show_user_msg': show_user_msg,
                    'home_label': user_home_label,
                    'user_account': user_account,
                    'user_token': user_token}

    html = '''
    <!-- CONTENT -->
    <div class="container">
        <div id="account-container" class="row">
            ''' % fill_helpers
    html += '''
            <div id="user-account-container" class="col-12 invert-theme">
                <div id="user-account-content" class="user-account-placeholder">
                    %(user_account)s
                </div>
                <div id="user-token-content" class="user-token-placeholder">
                    %(user_token)s
                </div>
                <div id="user-data-content" class="user-data-placeholder">
                <p>Details are from your sign up and/or any updates provided
                through your login. Please contact support if something is
                incorrect or has significantly changed.
                </p>
                </div>
            </div>
            ''' % fill_helpers
    html += '''
            <div id="user-msg-container" class="col-12 invert-theme %(show_user_msg)s">
                <div id="user-msg-content" class="user-msg-placeholder">
                    %(user_msg)s
                </div>
            </div>
            ''' % fill_helpers
    html += '''
            <div class="col-lg-12 vertical-spacer"></div>
        </div>
    '''

    # Account management like renew account access for local users
    # TODO: add change password and delete account support for all accounts?
    (auth_type_name, auth_flavor) = detect_client_auth(configuration, environ)
    (auth_type, auth_label) = find_auth_type_and_label(configuration,
                                                       auth_type_name,
                                                       auth_flavor)
    show_local = [i for i in configuration.site_login_methods
                  if i.startswith('mig')]
    fill_helpers.update({'auth_type': auth_type,
                         'auth_type_name': auth_type_name,
                         'auth_flavor': auth_flavor,
                         'auth_label': auth_label})
    html += '''
        <div id="manage-container" class="row">
            <div class="manage-page__header col-12">
                <h2>Manage Account</h2>
                <p class="sub-title">Depending on your %(short_title)s account
                type you have access to one or more account management actions
                below.
                </p>
            </div>
            ''' % fill_helpers
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = 'accountaction'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'form_method':
                         form_method, 'csrf_field': csrf_field,
                         'csrf_token': csrf_token})
    if auth_type in show_local:
        fill_helpers['account_action'] = "RENEW_ACCESS"
        fill_helpers['peer_acceptance_notice'] = ""
        if configuration.site_peers_mandatory:
            peers_email = user_dict.get("peers_email", "")
            peers_list = user_dict.get("peers", [])
            search_filter = default_search()
            search_filter['email'] = peers_email
            configuration.logger.info("peers_email: %r" % peers_email)
            (_, hits) = search_users(search_filter,
                                     configuration,
                                     default_db_path(configuration),
                                     regex_match=['email'])
            possible_peers = [ent[0] for ent in hits]
            possible_peers.extend(peers_list)
            configuration.logger.info("possible_peers: %r" % possible_peers)
            valid_peers_list = []
            for verify_peer in possible_peers:
                configuration.logger.info("verify_peer: %r" % verify_peer)
                try:
                    (verified_peer_list, _) \
                        = verify_user_peers(configuration,
                                            default_db_path(configuration),
                                            client_id,
                                            user_dict,
                                            time.time(),
                                            verify_peer,
                                            0,
                                            False,
                                            False)
                except Exception as err:
                    logger.warning("Failed to verify user peers: %s" % err)
                    continue
                logger.info("verified_peer_list: %r"
                            % verified_peer_list)
                valid_peers_list.extend([peer for peer in verified_peer_list
                                         if peer not in valid_peers_list])
            show_peers = ''
            for peer in valid_peers_list:
                show_peers += "%s &lt;%s&gt;" \
                    % (extract_field(peer, 'full_name'),
                        extract_field(peer, 'email'))
            if show_peers:
                fill_helpers['peer_acceptance_notice'] = """
Apparently %s accepted you as a peer
and if that peer appointment has not yet ended you can renew your access here
without further operator or peer contact involvement. Otherwise you may need to
obtain or await explicit extension or peer assignment from someone else before
your access renewal can proceed.
                """ % show_peers
            else:
                bin_url = requested_page(os.environ).replace('-sid', '-bin')
                if fill_helpers.get('auth_flavor', '') == AUTH_MIG_OID:
                    fill_helpers['target_op'] \
                        = os.path.join(os.path.dirname(bin_url),
                                       'reqoid')
                elif fill_helpers.get('auth_flavor', '') == AUTH_MIG_OIDC:
                    fill_helpers['target_op'] \
                        = os.path.join(os.path.dirname(bin_url),
                                       'reqoidc')
                elif auth_flavor == AUTH_MIG_CERT:
                    fill_helpers['target_op'] \
                        = os.path.join(os.path.dirname(bin_url),
                                       'migcert')
                fill_helpers['peer_acceptance_notice'] = """
It looks like you may need someone with authority to appoint you as their peer
before your access renewal can be accepted.
                """
        fill_helpers['renew_helper'] = renew_account_access_template(
            configuration,
            valid_peers_list,
            environ,
            default_values=fill_helpers) % fill_helpers
        html += '''
            <div class="renew-account-access__header col-12">
                <h3>Renew Account Access</h3>
                %(renew_helper)s
            </div>
        ''' % fill_helpers

    html += '''
            <div class="col-lg-12 vertical-spacer"></div>
        </div>
    '''

    # Show storage accounting information if enabled

    if configuration.site_enable_accounting:
        account_usage = get_usage(configuration, client_id)
        if account_usage is None:
            logger.error("Failed to load acount usage for user: %r"
                         % client_id)
            account_usage = {}
        accounting = account_usage.get('accounting', {})
        accounting_dt = datetime.datetime.fromtimestamp(
            account_usage.get('timestamp', 0))
        quota = account_usage.get('quota', {})
        fill_helpers['usage_helper'] = "<p>Updated: %s</p>" % accounting_dt
        fill_helpers['usage_helper'] += "<p>Quota updated:<br/>"
        for backend, values in quota.items():
            quota_dt = datetime.datetime.fromtimestamp(values.get('mtime', 0))
            fill_helpers['usage_helper'] \
                += "%s&nbsp;&nbsp;&nbsp;&nbsp;%s<br/>" % (quota_dt, backend)
        fill_helpers['usage_helper'] += "</p><p>"
        accounting_report = accounting.get(client_id, {})
        if configuration.site_enable_gdp:
            # NOTE: Only show vgrid usage when in GDP mode
            #       as no data is stored in user home
            vgrid_report = accounting_report.get('vgrid_report', '')
            if vgrid_report:
                fill_helpers['usage_helper'] \
                    += vgrid_report.replace('\n', '<br/>')
        else:
            total_report = accounting_report.get('total_report', '')
            home_report = accounting_report.get('home_report', '')
            freeze_report = accounting_report.get('freeze_report', '')
            vgrid_report = accounting_report.get('vgrid_report', '')
            ext_users_report = accounting_report.get('ext_users_report', '')
            peers_report = accounting_report.get('peers_report', '')
            if total_report:
                fill_helpers['usage_helper'] \
                    += total_report.replace('\n', '<br/>') \
                    + "<br/>"
            if home_report:
                fill_helpers['usage_helper'] \
                    += home_report.replace('\n', '<br/>') \
                    + "<br/>"
            if freeze_report:
                fill_helpers['usage_helper'] \
                    += freeze_report.replace('\n', '<br/>') \
                    + "<br/>"
            if vgrid_report:
                fill_helpers['usage_helper'] \
                    += vgrid_report.replace('\n', '<br/>') \
                    + "<br/>"
            if ext_users_report:
                fill_helpers['usage_helper'] \
                    += ext_users_report.replace('\n', '<br/>') \
                    + "<br/>"
            if peers_report:
                fill_helpers['usage_helper'] \
                    += peers_report.replace('\n', '<br/>') \
                    + "<br/>"
        fill_helpers['usage_helper'] += "</p>"

        html += '''
        <div id="usage-container" class="row">
            <div class="usage-page__header col-12">
                <h2>Account Usage</h2>
       '''
        html += '''
                %(usage_helper)s
            </div>
            <div class="col-lg-12 vertical-spacer"></div>
            ''' % fill_helpers

    html += '''
        </div>
    </div>
    '''

    return html


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['text', defaults]


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    # Generate and insert the page HTML
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s Profile' % configuration.short_title

    # jquery support for AJAX saving

    (add_import, add_init, add_ready) = man_base_js(configuration, [])
    add_init += '''
    '''
    add_ready += '''
                init_user_msg();
    '''
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    html = html_tmpl(configuration, client_id, environ, title_entry)
    output_objects.append({'object_type': 'html_form', 'text': html})

    return (output_objects, returnvalues.OK)
