#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# extcertaction - handle external certificate sign up and send email to admins
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

"""External certificate sign up action back end"""

from __future__ import absolute_import

# TODO: this backend is horribly KU/UCPH-specific, should move that to conf

import os
import time
import tempfile

from mig.shared import returnvalues
from mig.shared.accountreq import user_manage_commands, save_account_request
from mig.shared.accountstate import default_account_expire
from mig.shared.base import canonical_user, mask_creds, generate_https_urls, \
    distinguished_name_to_user, fill_distinguished_name, fill_user
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.notification import send_email
from mig.shared.serial import dumps
from mig.shared.useradm import create_user
from mig.shared.userdb import default_db_path


def signature(configuration):
    """Signature of the main function"""

    defaults = {
        'cert_id': REJECT_UNSET,
        'cert_name': REJECT_UNSET,
        'org': REJECT_UNSET,
        'email': REJECT_UNSET,
        'country': REJECT_UNSET,
        'state': [''],
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
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        require_user=False
    )
    if not validate_status:
        # NOTE: 'accepted' is a non-sensitive error string here
        logger.warning('%s invalid input: %s' % (op_name, accepted))
        return (accepted, returnvalues.CLIENT_ERROR)

    short_title = configuration.short_title
    if not 'extcert' in configuration.site_signup_methods:
        output_objects.append({'object_type': 'text', 'text':
                               """X.509 sign up is disabled on this site.
Please contact the %s site support (%s) if you think it should be enabled.
""" % (short_title, configuration.support_email)})
        return (output_objects, returnvalues.OK)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s external certificate sign up' % short_title
    title_entry['skipmenu'] = True
    output_objects.append({'object_type': 'header', 'text':
                           '%s external certificate sign up' % short_title
                           })

    support_email = configuration.support_email
    admin_email = configuration.admin_email
    smtp_server = configuration.smtp_server
    user_pending = os.path.abspath(configuration.user_pending)

    cert_id = accepted['cert_id'][-1].strip()

    cert_name = accepted['cert_name'][-1].strip()
    country = accepted['country'][-1].strip()
    state = accepted['state'][-1].strip()
    org = accepted['org'][-1].strip()
    # NOTE: safeinput thoroughly checks that emails are on valid form
    email = accepted['email'][-1].strip()

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

    is_diku_email = False
    is_diku_org = False
    if email.find('@diku.dk') != -1:
        is_diku_email = True
    if 'DIKU' == org.upper():

        # Consistent upper casing

        org = org.upper()
        is_diku_org = True

    if is_diku_org != is_diku_email:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Illegal email and organization combination:
Please read and follow the instructions in red on the request page!
If you are a DIKU student with only a @*.ku.dk address please just use KU as
organization.
As long as you state that you want the certificate for DIKU purposes in the
comment field, you will be given access to the necessary resources anyway.
'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    try:
        distinguished_name_to_user(cert_id)
    except:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Illegal Distinguished name:
Please note that the distinguished name must be a valid certificate DN with
multiple "key=val" fields separated by "/".
'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    raw_user = {
        'distinguished_name': cert_id,
        'full_name': cert_name,
        'organization': org,
        'state': state,
        'country': country,
        'email': email,
        'password': '',
        'comment': '%s: %s' % ('Existing certificate', comment),
        'expire': default_account_expire(configuration, 'cert'),
        'openid_names': [],
        'auth': ['extcert'],
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
    if configuration.user_openid_providers and configuration.user_openid_alias:
        user_dict['openid_names'] += \
            [user_dict[configuration.user_openid_alias]]
    # IMPORTANT: do NOT log credentials
    logger.info('got account request from extcert: %s' % mask_creds(user_dict))

    # If server allows automatic addition of users with a CA validated cert
    # we create the user immediately and skip mail

    if configuration.auto_add_cert_user:
        fill_user(user_dict)

        # Now all user fields are set and we can begin adding the user

        db_path = default_db_path(configuration)
        try:
            create_user(user_dict, configuration.config_file, db_path,
                        ask_renew=False)
        except Exception as err:
            logger.error('Failed to create user with existing cert %s: %s'
                         % (cert_id, err))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '''Could not create the user account for you:
Please report this problem to the site administrators (%s).''' %
                 admin_email})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({'object_type': 'text', 'text':
                               '''Created the user account for you:
Please use the navigation menu to the left to proceed using it.
'''})
        return (output_objects, returnvalues.OK)

    # Without auto add we end here and go through the mail-to-admins procedure
    (save_status, save_out) = save_account_request(configuration, user_dict)
    if not save_status:
        logger.error(
            'Failed to write existing certificate request %s' % save_out)
        output_objects.append({'object_type': 'error_text', 'text':
                               """Request could not be saved. Please contact
%s site support at %s if this error persists.""" % (short_title,
                                                    support_email)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    req_path = save_out
    logger.info('Wrote existing certificate sign up request to %s' % req_path)
    tmp_id = os.path.basename(req_path)
    user_dict['tmp_id'] = tmp_id

    mig_user = os.environ.get('USER', 'mig')
    helper_commands = user_manage_commands(configuration, mig_user, req_path,
                                           user_id, user_dict, 'cert')
    user_dict.update(helper_commands)
    user_dict['site'] = configuration.short_title
    user_dict['vgrid_label'] = configuration.site_vgrid_label
    user_dict['vgridman_links'] = generate_https_urls(
        configuration, '%(auto_base)s/%(auto_bin)s/vgridman.py', {})
    email_header = '%s certificate sign up request for %s (%s)' % \
                   (short_title, user_dict['full_name'], user_dict['email'])
    email_msg = """
Received an existing certificate sign up request with certificate data
 * Distinguished Name: %(distinguished_name)s
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

Finally add the user
%(distinguished_name)s
to any relevant %(vgrid_label)ss using one of the management links:
%(vgridman_links)s


--- If user must be denied access or deleted at some point ---

Command to reject user account request on %(site)s server:
%(command_user_reject)s

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
admins about your request for existing certificate sign up. Please contact %s site
support at %s and include the session ID: %s""" % (short_title, support_email,
                                                   tmp_id)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append(
        {'object_type': 'text', 'text': """Request sent to site administrators:
Your sign up request with your existing certificate will be verified and
handled as soon as possible, so please be patient.
Once handled an email will be sent to the address you have specified (%r) with
further information. In case of inquiries about this request, please contact
%s site support at %s and include the session ID %r in the message.""" %
         (email, short_title, support_email, tmp_id)})
    return (output_objects, returnvalues.OK)
