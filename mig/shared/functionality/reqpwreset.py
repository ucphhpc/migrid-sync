#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqpwreset - Account password reset request backend
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Request account password reset back end"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir, distinguished_name_to_user, \
    canonical_user, cert_field_map, requested_page
from mig.shared.accountreq import valid_password_chars, valid_name_chars, \
    password_min_len, password_max_len, account_pw_reset_template, \
    account_css_helpers
from mig.shared.defaults import csrf_field, keyword_auto, AUTH_MIG_OID, \
    AUTH_MIG_OIDC, AUTH_MIG_CERT
from mig.shared.functional import validate_input
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.httpsclient import detect_client_auth
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.pwcrypto import parse_password_policy
from mig.shared.safeinput import html_escape


def signature(configuration):
    """Signature of the main function"""

    local_login_methods = [i for i in configuration.site_login_methods
                           if not i.startswith('ext')]
    defaults = {'cert_id': [''], 'show': local_login_methods}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    client_dir = client_id_dir(client_id)
    defaults = signature(configuration)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    show = accepted['show']
    local_auth = [i for i in configuration.site_login_methods
                  if i.startswith('mig')]
    if not local_auth:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''No local login to reset password for on this site'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    unsupported = [i for i in show if not i in local_auth]
    if unsupported:
        output_objects.append(
            {'object_type': 'html_form', 'text':
             '''<span class="warningtext">
             Warning: ignored requested but unsupported show value(s): %s
             </span>'''
             % ', '.join(unsupported)})

    show_local = [i for i in show if i in local_auth]
    if not show_local:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''Please provide a supported value (%s) for the show argument'''
             % ', '.join(local_auth)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s account password reset request' % \
                          configuration.short_title
    title_entry['skipmenu'] = True
    form_fields = ['cert_id']
    # TODO: are these css tweaks needed?
    title_entry['style']['advanced'] += account_css_helpers(configuration)
    title_entry['script']['body'] = "class='staticpage'"

    header_entry = {'object_type': 'header', 'text':
                    '%s account password reset request' %
                    configuration.short_title}
    output_objects.append(header_entry)

    output_objects.append({'object_type': 'html_form', 'text': '''
    <div id="contextual_help">

    </div>
'''})

    # If already authenticated just redirect to sign up form for auto-fill
    # based on client_id and without changing access method (CGI vs. WSGI).
    if client_id:
        (auth_type, auth_flavor) = detect_client_auth(configuration, environ)
        bin_url = requested_page(os.environ).replace('-sid', '-bin')
        if auth_flavor == AUTH_MIG_OID:
            migoid_url = os.path.join(os.path.dirname(bin_url), 'reqoid.py')
            migoid_link = {'object_type': 'link', 'destination': migoid_url,
                           'text': 'Change %s %s password' %
                           (configuration.user_mig_oid_title, auth_type)}
            output_objects.append(migoid_link)
        elif auth_flavor == AUTH_MIG_OIDC:
            migoidc_url = os.path.join(os.path.dirname(bin_url), 'reqoidc.py')
            migoidc_link = {'object_type': 'link', 'destination': migoidc_url,
                            'text': 'Change %s %s password' %
                            (configuration.user_mig_oid_title, auth_type)}
            output_objects.append(migoidc_link)
        elif auth_flavor == AUTH_MIG_CERT:
            extcert_url = os.path.join(os.path.dirname(bin_url), 'extcert.py')
            extcert_link = {'object_type': 'link', 'destination': extcert_url,
                            'text': 'Change %s %s password' %
                            (configuration.user_mig_cert_title, auth_type)}
            output_objects.append(extcert_link)
    else:
        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        fill_helpers = {'form_method': form_method, 'csrf_field': csrf_field,
                        'csrf_limit': csrf_limit,
                        'short_title': configuration.short_title}
        target_op = "reqpwresetaction"
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token,
                             'show': show_local})
        html = account_pw_reset_template(configuration,
                                         default_values=fill_helpers)
        output_objects.append({'object_type': 'html_form', 'text': html %
                               fill_helpers})

    return (output_objects, returnvalues.OK)
