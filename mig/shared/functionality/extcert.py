#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# extcert - External certificate sign up backend
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

"""Request sign up with external certificate back end"""

import os

import shared.returnvalues as returnvalues
from shared.certreq import valid_name_chars, dn_max_len
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert
from shared.useradm import distinguished_name_to_user


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
    output_objects.append({'object_type': 'header', 'text'
                          : 'Welcome to the %s user sign up page' % \
                            configuration.site_title
                          })

    defaults = signature()[1]
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
        return (accepted, returnvalues.CLIENT_ERROR)

    # Redirect to reqcert page without certificate requirement but without
    # changing access method (CGI vs. WSGI).
    
    certreq_url = os.environ['REQUEST_URI'].replace('-bin', '-sid')
    certreq_url = os.path.join(os.path.dirname(certreq_url), 'reqcert.py')
    certreq_link = {'object_type': 'link', 'destination': certreq_url,
                    'text': 'Request a new %s certificate' % \
                            configuration.short_title }
    new_user = distinguished_name_to_user(client_id)

    output_objects.append({'object_type': 'html_form', 'text'
                          : """
This page is used to sign up for %(site)s with an existing certificate from a Certificate Authority (CA) allowed for %(site)s.
You can use it if you already have a x509 certificate from another accepted CA. In this way you can simply use your existing certificate for %(site)s access instead of requesting a new one.
<br />
The page tries to auto load any certificate your browser provides and fill in the fields accordingly, but in case it can't guess all <span class=mandatory>mandatory</span> fields, you still need to fill in those.<br />
Please enter any missing information below and press the Send button to submit the external certificate sign up request to the %(site)s administrators.<p>
<b><font color='red'>IMPORTANT: Please help us verify your identity by providing Organization and Email data that we can easily validate!<br />
That is, if You're a student/employee at DIKU, please type DIKU in the Organization field and use your USER@diku.dk address in the Email field.</font></b></p>
<hr />
<p>
<!-- use post here to avoid field contents in URL -->
<form method=post action=extcertaction.py>
<table>
<tr><td>Certificate DN</td>
<td><input type=text size=%(dn_max_len)s maxlength=%(dn_max_len)s name=cert_id value='%(client_id)s' /> <sup class=mandatory>1</sup></td>
</tr>
<tr><td>Full name</td><td><input type=text name=cert_name value='%(common_name)s' /> <sup class=mandatory>2</sup></td></tr>
<tr><td>Organization</td><td><input type=text name=org value='%(org)s' /> <sup class=mandatory>3</sup></td></tr>
<tr><td>Email address</td><td><input type=text name=email value='%(email)s' /> <sup class=mandatory>4</sup></td></tr>
<tr><td>State</td><td><input type=text name=state value='%(state)s' /> <sup class=optional>5</sup></td></tr>
<tr><td>Two letter country-code</td><td><input type=text name=country maxlength=2 value='%(country)s' /> <sup class=mandatory>6</sup></td></tr>
<tr><td>Comment or reason why you should<br />be granted a %(site)s certificate:</td><td><textarea rows=4 cols=%(dn_max_len)s name=comment></textarea> <sup class=optional>7</sup></td></tr>
<tr><td><input type='submit' value='Send' /></td><td></td></tr>
</table>
</form>
</p>
<hr />
<p>
<font size=-1>
<sup>1</sup> must be the exact Distinguished Name (DN) of your certificate<br />
<sup>2</sup> restricted to the characters in '%(valid_name_chars)s'<br />
<sup>3</sup> name or acronym<br />
<sup>4</sup> address associated with organization if at all possible<br />
<sup>5</sup> optional (just leave empty if you're not located in e.g the U.S.)<br />
<sup>6</sup> country code is on the form GB/DK/.. , <a href=http://www.iso.org/iso/en/prods-services/iso3166ma/02iso-3166-code-lists/list-en1.html>help</a><br />
<sup>7</sup> optional, but a short informative comment may help us verify your certificate needs and thus speed up our response.<br />
</font>
</p>
"""
                           % {
        'valid_name_chars': valid_name_chars,
        'client_id': client_id,
        'dn_max_len': dn_max_len,
        'common_name': new_user.get('full_name', ''),
        'org': new_user.get('organization', ''),
        'email': new_user.get('email', ''),
        'state': new_user.get('state', ''),
        'country': new_user.get('country', ''),
        'site': configuration.short_title,
        }})

    return (output_objects, returnvalues.OK)


