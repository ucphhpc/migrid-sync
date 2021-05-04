#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqcertaction - handle certificate account requests and send email to admins
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

"""Request certificate account action back end"""
from __future__ import absolute_import

# TODO: this backend is horribly KU/UCPH-specific, should move that to conf

import os
import time
import tempfile

from mig.shared import returnvalues
from mig.shared.accountreq import existing_country_code, forced_org_email_match, \
    user_manage_commands
from mig.shared.accountstate import default_account_expire
from mig.shared.base import client_id_dir, force_utf8, force_unicode, \
    generate_https_urls, fill_distinguished_name
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.notification import send_email
from mig.shared.pwhash import scramble_password, assure_password_strength
from mig.shared.serial import dumps


def signature():
    """Signature of the main function"""

    defaults = {
        'cert_name': REJECT_UNSET,
        'org': REJECT_UNSET,
        'email': REJECT_UNSET,
        'country': REJECT_UNSET,
        'state': [''],
        'password': REJECT_UNSET,
        'verifypassword': REJECT_UNSET,
        'comment': [''],
        'accept_terms': [''],
    }
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        logger.warning('%s invalid input: %s' % (op_name, accepted))
        return (accepted, returnvalues.CLIENT_ERROR)

    if not 'migcert' in configuration.site_signup_methods:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''X.509 certificate login is not enabled on this site'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s certificate account request' % \
                          configuration.short_title
    title_entry['skipmenu'] = True
    output_objects.append({'object_type': 'header', 'text':
                           '%s certificate account request' %
                           configuration.short_title
                           })

    admin_email = configuration.admin_email
    smtp_server = configuration.smtp_server
    user_pending = os.path.abspath(configuration.user_pending)

    # TODO: switch to canonical_user fra mig.shared.base instead?
    # force name to capitalized form (henrik karlsen -> Henrik Karlsen)
    # please note that we get utf8 coded bytes here and title() treats such
    # chars as word termination. Temporarily force to unicode.

    raw_name = accepted['cert_name'][-1].strip()
    try:
        cert_name = force_utf8(force_unicode(raw_name).title())
    except Exception:
        cert_name = raw_name.title()
    country = accepted['country'][-1].strip().upper()
    state = accepted['state'][-1].strip().upper()
    org = accepted['org'][-1].strip()

    # lower case email address

    email = accepted['email'][-1].strip().lower()
    password = accepted['password'][-1]
    verifypassword = accepted['verifypassword'][-1]

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
CSRF-filtered POST requests to prevent unintended updates'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not accept_terms:
        output_objects.append({'object_type': 'error_text', 'text':
                               'You must accept the terms of use in sign up!'})
        output_objects.append(
            {'object_type': 'link', 'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Try again"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if password != verifypassword:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Password and verify password are not identical!'
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    try:
        assure_password_strength(configuration, password)
    except Exception as exc:
        logger.warning(
            "%s invalid password for '%s' (policy %s): %s" %
            (op_name, cert_name, configuration.site_password_policy, exc))
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid password requested: %s.'
                               % exc
                               })
        output_objects.append(
            {'object_type': 'link', 'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Try again"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not existing_country_code(country, configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Illegal country code:
Please read and follow the instructions shown in the help bubble when filling
the country field on the request page!
Specifically if you are from the U.K. you need to use GB as country code in
line with the ISO-3166 standard.
'''})
        output_objects.append(
            {'object_type': 'link',
             'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Try again"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # TODO: move this check to conf?

    if not forced_org_email_match(org, email, configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Illegal email and organization combination:
Please read and follow the instructions in red on the request page!
If you are a student with only a @*.ku.dk address please just use KU as
organization. As long as you state that you want the account for course
purposes in the comment field, you will be given access to the necessary
resources anyway.
'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    user_dict = {
        'full_name': cert_name,
        'organization': org,
        'state': state,
        'country': country,
        'email': email,
        'comment': comment,
        'password': scramble_password(configuration.site_password_salt,
                                      password),
        'expire': default_account_expire(configuration, 'cert'),
        'openid_names': [],
        'auth': ['migcert'],
    }
    fill_distinguished_name(user_dict)
    user_id = user_dict['distinguished_name']
    user_dict['authorized'] = (user_id == client_id)
    if configuration.user_openid_providers and configuration.user_openid_alias:
        user_dict['openid_names'] += \
            [user_dict[configuration.user_openid_alias]]
    logger.info('got account request from reqcert: %s' % user_dict)

    # For testing only

    if cert_name.upper().find('DO NOT SEND') != -1:
        output_objects.append(
            {'object_type': 'text', 'text': "Test request ignored!"})
        return (output_objects, returnvalues.OK)

    if not configuration.ca_fqdn or not configuration.ca_user:
        output_objects.append({'object_type': 'error_text', 'text': """
User certificate requests are not supported on this site!"""})
        return (output_objects, returnvalues.CLIENT_ERROR)

    req_path = None
    try:
        (os_fd, req_path) = tempfile.mkstemp(dir=user_pending)
        os.write(os_fd, dumps(user_dict))
        os.close(os_fd)
    except Exception as err:
        logger.error('Failed to write certificate account request to %s: %s'
                     % (req_path, err))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             """Request could not be sent to site administrators. Please
contact them manually on %s if this error persists.""" % admin_email})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.info('Wrote certificate account request to %s' % req_path)
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
    email_header = '%s certificate request for %s' % \
                   (configuration.short_title, cert_name)
    email_msg = \
        """
Received a certificate request with account data
 * Full Name: %(full_name)s
 * Organization: %(organization)s
 * State: %(state)s
 * Country: %(country)s
 * Email: %(email)s
 * Comment: %(comment)s
 * Expire: %(expire)s

Command to create user on %(site)s server:
%(command_user_create)s

Command to create certificate:
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

Command to revoke user certificate:
%(command_cert_revoke)s
You need to copy the resulting signed certificate revocation list (crl.pem)
to the web server(s) for the revocation to take effect.

Command to suspend user on %(site)s server:
%(command_user_suspend)s

Command to delete user again on %(site)s server:
%(command_user_delete)s

---

"""\
         % user_dict

    logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                % (admin_email, email_header, email_msg, smtp_server))
    if not send_email(admin_email, email_header, email_msg, logger,
                      configuration):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             """An error occured trying to send the email requesting the site
administrators to create a new certificate and account. Please email them (%s)
manually and include the session ID: %s""" % (admin_email, tmp_id)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append(
        {'object_type': 'text', 'text': """Request sent to site administrators:
Your certificate account request will be verified and handled as soon as
possible, so please be patient.
Once handled an email will be sent to the account you have specified ('%s')
with further information. In case of inquiries about this request, please email
the site administrators (%s) and include the session ID: %s"""
         % (email, configuration.admin_email, tmp_id)})
    return (output_objects, returnvalues.OK)
