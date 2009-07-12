#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqcert - Certificate request backend
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

"""Request certificate back end"""

import sys
import os

from shared.certreq import valid_password_chars, valid_name_chars, \
    password_min_len, password_max_len
from shared.init import initialize_main_variables
from shared.functional import validate_input, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False,
                                  op_menu=False)
    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG certificate request', 'skipmenu'
                          : True})
    output_objects.append({'object_type': 'header', 'text'
                          : 'Welcome to the MiG certificate request page'
                          })

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    extcert_link = {'object_type': 'link', 'destination': 'extcert.py',
                    'text': 'Sign up with existing certificate'}
    if client_id:
        output_objects.append({'object_type': 'warning', 'text':
                               'Apparently you already have a suitable MiG certificate that you may sign up with:'})
        output_objects.append(extcert_link)
        output_objects.append({'object_type': 'warning', 'text':
                               'However, if you want a dedicated MiG certificate you can still request one below:'})

    output_objects.append({'object_type': 'html_form', 'text'
                          : """
Please enter your information in at least the <span class=mandatory>mandatory</span> fields below and press the Send button to submit the certificate request to the MiG administrators.<p>
<b><font color='red'>IMPORTANT: Please help us verify your identity by providing Organization and Email data that we can easily validate!<br>
That is, if You're a student/employee at DIKU, please type DIKU in the Organization field and use your USER@diku.dk address in the Email field.</font></b><p>
<hr>
<p>
<!-- use post here to avoid field contents in URL -->
<form method=post action=reqcertaction.py>
<input type=hidden commit=true>
<table>
<tr><td>Full name</td><td><input type=text name=cert_name> <sup class=mandatory>1</sup></td></tr>
<tr><td>Organization</td><td><input type=text name=org> <sup class=mandatory>2</sup></td></tr>
<tr><td>Email address</td><td><input type=text name=email> <sup class=mandatory>3</sup></td></tr>
<tr><td>State</td><td><input type=text name=state> <sup class=optional>4</sup></td></tr>
<tr><td>Two letter country-code</td><td><input type=text name=country maxlength=2> <sup class=mandatory>5</sup></td></tr>
<tr><td>Password</td><td><input type=password name=password maxlength=%(password_max_len)s> <sup class=mandatory>6, 7</sup></td></tr>
<tr><td>Verify password</td><td><input type=password name=verifypassword maxlength=%(password_max_len)s> <sup class=mandatory>6, 7</sup></td></tr>
<tr><td>Comment or reason why you should<br>be granted a MiG certificate:</td><td><textarea rows=4 cols=%(password_max_len)s name=comment></textarea> <sup class=optional>8</sup></td></tr>
<tr><td><input type=submit value=Send></td><td></td></tr>
</table>
</form>
<p>
<font color='red'>Please note that passwords will be visible to the MiG administrators!</font><p>
<hr>
<p>
<font size=-1>
<sup>1</sup> restricted to the characters in '%(valid_name_chars)s'<br>
<sup>2</sup> name or acronym<br>
<sup>3</sup> address associated with organization if at all possible<br>
<sup>4</sup> optional<br>
<sup>5</sup> Country code is on the form GB/DK/.. , <a href=http://www.iso.org/iso/en/prods-services/iso3166ma/02iso-3166-code-lists/list-en1.html>help</a><br>
<sup>6</sup> Password is restricted to the characters in '%(valid_password_chars)s'<br>
<sup>7</sup> Password must be at least %(password_min_len)s and at most %(password_max_len)s characters long<br> 
<sup>8</sup> optional, but a short informative comment may help us verify your certificate needs and thus speed up our response.<br>
</font>
<p>
"""
                           % {
        'valid_name_chars': valid_name_chars,
        'valid_password_chars': valid_password_chars,
        'password_min_len': password_min_len,
        'password_max_len': password_max_len,
        }})

    return (output_objects, returnvalues.OK)


