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
    user_pending = configuration.user_pending

    # force name to capitalized form (henrik karlsen -> Henrik Karlsen)

    cert_name = accepted['cert_name'][-1].title()
    country = accepted['country'][-1].upper()
    state = accepted['state'][-1].title()
    org = accepted['org'][-1]

    # lower case email address

    email = accepted['email'][-1].lower()
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
                              : 'Illegal email and organization combination'
                              })
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Please read and follow the instructions in red!'
                              })
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
    command_cert_create_old = \
        """
Copy password:
%s
to the clipboard (needed several times).
As 'root' on amigos19.diku.dk:
cd /usr/lib/ssl/misc
./mig_gen_cert.sh '%s' '%s' '%s' '%s' '%s' '%s'"""\
         % (
        password,
        cert_name,
        country,
        org,
        state,
        email,
        dest,
        )
    command_user_create = \
        """
As '%s' on %s:
cd ~/mig/server
./createuser.py -u '%s'"""\
         % (mig_user,
            configuration.server_fqdn,
             req_path,
            )
    command_user_create_old = \
        """
As '%s' user on %s:
cd ~/mig/server
./createuser.py '%s' '%s' '%s' '%s' '%s' '%s' '%s'"""\
         % (
             mig_user,
             configuration.server_fqdn,
             cert_name,
             org,
             state,
             country,
             email,
             comment,
             password,
        )
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

    email_header = 'MiG certificate request for %s' % cert_name
    email_msg = \
        """
Certificate data
Common Name: %s
Country: %s
State: %s
Org: %s
Email: %s
Comment: %s

#####
Remember to verify that we really do trust the person with the
specified email address!!

Command to create user on MiG server:
%s

Command to create certificate:
%s

Finally add the user to any relevant VGrids from:
%s/cgi-bin/vgridadmin.py

Use the text below as a template for the email to the new certificate
holder.

Attach: packed file with cert.pem, key.pem, cert.p12 and cacert.pem
#####

To: %s
Subject: Your new MiG certificate 
    
Your new MiG certificate has been created with the pass phrase that you
chose during the certificate request. 

You can access the MiG system in two ways - either by using a browser or
the 'user scripts' (bash and python scripts available at the moment). The
easiest way to get started is to use your browser. The attached .p12
certificate must be imported in your browser, then you can access MiG
by pointing a browser to your personal entry page at:
%s
    
A few more features are available in the 'user scripts', and handling
large amounts of jobs may be easier with the scripts than through the
web interface.

The bash version of the user scripts is limited to unix compatible
installations including curl (http://curl.haxx.se/), whereas the python
version runs on the wider array of platforms supporting python and curl.
If you miss any features on the web page or simply prefer to use the
scripts, it is possible to dynamically generate the latest version from
the Download section on your personal MiG entry page mentioned above.
User scripts rely on the availability of the attached certificate and
key file.

General documentation and information about MiG can be found at:
http://www.migrid.org/
while specific documentation on the 'user scripts' is available from:
http://www.migrid.org/MiG/Mig/user_introduction/user_scripts_intro.html/

Jobs are specified in the 'mRSL' language. Online, on-demand documentation
can be found at:
%s/cgi-bin/docs.py
     
If you have any questions or problems, please don't hesitate to contact
the MiG team by sending an email to one of the following persons:
%s
"""\
         % (
        cert_name,
        country,
        state,
        org,
        email,
        comment,
        command_user_create_old,
        command_cert_create_old,
        configuration.migserver_https_url,
        email,
        configuration.migserver_https_url,
        configuration.migserver_https_url,
        admin_email,
        )

    logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                 % (admin_email, email_header, email_msg, smtp_server))
    user_dict['command_user_create'] = command_user_create
    user_dict['command_user_delete'] = command_user_delete
    user_dict['command_cert_create'] = command_cert_create
    user_dict['migserver_https_url'] = configuration.migserver_https_url
    server_req = \
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

####################################################
# DISCLAIMER: the rest of this mail is obsolete!   #
# - please ignore it unless serious problems arise #
####################################################
"""\
         % user_dict

    if not send_email(admin_email, email_header, server_req
                       + email_msg, logger, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'An error occured trying to send the email requesting the MiG administrators to create a new certificate. Please email the MiG administrators (%s) manually and include the session ID: %s'
                               % (admin_email, tmp_id)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : "Request sent to MiG administrators: The MiG certificate will be generated as soon as possible. When the certificate has been generated an email will be sent to the account you have specified ('%s') with further information. In case of inquiries about this request, please include the session ID: %s"
                           % (email, tmp_id)})
    return (output_objects, returnvalues.OK)


