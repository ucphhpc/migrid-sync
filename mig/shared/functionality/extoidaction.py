#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# extoidaction - handle account sign up with external OpenID credentials
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

"""OpenID account sign up action back end"""

from __future__ import absolute_import

import os
import time
import tempfile

from mig.shared import returnvalues
from mig.shared.accountreq import user_manage_commands, save_account_request
from mig.shared.accountstate import default_account_expire
from mig.shared.base import client_id_dir, canonical_user, mask_creds, \
    generate_https_urls, fill_distinguished_name
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.notification import send_email
from mig.shared.serial import dumps


def signature(configuration):
    """Signature of the main function"""

    defaults = {
        'openid.ns.sreg': [''],
        'openid.sreg.full_name': REJECT_UNSET,
        'openid.sreg.organization': REJECT_UNSET,
        'openid.sreg.organizational_unit': REJECT_UNSET,
        'openid.sreg.locality': [''],
        'openid.sreg.state': [''],
        'openid.sreg.email': REJECT_UNSET,
        'openid.sreg.country': [''],
        'state': [''],
        'password': [''],
        'comment': [''],
        'accept_terms': [''],
    }
    if configuration.site_enable_peers:
        if configuration.site_peers_mandatory:
            peers_default = REJECT_UNSET
        else:
            peers_default = ['']
        for field_name in configuration.site_peers_explicit_fields:
            defaults['peers_%s' % field_name] = peers_default
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature(configuration)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        # NOTE: 'accepted' is a non-sensitive error string here
        logger.warning('%s invalid input: %s' % (op_name, accepted))
        return (accepted, returnvalues.CLIENT_ERROR)

    short_title = configuration.short_title
    if not 'extoid' in configuration.site_signup_methods:
        output_objects.append({'object_type': 'text', 'text':
                               """OpenID sign up is disabled on this site.
Please contact the %s site support (%s) if you think it should be enabled.
""" % (short_title, configuration.support_email)})
        return (output_objects, returnvalues.OK)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s OpenID account sign up' % short_title
    title_entry['skipmenu'] = True
    output_objects.append({'object_type': 'header', 'text':
                           '%s OpenID account sign up' % short_title
                           })

    support_email = configuration.support_email
    admin_email = configuration.admin_email
    smtp_server = configuration.smtp_server
    user_pending = os.path.abspath(configuration.user_pending)

    # force name to capitalized form (henrik karlsen -> Henrik Karlsen)

    id_url = os.environ['REMOTE_USER'].strip()
    openid_prefix = configuration.user_ext_oid_provider.rstrip('/') + '/'
    raw_login = id_url.replace(openid_prefix, '')
    full_name = accepted['openid.sreg.full_name'][-1].strip().title()
    country = accepted['openid.sreg.country'][-1].strip().upper()
    state = accepted['state'][-1].strip().title()
    organization = accepted['openid.sreg.organization'][-1].strip()
    organizational_unit = accepted['openid.sreg.organizational_unit'][-1].strip()
    locality = accepted['openid.sreg.locality'][-1].strip()

    # lower case email address

    email = accepted['openid.sreg.email'][-1].strip().lower()
    password = accepted['password'][-1]
    #verifypassword = accepted['verifypassword'][-1]

    if configuration.site_enable_peers:
        # Peers are passed as multiple strings of comma or space separated emails
        # so we reformat to a consistently comma+space separated string.
        peers_full_name_list = []
        for entry in accepted.get('peers_full_name', ['']):
            peers_full_name_list += [i.strip() for i in entry.split(',')]
        peers_full_name = ', '.join(peers_full_name_list)
        peers_email_list = []
        for entry in accepted.get('peers_email', ['']):
            peers_email_list += [i.strip() for i in entry.split(',')]
        peers_email = ', '.join(peers_email_list)

    # keep comment to a single line

    comment = accepted['comment'][-1].replace('\n', '   ')

    # single quotes break command line format - remove

    comment = comment.replace("'", ' ')
    accept_terms = (accepted['accept_terms'][-1].strip().lower() in
                    ('1', 'o', 'y', 't', 'on', 'yes', 'true'))

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not accept_terms:
        output_objects.append({'object_type': 'error_text', 'text':
                               'You must accept the terms of use in sign up!'})
        output_objects.append(
            {'object_type': 'link', 'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Try again"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    raw_user = {
        'full_name': full_name,
        'organization': organization,
        'organizational_unit': organizational_unit,
        'locality': locality,
        'state': state,
        'country': country,
        'email': email,
        'password': password,
        'comment': comment,
        'expire': default_account_expire(configuration, 'oid'),
        'openid_names': [raw_login],
        'auth': ['extoid'],
        'accepted_terms': time.time(),
    }
    if configuration.site_enable_peers:
        raw_user['peers_full_name'] = peers_full_name
        raw_user['peers_email'] = peers_email

    # Force user ID fields to canonical form for consistency
    # Title name, lowercase email, uppercase country and state, etc.
    user_dict = canonical_user(configuration, raw_user, raw_user.keys())
    fill_distinguished_name(user_dict)
    user_id = user_dict['distinguished_name']
    user_dict['authorized'] = (user_id == client_id)
    if configuration.user_openid_providers and configuration.user_openid_alias:
        user_dict['openid_names'].append(
            user_dict[configuration.user_openid_alias])
    # IMPORTANT: do NOT log credentials
    logger.info('got account request from extoid: %s' % mask_creds(user_dict))

    # For testing only

    if full_name.upper().find('DO NOT SEND') != -1:
        output_objects.append(
            {'object_type': 'text', 'text': "Test request ignored!"})
        return (output_objects, returnvalues.OK)

    (save_status, save_out) = save_account_request(configuration, user_dict)
    if not save_status:
        logger.error('Failed to write OpenID account request: %s' % save_out)
        output_objects.append({'object_type': 'error_text', 'text':
                               """Request could not be saved. Please contact
%s site support at %s if this error persists.""" % (short_title,
                                                    support_email)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    req_path = save_out
    logger.info('Wrote OpenID account request to %s' % req_path)
    tmp_id = os.path.basename(req_path)
    user_dict['tmp_id'] = tmp_id

    # TODO: remove cert generation or generate pw for it
    mig_user = os.environ.get('USER', 'mig')
    helper_commands = user_manage_commands(configuration, mig_user, req_path,
                                           user_id, user_dict, 'oid')
    user_dict.update(helper_commands)
    user_dict['site'] = short_title
    user_dict['vgrid_label'] = configuration.site_vgrid_label
    user_dict['vgridman_links'] = generate_https_urls(
        configuration, '%(auto_base)s/%(auto_bin)s/vgridman.py', {})
    email_header = '%s OpenID sign up request for %s (%s)' % \
                   (short_title, user_dict['full_name'], user_dict['email'])
    email_msg = """
Received an OpenID account sign up with user data
 * Full Name: %(full_name)s
 * Organization: %(organization)s
 * State: %(state)s
 * Country: %(country)s
 * Email: %(email)s"""
    if configuration.site_enable_peers:
        email_msg += """
 * Peers: %(peers_full_name)s (%(peers_email)s)"""
    email_msg += """
 * Comment: %(comment)s
 * Expire: %(expire)s

Command to create user on %(site)s server:
%(command_user_create)s

Command to inform user and %(site)s admins:
%(command_user_notify)s

Optional command to create matching certificate:
%(command_cert_create)s

Finally add the user
%(distinguished_name)s
to any relevant %(vgrid_label)ss using one of the management links:
%(vgridman_links)s


--- If user must be denied access or deleted at some point ---

Command to reject user account request on %(site)s server:
%(command_user_reject)s

Remove the user
%(distinguished_name)s
from any relevant %(vgrid_label)ss using one of the management links:
%(vgridman_links)s

Optional command to revoke any user certificates:
%(command_cert_revoke)s
You need to copy the resulting signed certificate revocation list (crl.pem)
to the web server(s) for the revocation to take effect.

Command to suspend user on %(site)s server:
%(command_user_suspend)s

Command to delete user again on %(site)s server:
%(command_user_delete)s

---

"""
    email_msg = email_msg % user_dict

    logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                % (admin_email, email_header, email_msg, smtp_server))
    if not send_email(admin_email, email_header, email_msg, logger,
                      configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               """An error occurred trying to inform the site
admins about your request for OpenID account access. Please contact %s site
support at %s and include the session ID: %s""" % (short_title, support_email,
                                                   tmp_id)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append(
        {'object_type': 'text', 'text': """Request sent to site administrators:
Your user account will be created as soon as possible, so please be patient. 
Once handled an email will be sent to the address you have specified (%r) with
further information. In case of inquiries about this request, please contact
%s site support at %s and include the session ID %r in the message.""" %
         (email, short_title, support_email, tmp_id)})
    return (output_objects, returnvalues.OK)
