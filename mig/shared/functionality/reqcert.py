#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqcert - Certificate account request backend
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

"""Request certificate account back end"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir, distinguished_name_to_user, \
    canonical_user, cert_field_map, requested_page
from mig.shared.accountreq import valid_password_chars, valid_name_chars, \
    password_min_len, password_max_len, account_js_helpers, \
    account_css_helpers, account_request_template
from mig.shared.defaults import csrf_field, keyword_auto
from mig.shared.functional import validate_input
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.pwcrypto import parse_password_policy
from mig.shared.safeinput import html_escape


def signature(configuration):
    """Signature of the main function"""

    defaults = {'full_name': [''],
                'organization': [''],
                'email': [''],
                'country': [''],
                'state': [''],
                'comment': [''],
                'ro_fields': [''],
                'reset_token': [''],
                }
    if configuration.site_enable_peers:
        for field_name in configuration.site_peers_explicit_fields:
            defaults['peers_%s' % field_name] = ['']
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    client_dir = client_id_dir(client_id)
    defaults = signature(configuration)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    if not 'migcert' in configuration.site_signup_methods:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''X.509 certificate login is not enabled on this site'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    reset_token = accepted['reset_token'][-1].strip()

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s certificate account request' % \
                          configuration.short_title
    title_entry['skipmenu'] = True
    form_fields = ['full_name', 'organization', 'email', 'country', 'state',
                   'password', 'verifypassword', 'comment']
    title_entry['style']['advanced'] += account_css_helpers(configuration)
    add_import, add_init, add_ready = account_js_helpers(configuration,
                                                         form_fields)
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    title_entry['script']['body'] = "class='staticpage'"
#    output_objects.append({'object_type': 'html_form',
#                           'text': '''
# <div id="contextual_help">
#  <div class="help_gfx_bubble"><!-- graphically connect field with help text --></div>
#  <div class="help_message"><!-- filled by js --></div>
# </div>
# '''})
    header_entry = {'object_type': 'header', 'text':
                    '%s account request - with certificate login' %
                    configuration.short_title}
    output_objects.append(header_entry)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    user_fields = {'full_name': '', 'organization': '', 'email': '',
                   'state': '', 'country': '', 'password': '',
                   'verifypassword': '', 'comment': ''}
    for field_name in configuration.site_peers_explicit_fields:
        user_fields['peers_%s' % field_name] = ''

    if not os.path.isdir(base_dir) and client_id:

        # Redirect to extcert page with certificate requirement but without
        # changing access method (CGI vs. WSGI).

        extcert_url = requested_page(os.environ).replace('-sid', '-bin')
        extcert_url = os.path.join(os.path.dirname(extcert_url), 'extcert.py')
        extcert_link = {'object_type': 'link', 'destination': extcert_url,
                        'text': 'Sign up with existing certificate (%s)' %
                        client_id}
        output_objects.append(
            {'object_type': 'warning', 'text': """Apparently you already have a
suitable %s certificate that you may sign up with:""" %
             configuration.short_title
             })
        output_objects.append(extcert_link)
        output_objects.append({'object_type': 'warning', 'text': """However, if
you want a dedicated %s certificate you can still request one below:""" %
                               configuration.short_title
                               })
    elif not configuration.ca_fqdn or not configuration.ca_user:
        output_objects.append({'object_type': 'error_text', 'text': """
