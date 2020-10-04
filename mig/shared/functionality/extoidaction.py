#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# extoidaction - handle account sign up with external OpenID credentials
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

"""OpenID account sign up action back end"""
from __future__ import absolute_import

import os
import time
import tempfile
import base64
import re

from mig.shared import returnvalues
from mig.shared.accountreq import user_manage_commands
from mig.shared.accountstate import default_account_expire
from mig.shared.base import client_id_dir, generate_https_urls, \
    fill_distinguished_name
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.notification import send_email
from mig.shared.serial import dumps


def signature():
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
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature()[1]
    logger.debug('in extoidaction: %s' % user_arguments_dict)
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    # Unfortunately OpenID does not use POST
    # if not safe_handler(configuration, 'post', op_name, client_id,
    #                    get_csrf_limit(configuration), accepted):
    #    output_objects.append(
    #        {'object_type': 'error_text', 'text': '''Only accepting
# CSRF-filtered POST requests to prevent unintended updates'''
    #         })
    #    return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s OpenID account sign up' % configuration.short_title
    title_entry['skipmenu'] = True
    output_objects.append({'object_type': 'header', 'text':
                           '%s OpenID account sign up' %
                           configuration.short_title})

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

    user_dict = {
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
    }
    fill_distinguished_name(user_dict)
    user_id = user_dict['distinguished_name']
    if configuration.user_openid_providers and configuration.user_openid_alias:
        user_dict['openid_names'].append(
            user_dict[configuration.user_openid_alias])

    req_path = None
    try:
        (os_fd, req_path) = tempfile.mkstemp(dir=user_pending)
        os.write(os_fd, dumps(user_dict))
        os.close(os_fd)
    except Exception as err:
        logger.error('Failed to write OpenID account request to %s: %s'
                     % (req_path, err))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''Request could not be sent to site administrators. Please
contact them manually on %s if this error persists.''' % admin_email})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.info('Wrote OpenID account request to %s' % req_path)
    tmp_id = req_path.replace(user_pending, '')
    user_dict['tmp_id'] = tmp_id

    # TODO: remove cert generation or generate pw for it
    mig_user = os.environ.get('USER', 'mig')
    helper_commands = user_manage_commands(configuration, mig_user, req_path,
                                           user_id, user_dict, 'oid')
    user_dict.update(helper_commands)
    user_dict['site'] = configuration.short_title
    user_dict['vgrid_label'] = configuration.site_vgrid_label
    user_dict['vgridman_links'] = generate_https_urls(
        configuration, '%(auto_base)s/%(auto_bin)s/vgridman.py', {})
    email_header = '%s OpenID request for %s' % \
                   (configuration.short_title, full_name)
    email_msg = """
Received an OpenID account sign up with user data
 * Full Name: %(full_name)s
 * Organization: %(organization)s
 * State: %(state)s
 * Country: %(country)s
 * Email: %(email)s
 * Comment: %(comment)s
 * Expire: %(expire)s

Command to create user on %(site)s server:
%(command_user_create)s

Optional command to create matching certificate:
%(command_cert_create)s

Finally add the user
%(distinguished_name)s
to any relevant %(vgrid_label)ss using one of the management links:
%(vgridman_links)s


--- If user must be denied access or deleted at some point ---

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

""" % user_dict

    logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                % (admin_email, email_header, email_msg, smtp_server))
    if not send_email(admin_email, email_header, email_msg, logger,
                      configuration):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''An error occured trying to send the email requesting your new
user account. Please email the site administrators (%s) manually and include
the session ID: %s''' % (admin_email, tmp_id)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append(
        {'object_type': 'text', 'text':
         """Request sent to site administrators: Your user account will
be created as soon as possible, so please be patient. Once handled an email
will be sent to the account you have specified ('%s') with further information.
In case of inquiries about this request, please email the site administrators
(%s) and include the session ID: %s"""
         % (email, configuration.admin_email, tmp_id)})
    return (output_objects, returnvalues.OK)
