#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqcert - Certificate request backend
# Copyright (C) 2003-2013  The MiG Project lead by Brian Vinter
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

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.certreq import valid_password_chars, valid_name_chars, \
    password_min_len, password_max_len, js_helpers
from shared.init import initialize_main_variables, find_entry
from shared.functional import validate_input
from shared.useradm import distinguished_name_to_user


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s certificate request' % configuration.short_title
    title_entry['skipmenu'] = True
    form_fields = ['full_name', 'organization', 'email', 'country', 'state',
                   'password', 'verifypassword', 'comment']
    title_entry['javascript'] = js_helpers(form_fields)
    output_objects.append({'object_type': 'html_form',
                           'text':'''
 <div id="contextual_help">
  <div class="help_gfx_bubble"><!--- graphically connect field with help text---></div>
  <div class="help_message"><!-- filled by js --></div>
 </div>
'''                       })
    header_entry = {'object_type': 'header', 'text'
                    : 'Welcome to the %s certificate request page' % \
                    configuration.short_title}
    output_objects.append(header_entry)
    
    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    user_fields = {'full_name': '', 'organization': '', 'email': '',
                   'state': '', 'country': '', 'password': '',
                   'verifypassword': ''}
    if not os.path.isdir(base_dir) and client_id:

        # Redirect to extcert page with certificate requirement but without
        # changing access method (CGI vs. WSGI).

        extcert_url = os.environ['REQUEST_URI'].replace('-sid', '-bin')
        extcert_url = os.path.join(os.path.dirname(extcert_url), 'extcert.py')
        extcert_link = {'object_type': 'link', 'destination': extcert_url,
                        'text': 'Sign up with existing certificate'}
        output_objects.append({'object_type': 'warning', 'text'
                              : 'Apparently you already have a suitable %s certificate that you may sign up with:' % \
                                configuration.short_title
                              })
        output_objects.append(extcert_link)
        output_objects.append({'object_type': 'warning', 'text'
                              : 'However, if you want a dedicated %s certificate you can still request one below:' % \
                                configuration.short_title
                              })
    elif client_id:
        for entry in (title_entry, header_entry):
            entry['text'] = entry['text'].replace('request', 'request / renew')
        output_objects.append({'object_type': 'html_form', 'text'
                              : '''<p>
Apparently you already have a valid %s certificate, but if it is about to
expire you can renew it by posting the form below. Renewal with changed fields
is <span class=mandatory>not</span> supported, so all fields including your
original password must remain unchanged for renew to work. Otherwise it
results in a request for a new account and certificate without access to your
old files, jobs and privileges.</p>''' % \
                               configuration.short_title})
        user_fields.update(distinguished_name_to_user(client_id))

    user_fields.update({
        'valid_name_chars': valid_name_chars,
        'valid_password_chars': valid_password_chars,
        'password_min_len': password_min_len,
        'password_max_len': password_max_len,
        'site': configuration.short_title
        })

    output_objects.append({'object_type': 'html_form', 'text'
                          : """
Please enter your information in at least the <span class=mandatory>mandatory</span> fields below and press the Send button to submit the certificate request to the %(site)s administrators.<p>
<b><font color='red'>IMPORTANT: Please help us verify your identity by providing Organization and Email data that we can easily validate!<br />
That is, if You're a student/employee at KU, please enter institute acronym (NBI, DIKU, etc.) in the Organization field and use your corresponding USER@ACRONYM.dk or USER@*.ku.dk address in the Email field.</font></b></p>
<hr />
<div class=form_container>
<!-- use post here to avoid field contents in URL -->
<form method=post action=reqcertaction.py onSubmit='return validate_form();'>
<table>
<tr><td class='mandatory label'>Full name</td><td><input id='full_name_field' type=text name=cert_name value='%(full_name)s' /></td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Email address</td><td><input id='email_field' type=text name=email value='%(email)s' /> </td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Organization</td><td><input id='organization_field' type=text name=org value='%(organization)s' /></td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Two letter country-code</td><td><input id='country_field' type=text name=country maxlength=2 value='%(country)s' /></td><td class=fill_space><br /></td></tr>
<tr><td class='optional label'>State</td><td><input id='state_field' type=text name=state value='%(state)s' /> </td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Password</td><td><input id='password_field' type=password name=password maxlength=%(password_max_len)s value='%(password)s' /> </td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Verify password</td><td><input id='verifypassword_field' type=password name=verifypassword maxlength=%(password_max_len)s value='%(verifypassword)s' /></td><td class=fill_space><br /></td></tr>
<tr><td class='optional label'>Optional comment or reason why you should<br />be granted a %(site)s certificate:</td><td><textarea id='comment_field' rows=4 name=comment></textarea></td><td class=fill_space><br /></td></tr>
<tr><td class='label'><!--- empty area ---></td><td><input id='submit_button' type=submit value=Send /></td><td class=fill_space><br /></td></tr>
</table>
</form>
</div>
<hr />
<p>
<div class='warn_message'>Please note that passwords may be accessible to the %(site)s administrators!</div>
</p>
<!--- Hidden help text --->
<div id='help_text'>
  <div id='full_name_help'>Your full name, restricted to the characters in '%(valid_name_chars)s'</div>
  <div id='organization_help'>Organization name or acronym  matching email</div>
  <div id='email_help'>Email address associated with your organization if at all possible</div>
  <div id='country_help'>Country code is on the form DE/DK/GB/US/.. , <a href='http://www.iso.org/iso/country_codes/iso_3166_code_lists/country_names_and_code_elements.html'>help</a></div>
  <div id='state_help'>Optional, please just leave empty unless you are a citizen of the US or similar</div>
  <div id='password_help'>Password is restricted to the characters in '%(valid_password_chars)s and must be %(password_min_len)s to %(password_max_len)s characters long'</div>
  <div id='verifypassword_help'>Please repeat password</div>
  <div id='comment_help'>Optional, but a short informative comment may help us verify your certificate needs and thus speed up our response.</div>
</div>
"""
                           % user_fields})

    return (output_objects, returnvalues.OK)