User certificate requests are not supported on this site!"""})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif client_id:
        for entry in (title_entry, header_entry):
            entry['text'] = entry['text'].replace('request', 'request / renew')
        output_objects.append({'object_type': 'html_form', 'text': '''<p>
Apparently you already have a valid %s certificate, but if it is about to
expire you can renew it by posting the form below. Renewal with changed fields
is <span class="warningtext">not</span> supported, so all fields except maybe your
password must remain unchanged for renew to work. Otherwise it results in a
request for a new account and certificate without access to your old files,
jobs and privileges.</p>''' % configuration.short_title})
        user_fields.update(distinguished_name_to_user(client_id))

    # Override with arg values if set
    for field in user_fields:
        if not field in accepted:
            continue
        override_val = accepted[field][-1].strip()
        if override_val:
            user_fields[field] = override_val
    user_fields = canonical_user(configuration, user_fields,
                                 list(user_fields))

    # Site policy dictates min length greater or equal than password_min_len
    policy_min_len, policy_min_classes = parse_password_policy(configuration)
    user_fields.update({
        'valid_name_chars': '%s (and common accents)' %
        html_escape(valid_name_chars),
        'valid_password_chars': html_escape(valid_password_chars),
        'password_min_len': max(policy_min_len, password_min_len),
        'password_max_len': password_max_len,
        'password_min_classes': max(policy_min_classes, 1),
        'peers_contact_hint': configuration.site_peers_contact_hint,
        'site': configuration.short_title
    })
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'reqcertaction'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
    fill_helpers.update({'site_signup_hint': configuration.site_signup_hint})
    # Write-protect ID and peers helper fields if specifically requested
    peers_fields = ['peers_%s' % field for field in
                    configuration.site_peers_explicit_fields]
    given_peers = [i for i in peers_fields if user_fields.get(i, None)]
    for field in list(cert_field_map) + peers_fields:
        fill_helpers['readonly_%s' % field] = ''
    ro_fields = [i for i in accepted['ro_fields'] if i in
                 list(cert_field_map) + given_peers]
    # Only write-protect ID fields in auto-mode
    if keyword_auto in accepted['ro_fields']:
        ro_fields += [i for i in list(cert_field_map) if not i in ro_fields]
    if reset_token:
        user_fields['reset_token'] = reset_token
        lock_fields = given_peers + ['comment']
        ro_fields += lock_fields
        for hide_field in lock_fields:
            user_fields['show_%s' % hide_field] = 'hidden'
    for field in ro_fields:
        fill_helpers['readonly_%s' % field] = 'readonly'
    fill_helpers.update(user_fields)
    html = """Please enter
your information in at least the <span class=highlight_required>mandatory</span>
fields below and press the Send button to submit the account request to
the %(site)s administrators.

<p class='personal leftpad highlight_message'>
IMPORTANT: we need to identify and notify you about login info, so please use a
working Email address clearly affiliated with your Organization!
</p>

%(site_signup_hint)s

<hr />

    """

    html += account_request_template(configuration,
                                     default_values=fill_helpers)

    # TODO : remove this legacy version?
    html += """
<div style="height: 0; visibility: hidden; display: none;">
<!--OLD FORM-->
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
<tr><td class='optional label'>Optional comment or reason why you should<br />be granted a %(site)s account:</td><td><textarea id='comment_field' rows=4 name=comment title='A free-form comment where you can explain what you need the account for' ></textarea></td><td class=fill_space><br /></td></tr>
<tr><td class='label'><!-- empty area --></td><td><input id='submit_button' type=submit value=Send /></td><td class=fill_space><br /></td></tr>
</table>
</form>
</div>
<hr />
<br />
<div class='warn_message'>Please note that passwords may be recoverable by the %(site)s administrators!</div>
<br />
<!-- Hidden help text -->
<div id='help_text'>
  <div id='full_name_help'>Your full name, restricted to the characters in '%(valid_name_chars)s'</div>
  <div id='organization_help'>Organization name or acronym  matching email</div>
  <div id='email_help'>Email address associated with your organization if at all possible</div>
  <div id='country_help'>Country code of your organization and on the form DE/DK/GB/US/.. , <a href='https://en.wikipedia.org/wiki/ISO_3166-1'>help</a></div>
  <div id='state_help'>Optional 2-letter ANSI state code of your organization, please just leave empty unless it is in the US or similar, <a href='https://en.wikipedia.org/wiki/List_of_U.S._state_abbreviations'>help</a></div>
  <div id='password_help'>Password is restricted to the characters:<br/><tt>%(valid_password_chars)s</tt><br/>Certain other complexity requirements apply for adequate strength. For example it must be %(password_min_len)s to %(password_max_len)s characters long and contain at least %(password_min_classes)d different character classes.</div>
  <div id='verifypassword_help'>Please repeat password</div>
  <div id='comment_help'>Optional, but a short informative comment may help us verify your account needs and thus speed up our response. Typically the name of a local collaboration partner or project may be helpful.</div>
</div>
</div>
"""
    output_objects.append(
        {'object_type': 'html_form', 'text': html % fill_helpers})
    return (output_objects, returnvalues.OK)
