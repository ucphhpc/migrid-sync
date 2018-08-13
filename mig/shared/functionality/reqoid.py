#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqoid - OpenID account request backend
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Request OpenID account back end"""

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir, distinguished_name_to_user
from shared.accountreq import valid_password_chars, valid_name_chars, \
    password_min_len, password_max_len, account_js_helpers
from shared.defaults import csrf_field
from shared.functional import validate_input
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.safeinput import html_escape


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
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s OpenID account request' % \
                          configuration.short_title
    title_entry['skipmenu'] = True
    form_fields = ['full_name', 'organization', 'email', 'country', 'state',
                   'password', 'verifypassword', 'comment']
    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] = account_js_helpers(form_fields)
    output_objects.append({'object_type': 'html_form',
                           'text': '''
 <div id="contextual_help">
  <div class="help_gfx_bubble"><!-- graphically connect field with help text --></div>
  <div class="help_message"><!-- filled by js --></div>
 </div>
'''})
    header_entry = {'object_type': 'header', 'text':
                    'Welcome to the %s OpenID account request page' %
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
                        'text': 'Sign up with existing certificate (%s)' %
                        client_id}
        output_objects.append({'object_type': 'warning', 'text': '''Apparently
you already have a suitable %s certificate that you may sign up with:''' %
                               configuration.short_title
                               })
        output_objects.append(extcert_link)
        output_objects.append({'object_type': 'warning', 'text': '''However,
if you want a dedicated %s %s User OpenID you can still request one below:'''
                               % (configuration.short_title,
                                  configuration.user_mig_oid_title)})
    elif client_id:
        for entry in (title_entry, header_entry):
            entry['text'] = entry['text'].replace('request', 'request / renew')
        output_objects.append({'object_type': 'html_form', 'text': '''<p>
Apparently you already have valid %s credentials, but if you want to add %s
User OpenID access to the same account you can do so by posting the form below.
Changing fields is <span class=mandatory> not </span> supported, so all fields
must remain unchanged for it to work.
Otherwise it results in a request for a new account and OpenID without access
to your old files, jobs and privileges. </p>''' %
                               (configuration.short_title,
                                configuration.user_mig_oid_title)})
        user_fields.update(distinguished_name_to_user(client_id))

    user_fields.update({
        'valid_name_chars': '%s (and common accents)' %
        html_escape(valid_name_chars),
        'valid_password_chars': html_escape(valid_password_chars),
        'password_min_len': password_min_len,
        'password_max_len': password_max_len,
        'site': configuration.short_title
    })
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'reqoidaction'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    fill_helpers.update({'site_signup_hint': configuration.site_signup_hint})
    fill_helpers.update(user_fields)
    output_objects.append({'object_type': 'html_form', 'text': """
Please enter your information in at least the <span class=mandatory>mandatory</span> fields below and press the Send button to submit the OpenID account request to the %(site)s administrators.
<p class='criticaltext highlight_message'>
IMPORTANT: Please help us verify your identity by providing Organization and
Email data that we can easily validate!
</p>
%(site_signup_hint)s
<hr />
<div class=form_container>
<!-- use post here to avoid field contents in URL -->
<form method='%(form_method)s' action='%(target_op)s.py' onSubmit='return validate_form();'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<table>
<!-- NOTE: javascript support for unicode pattern matching is lacking so we
           only restrict e.g. Full Name to words separated by space here. The
           full check takes place in the backend, but users are better of with
           sane early warnings than the cryptic backend errors.
-->
<tr><td class='mandatory label'>Full name</td><td><input id='full_name_field' type=text name=cert_name value='%(full_name)s' required pattern='[^ ]+([ ][^ ]+)+' title='Your full name, i.e. two or more names separated by space' /></td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Email address</td><td><input id='email_field' type=email name=email value='%(email)s' required title='A valid email address that you read' /> </td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Organization</td><td><input id='organization_field' type=text name=org value='%(organization)s' required pattern='[^ ]+([ ][^ ]+)*' title='Name of your organisation: one or more abbreviations or words separated by space' /></td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Two letter country-code</td><td><input id='country_field' type=text name=country minlength=2 maxlength=2 value='%(country)s' required pattern='[A-Z]{2}' title='The two capital letters used to abbreviate your country' /></td><td class=fill_space><br /></td></tr>
<tr><td class='optional label'>State</td><td><input id='state_field' type=text name=state value='%(state)s' pattern='([A-Z]{2})?' maxlength=2 title='Leave empty or enter the capital 2-letter abbreviation of your state if you are a US resident' /> </td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Password</td><td><input id='password_field' type=password name=password minlength=%(password_min_len)d maxlength=%(password_max_len)d value='%(password)s' required pattern='.{%(password_min_len)d,%(password_max_len)d}' title='Password of your choice, see help box for limitations' /> </td><td class=fill_space><br /></td></tr>
<tr><td class='mandatory label'>Verify password</td><td><input id='verifypassword_field' type=password name=verifypassword minlength=%(password_min_len)d maxlength=%(password_max_len)d value='%(verifypassword)s' required pattern='.{%(password_min_len)d,%(password_max_len)d}' title='Repeat your chosen password' /></td><td class=fill_space><br /></td></tr>
<!-- NOTE: we technically allow saving the password on scrambled form hide it by default -->
<tr class='hidden'><td class='optional label'>Password recovery</td><td class=''><input id='passwordrecovery_checkbox' type=checkbox name=passwordrecovery></td>
</td><td class=fill_space><br/></td></tr>
<tr><td class='optional label'>Optional comment or reason why you should<br />be granted a %(site)s account:</td><td><textarea id='comment_field' rows=4 name=comment title='A free-form comment where you can explain what you need the account for' ></textarea></td><td class=fill_space><br /></td></tr>
<tr><td class='label'><!-- empty area --></td><td><input id='submit_button' type=submit value=Send /></td><td class=fill_space><br/></td></tr>
</table>
</form>
<hr />
<div class='warn_message'>Please note that if you enable password recovery your password will be saved on encoded format but recoverable by the %(site)s administrators</div>
</div>
<br />
<br />
<!-- Hidden help text -->
<div id='help_text'>
  <div id='full_name_help'>Your full name, restricted to the characters in '%(valid_name_chars)s'</div>
  <div id='organization_help'>Organization name or acronym  matching email</div>
  <div id='email_help'>Email address associated with your organization if at all possible</div>
  <div id='country_help'>Country code of your organization and on the form DE/DK/GB/US/.. , <a href='https://en.wikipedia.org/wiki/ISO_3166-1'>help</a></div>
  <div id='state_help'>Optional 2-letter ANSI state code of your organization, please just leave empty unless it is in the US or similar, <a href='https://en.wikipedia.org/wiki/List_of_U.S._state_abbreviations'>help</a></div>
  <div id='password_help'>Password is restricted to the characters in '%(valid_password_chars)s and must be %(password_min_len)s to %(password_max_len)s characters long'</div>
  <div id='verifypassword_help'>Please repeat password</div>
  <div id='comment_help'>Optional, but a short informative comment may help us verify your account needs and thus speed up our response.</div>
</div>
""" % fill_helpers})

    return (output_objects, returnvalues.OK)
