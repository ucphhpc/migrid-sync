#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# extoidaction - handle sign up with external openid credentials
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""OpenID sign up action back end"""

import os
import time
import tempfile
import base64
import re

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import oid_valid_days
from shared.functional import validate_input, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables, find_entry
from shared.notification import send_email
from shared.serial import dumps
from shared.useradm import fill_distinguished_name


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
        }
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature()[1]
    logger.debug('in extoidaction: %s' % user_arguments_dict)
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    # Unfortunately OpenID does not use POST
    #if not correct_handler('GET'):
    #    output_objects.append(
    #        {'object_type': 'error_text', 'text'
    #         : 'Only accepting POST requests to prevent unintended updates'})
    #    return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s OpenID sign up' % configuration.short_title
    title_entry['skipmenu'] = True
    output_objects.append({'object_type': 'header', 'text'
                          : '%s OpenID sign up' % \
                            configuration.short_title 
                           })

    admin_email = configuration.admin_email
    smtp_server = configuration.smtp_server
    user_pending = os.path.abspath(configuration.user_pending)

    # force name to capitalized form (henrik karlsen -> Henrik Karlsen)

    id_url = os.environ['REMOTE_USER'].strip()
    openid_prefix = configuration.user_openid_providers[0].rstrip('/') + '/'
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
        'expire': int(time.time() + oid_valid_days * 24 * 60 * 60),
        'openid_names': [raw_login],
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
    except Exception, err:
        logger.error('Failed to write certificate request to %s: %s'
                      % (req_path, err))
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Request could not be sent to grid administrators. Please contact them manually on %s if this error persists.'
                               % admin_email})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.info('Wrote certificate request to %s' % req_path)
    tmp_id = req_path.replace(user_pending, '')
    user_dict['tmp_id'] = tmp_id

    # TODO: remove cert generation or generate pw for it 
    mig_user = os.environ.get('USER', 'mig')
    command_cert_create = \
        """
on CA host (apu01.esci.nbi.dk):
sudo su - mig-ca
rsync %s@%s:mig/server/MiG-users.db ~/
./ca-scripts/createusercert.py -a '%s' -d ~/MiG-users.db -s '%s' -u '%s'"""\
         % (mig_user, configuration.server_fqdn,
            configuration.admin_email, configuration.server_fqdn,
            user_id)
    command_user_create = \
        """
As '%s' on %s:
cd ~/mig/server
./createuser.py -u '%s'"""\
         % (mig_user, configuration.server_fqdn, req_path)
    command_user_delete = \
        """
As '%s' user on %s:
cd ~/mig/server
./deleteuser.py -i '%s'"""\
         % (mig_user, configuration.server_fqdn, user_id)
    command_cert_revoke = \
        """
on CA host (apu01.esci.nbi.dk):
sudo su - mig-ca
./ca-scripts/revokeusercert.py -a '%s' -d ~/MiG-users.db -u '%s'"""\
         % (configuration.admin_email, user_id)

    user_dict['command_user_create'] = command_user_create
    user_dict['command_user_delete'] = command_user_delete
    user_dict['command_cert_create'] = command_cert_create
    user_dict['command_cert_revoke'] = command_cert_revoke
    user_dict['site'] = configuration.short_title
    # NOTE: we only expect cert access for now
    user_dict['https_default_url'] = configuration.migserver_https_cert_url
    email_header = '%s account request for %s' % \
                   (configuration.short_title, full_name)
    email_msg = \
        """
Received an OpenID sign up with user data
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
to any relevant VGrids on:
%(https_default_url)s/cgi-bin/vgridadmin.py


--- If user must be denied access or deleted at some point ---

Remove the user from any relevant VGrids on:
%(https_default_url)s/cgi-bin/vgridadmin.py

Optional command to revoke any user certificates:
%(command_cert_revoke)s
You need to copy the resulting signed certificate revocation list (crl.pem)
to the web server(s) for the revocation to take effect.

Command to delete user again on %(site)s server:
%(command_user_delete)s

---

"""\
         % user_dict

    logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                 % (admin_email, email_header, email_msg, smtp_server))
    if not send_email(admin_email, email_header, email_msg, logger,
                      configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'An error occured trying to send the email requesting the grid administrators to create a new user account. Please email them (%s) manually and include the session ID: %s'
                               % (admin_email, tmp_id)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append(
        {'object_type': 'text', 'text'
         : """Request sent to grid administrators: Your user account will
be created as soon as possible, so please be patient. Once
handled an email will be sent to the account you have specified ('%s') with
further information. In case of inquiries about this request, please email
the grid administrators (%s) and include the session ID: %s"""
         % (email, configuration.admin_email, tmp_id)})
    return (output_objects, returnvalues.OK)
