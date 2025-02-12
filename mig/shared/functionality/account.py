#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# account - account page with info and account management options
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


"""Account page with user details and account management options"""

from __future__ import absolute_import

import datetime
import os

from mig.shared import returnvalues
from mig.shared.accountreq import account_pw_reset_template
from mig.shared.base import requested_page
from mig.shared.defaults import csrf_field, user_home_label, cert_field_order, \
    AUTH_MIG_OID, AUTH_MIG_OIDC, AUTH_MIG_CERT, AUTH_EXT_CERT
from mig.shared.functional import validate_input_and_cert
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.htmlgen import html_user_messages, man_base_html, man_base_js
from mig.shared.httpsclient import detect_client_auth
from mig.shared.output import html_link
from mig.shared.useradm import get_full_user_map

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

    user_msg, show_user_msg = '', 'hidden'
    if configuration.site_enable_user_messages:
        user_msg = html_user_messages(configuration, client_id)
        show_user_msg = ''
    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    user_account = ''
    if user_dict:
        user_account += '''
        <h3>Account Details</h3>
        <p class="sub-title">Your account has the following information
        registered:
        </p>
        '''
        for (field, label) in _account_field_order:
            if not user_dict.get(field, False):
                continue
            if field == 'expire':
                # NOTE: translate epoch to proper datetime string
                expire_dt = datetime.datetime.fromtimestamp(user_dict[field])
                user_dict[field] = expire_dt
            user_account += '''%s: %s<br/>
            ''' % (label, user_dict[field])
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
                    'user_msg': user_msg, 'show_user_msg': show_user_msg,
                    'home_label': user_home_label, 'user_account': user_account,
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

    # Account management like renew user and change password for local users
    # TODO: add delete account support for all accounts?
    (auth_type, auth_flavor) = detect_client_auth(configuration, environ)
    show_local = [i for i in configuration.site_login_methods
                  if i.startswith('mig')]
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
    if show_local and (user_dict.get('password', False) or
                       user_dict.get('password_hash', False)):
        bin_url = requested_page(os.environ).replace('-sid', '-bin')
        if auth_flavor == AUTH_MIG_OID:
            migoid_url = os.path.join(os.path.dirname(bin_url), 'reqoid.py')
            migoid_link = {'object_type': 'link', 'destination': migoid_url,
                           'text': 'Change %s %s password' %
                           (configuration.user_mig_oid_title, auth_type)}
            fill_helpers['pwreset_helper'] = html_link(migoid_link)
        elif auth_flavor == AUTH_MIG_OIDC:
            migoidc_url = os.path.join(os.path.dirname(bin_url), 'reqoidc.py')
            migoidc_link = {'object_type': 'link', 'destination': migoidc_url,
                            'text': 'Change %s %s password' %
                            (configuration.user_mig_oidc_title, auth_type)}
            fill_helpers['pwreset_helper'] = html_link(migoidc_link)
        elif auth_flavor == AUTH_MIG_CERT:
            migcert_url = os.path.join(os.path.dirname(bin_url), 'migcert.py')
            migcert_link = {'object_type': 'link', 'destination': migcert_url,
                            'text': 'Change %s %s password' %
                            (configuration.user_mig_cert_title, auth_type)}
            fill_helpers['pwreset_helper'] = html_link(migcert_link)
        else:
            form_method = 'post'
            csrf_limit = get_csrf_limit(configuration)
            target_op = 'reqpwresetaction'
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            fill_helpers.update({'target_op': target_op, 'form_method':
                                 form_method, 'csrf_field': csrf_field,
                                 'csrf_token': csrf_token, 'cert_id': client_id,
                                 'show': show_local})
            fill_helpers['pwreset_helper'] = '''
            <p>You can reset your password with a reset link sent to your
                email address above for proof of ownership</p>
            '''
            fill_helpers['pwreset_helper'] += account_pw_reset_template(
                configuration, default_values=fill_helpers) % fill_helpers

        html += '''
            <div class="resetpw__header col-12">
                <h3>Password Reset</h3>
                %(pwreset_helper)s
            </div>
    ''' % fill_helpers

    if user_dict.get('status', 'active') == 'temporal':
        bin_url = requested_page(os.environ).replace('-sid', '-bin')
        if auth_flavor == AUTH_MIG_OID:
            migoid_url = os.path.join(os.path.dirname(bin_url), 'reqoid.py')
            migoid_link = {'object_type': 'link', 'destination': migoid_url,
                           'text': 'Change %s %s password' %
                           (configuration.user_mig_oid_title, auth_type)}
            fill_helpers['pwreset_helper'] = html_link(migoid_link)
        elif auth_flavor == AUTH_MIG_OIDC:
            migoidc_url = os.path.join(os.path.dirname(bin_url), 'reqoidc.py')
            migoidc_link = {'object_type': 'link', 'destination': migoidc_url,
                            'text': 'Change %s %s password' %
                            (configuration.user_mig_oidc_title, auth_type)}
            fill_helpers['pwreset_helper'] = html_link(migoidc_link)
        elif auth_flavor == AUTH_MIG_CERT:
            migcert_url = os.path.join(os.path.dirname(bin_url), 'migcert.py')
            migcert_link = {'object_type': 'link', 'destination': migcert_url,
                            'text': 'Change %s %s password' %
                            (configuration.user_mig_cert_title, auth_type)}
            fill_helpers['pwreset_helper'] = html_link(migcert_link)
        else:
            form_method = 'post'
            csrf_limit = get_csrf_limit(configuration)
            target_op = 'autocreate'
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            fill_helpers['autorenew_form_prefix'] = '''
        <form class="autorenew" action="%s.py" method="%s">
            <input type="hidden" name="%s" value="%s">
            <input type="hidden" name="accept_terms" value="yes">
            <input type="hidden" name="peers_full_name" value="%s">
            <input type="hidden" name="peers_email" value="%s">
        ''' % (target_op, form_method, csrf_field, csrf_token,
               user_dict.get('peers_full_name', ''),
               user_dict.get('peers_email', ''))
        if auth_flavor == AUTH_EXT_CERT:
            fill_helpers['autorenew_form_prefix'] += '''
            <input type="hidden" name="cert_id" value="%s">
            <input type="hidden" name="email" value="%s">
            ''' % (client_id, user_dict['email'])
        fill_helpers['autorenew_form_suffix'] = '''
            <input type="submit" value="Renew Account Access">
        </form>
        '''
        html += '''
        <div class="autorenew__header col-12">
            <h3>Renew Access</h3>
            <p>
            Account access automatically expires after a while and needs to be
            actively renewed. If you had someone appoint you as their peer and
            that appointment has not yet expired you can renew your access here
            without further operator or peer contact involvement.
            </p>
            %(autorenew_form_prefix)s
            %(autorenew_form_suffix)s
        </div>
        ''' % fill_helpers

    html += '''
            <div class="col-lg-12 vertical-spacer"></div>
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
