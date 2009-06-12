#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqcertaction - handle certificate requests and send email to admins
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Request certificate action back end"""

import cgi
import cgitb
cgitb.enable()
import sys
import os
import time
import tempfile
import base64
import pickle

from shared.init import initialize_main_variables
from shared.functional import validate_input, REJECT_UNSET
from shared.notification import send_email
import shared.returnvalues as returnvalues


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
        }
    return ['text', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False,
                                  op_menu=False)
    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG certificate request', 'skipmenu'
                          : True})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG certificate request'})

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    admin_email = configuration.admin_email
    smtp_server = configuration.smtp_server
    user_pending = os.path.abspath(configuration.user_pending)

    # force name to capitalized form (henrik karlsen -> Henrik Karlsen)

    cert_name = accepted['cert_name'][-1].strip().title()
    country = accepted['country'][-1].strip().upper()
    state = accepted['state'][-1].strip().title()
    org = accepted['org'][-1].strip()

    # lower case email address

    email = accepted['email'][-1].strip().lower()
    password = accepted['password'][-1]
    verifypassword = accepted['verifypassword'][-1]

    # keep comment to a single line

    comment = accepted['comment'][-1].replace('\n', '   ')

    # single quotes break command line format - remove

    comment = comment.replace("'", ' ')

    if password != verifypassword:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Password and verify password are not identical!'
                              })
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
        output_objects.append({'object_type': 'error_text', 'text'
                              : '''Illegal email and organization combination:
Please read and follow the instructions in red on the request page!
If you are a DIKU student with only a @*.ku.dk address please just use KU as organization.
As long as you state that you want the certificate for DIKU purposes in the comment field, you
will be given access to the necessary resources anyway.
'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    user_dict = {
        'full_name': cert_name,
        'organization': org,
        'state': state,
        'country': country,
        'email': email,
        'comment': comment,
        'password': base64.b64encode(password),
        'expire': int(time.time() + (((2 * 365.25) * 24) * 60) * 60),
        }
    user_id = '%(full_name)s:%(organization)s:' % user_dict
    user_id += '%(state)s:%(country)s:%(email)s' % user_dict
    req_path = None
    try:
        (os_fd, req_path) = tempfile.mkstemp(dir=user_pending)
        os.write(os_fd, pickle.dumps(user_dict))
        os.close(os_fd)
    except Exception, err:
        logger.error('Failed to write certificate request to %s: %s'
                      % (req_path, err))
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Request could not be sent to MiG administrators. Please contact the MiG administrators %s if this error persists.'
                               % admin_email})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.info('Wrote certificate request to %s' % req_path)
    tmp_id = req_path.replace(user_pending, '')
    user_dict['tmp_id'] = tmp_id

    dest = 'karlsen@erda.imada.sdu.dk'
    mig_user = os.environ.get('USER', 'mig')
    command_cert_create = \
        """
on CA host (amigos19.diku.dk):
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
./deleteuser.py '%s' '%s' '%s' '%s' '%s'"""\
         % (
        mig_user,
        configuration.server_fqdn,
        cert_name,
        org,
        state,
        country,
        email,
        )

    user_dict['command_user_create'] = command_user_create
    user_dict['command_user_delete'] = command_user_delete
    user_dict['command_cert_create'] = command_cert_create
    user_dict['migserver_https_url'] = configuration.migserver_https_url
    email_header = 'MiG certificate request for %s' % cert_name
    email_msg = \
        """
Received a certificate request with certificate data
 * Full Name: %(full_name)s
 * Organization: %(organization)s
 * State: %(state)s
 * Country: %(country)s
 * Email: %(email)s
 * Comment: %(comment)s
 * Expire: %(expire)s

Command to create user on MiG server:
%(command_user_create)s

Command to create certificate:
%(command_cert_create)s

Finally add the user to any relevant VGrids from:
%(migserver_https_url)s/cgi-bin/vgridadmin.py

---
Command to delete user again on MiG server:
%(command_user_delete)s
---

"""\
         % user_dict

    logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                 % (admin_email, email_header, email_msg, smtp_server))
    if not send_email(admin_email, email_header, email_msg, logger,
                      configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'An error occured trying to send the email requesting the MiG administrators to create a new certificate. Please email the MiG administrators (%s) manually and include the session ID: %s'
                               % (admin_email, tmp_id)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : "Request sent to MiG administrators: The MiG certificate will be generated as soon as possible. When the certificate has been generated an email will be sent to the account you have specified ('%s') with further information. In case of inquiries about this request, please include the session ID: %s"
                           % (email, tmp_id)})
    return (output_objects, returnvalues.OK)


