#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# accountreq - helpers for certificate/OpenID account requests
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

"""This module contains various helper contents for the certificate and OpenID
account request handlers"""

from __future__ import absolute_import

import re
import os
import time

# NOTE: the external iso3166 module is optional and only used if available
try:
    import iso3166
except ImportError:
    iso3166 = None

from mig.shared.accountstate import default_account_expire
from mig.shared.base import force_utf8, canonical_user, client_id_dir, \
    distinguished_name_to_user, fill_distinguished_name, fill_user, \
    auth_type_description, mask_creds
from mig.shared.defaults import peers_fields, peers_filename, \
    pending_peers_filename, keyword_auto, user_db_filename, \
    gdp_distinguished_field
from mig.shared.fileio import delete_file, make_temp_file
from mig.shared.notification import notify_user
# Expose some helper variables for functionality backends
from mig.shared.safeinput import name_extras, password_extras, \
    password_min_len, password_max_len, valid_password_chars, \
    valid_name_chars, dn_max_len, html_escape, validated_input, REJECT_UNSET
from mig.shared.serial import load, dump, dumps
from mig.shared.useradm import user_request_reject, user_account_notify, \
    default_search, search_users, create_user, load_user_dict
from mig.shared.userdb import default_db_path
from mig.shared.validstring import valid_email_addresses


def account_css_helpers(configuration):
    """CSS to include in the cert/oid account req page header"""
    css = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.accountform.css" media="screen"/>
    '''
    return css


def account_js_helpers(configuration, fields):
    """Javascript to include in the cert/oid account req page header"""
    # TODO: change remaining names and messages to fit generic auth account?
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<script type="text/javascript" src="/images/js/jquery.accountform.js"></script>
    '''
    add_init = """
  /* Helper to define countries for which State field makes sense */
  var enable_state = ['US', 'CA', 'AU'];
  var peers_mandatory = %(peers_mandatory)s;
  var peers_explicit_fields = %(peers_explicit_fields)s;

  function rtfm_warn(message) {
      return confirm(message + ': Proceed anyway? (If you read and followed the instructions!)');
  }
  function rtfm_error(message) {
      alert(message + ': Please read and follow the instructions!');
  }

  function valid_distinguished_name(value) {
      /* TODO: use regexp test instead? */
      if (value.indexOf('/') == -1 || value.indexOf('=') == -1) {
          return false;
      } else {
          return true;
      }
  }
  function valid_full_name(value) {
      /* TODO: use regexp test instead? */
      /* Just test for space separated strings */
      var parts = value.trim().split(' ');
      if (parts.length < 2) {
          return false;
      } else {
          return true;
      }
  }
  function valid_email(value) {
      /* TODO: use regexp test instead? */
      /* Just test for @ and domain part with dot for now */
      var parts = value.trim().split('@');
      if (parts.length < 2 || parts[1].indexOf('.') < 1) {
          return false;
      } else {
          return true;
      }
  }
  function deprecated_email(value) {
      if (value.search('@gmail.com') != -1 || value.search('@yahoo.com') != -1 || value.search('@hotmail.com') != -1) {
          return true;
      } else {
          return false;
      }
  }

  function check_account_id() {
      //alert('#account_id_help');
      if (!valid_distinguished_name($('#cert_id_field').val())) {
          return rtfm_warn('Account ID does not look like a proper x509 DN');
      }
      return true;
  }
  function check_account_name() {
      //alert('#account_name_help');
      if (!valid_full_name($('#cert_name_field').val())) {
          return rtfm_warn('Full name does not look like a real name');
      }
      return true;
  }
  /* Aliases for extcert */
  function check_cert_id() {
      return check_account_id();
  }
  function check_cert_name() {
      return check_account_name();
  }
  function check_full_name() {
      //alert('#full_name_help');
      if (!valid_full_name($('#full_name_field').val())) {
          return rtfm_warn('Full name does not look like a real name');
      }
      return true;
  }
  function check_email() {
      //alert('#email_help');
      if (!valid_email($('#email_field').val())) {
          return rtfm_warn('Email is invalid');
      }
      if (deprecated_email($('#email_field').val())) {
          return rtfm_warn('Email does not look like an organization address');
      }
      return true;
  }
  function check_organization() {
      //alert('#organization_help');
      if ($('#email_field').val().search('.ku.dk') != -1 || $('#email_field').val().search('diku.dk') != -1 || $('#email_field').val().search('nbi.dk') != -1) {
          if ($('#organization_field').val().indexOf(' ') != -1) {
              return rtfm_warn('Organization does not look like an acronym');
          }
      }
      return true;
  }
  function check_country() {
      //alert('#country_help');
      if ($('#country_field').val().length !== 2) {
          return rtfm_warn('Valid ISO 3166 country code must be provided');
      }
      return true;
  }
  function check_state() {
      //alert('#state_help');
      if (enable_state.indexOf($('#country_field').val()) == -1) {
          if ($('#state_field').val() && $('#state_field').val() != 'NA') {
              return rtfm_warn('State only makes sense for '+enable_state.join(', ')+' users');
          }
      }
      return true;
  }
  function check_password() {
      //alert('#password_help');
      if ($('#password_field').val().length < %(password_min_len)d) {
         return rtfm_warn('Password too short');
      } else if ($('#password_field').val().length > %(password_max_len)d) {
         return rtfm_warn('Password too long');
      }
      return true;
  }
  function check_verifypassword() {
      //alert('#verifypassword_help');
      if ($('#verifypassword_field').val().length < %(password_min_len)d) {
         return rtfm_warn('Verify password too short');
      } else if ($('#verifypassword_field').val().length > %(password_max_len)d) {
         return rtfm_warn('Verify password too long');
      } else if ($('#password_field').val() != $('#verifypassword_field').val()) {
         return rtfm_warn('Mismatch between password and verify password');
      }
      return true;
  }
  function check_peers_full_name() {
      //alert('#peers_full_name_help');
      if (!peers_mandatory || !(peers_explicit_fields.includes('full_name'))) {
          return true;
      }
      var base_err = 'One or more peers contact full names must be provided';
      /* NOTE: split on comma and verbatim 'and' with space removal */
      var all_parts = $('#peers_full_name_field').val().trim().split(/\s*,\s*|\s+and\s+/);
      if (all_parts.length < 1) {
          rtfm_error(base_err);
          return false;
      }
      for (var i = 0; i < all_parts.length; i++) {
          if (!valid_full_name(all_parts[i])) {
              rtfm_error('Peers full name is invalid: '+ \
                         all_parts[i] + '\\n' + base_err);
              return false;
          }
      }
      return true;
  }
  function check_peers_email() {
      //alert('#peers_email_help');
      /* if (!peers_mandatory || !(peers_explicit_fields.includes('email'))) {*/
      if (!peers_mandatory) {
          return true;
      }
      var base_err = 'One or more peers contact emails must be provided';
      /* NOTE: split on comma and verbatim 'and' with space removal */
      var all_parts = $('#peers_email_field').val().trim().split(/\s*,\s*|\s+and\s+/);
      if (all_parts.length < 1) {
          rtfm_error(base_err);
          return false;
      }
      for (var i = 0; i < all_parts.length; i++) {
          if (!valid_email(all_parts[i])) {
              /* Bail if peers email on invalid format */
              rtfm_error('Peer contact email is invalid: '+ \
                         all_parts[i] + '\\n' + base_err);
              return false;
          } else if (all_parts[i].trim().toLowerCase() === $('#email_field').val().trim().toLowerCase()) {
              rtfm_error(
                  'Peer contact email cannot be your own, '+all_parts[i]);
              $('#peers_email_field')[0].setCustomValidity(base_err);
              return false;
          }
      }
      return true;
  }
  function check_comment() {
      /* NOTE: HTML5 and  bootstrap ignore validation of textarea patterns.
         We can use setCustomValidity, which is native javascript funtion.
         https://stackoverflow.com/questions/30958536/custom-validity-jquery
         Set it to something to mark invalid and to empty string to mark valid.
      */
      //alert('#comment_help');
      var invalid_msg = 'Comment must justify your account needs. '+hint;
      /* Comment only needed if peers are mandatory and not explicitly given */
      if (!peers_mandatory || peers_explicit_fields.length > 0) {
          $('#comment_field')[0].setCustomValidity('');
          return true;
      }
      var comment = $('#comment_field').val();
      if (!comment) {
          /* Comment is mandatory in this case */
          $('#comment_field')[0].setCustomValidity(invalid_msg);
          return false;
      }
      /* Comment must contain purpose and contact email.
         Fuzzy match using pattern definition from textarea.
         */
      var pattern = $('#comment_field').attr('pattern');
      var hint = $('#comment_field').attr('placeholder');
      var patternRegex;
      if(typeof pattern !== typeof undefined && pattern !== false) {
          /* Anchored multiline match */
          var patternRegex = new RegExp('^' + pattern.replace(/^\^|\$$/g, '') + '$', 'gm');
      }
      if (patternRegex && !comment.match(patternRegex)) {
          /* Warn about comment on invalid format */
          rtfm_error('Comment must justify your account needs. '+hint);
          $('#comment_field')[0].setCustomValidity(invalid_msg);
          return false;
      }
      $('#comment_field')[0].setCustomValidity('');
      return true;
  }

  function toggle_state() {
      var country = $('#country_field').val();
      if (country && enable_state.indexOf(country) > -1) {
          $('#state_field').prop('readonly', false);
      } else {
          $('#state_field').prop('readonly', true);
          /* NOTE: reset state on change to other country */
          $('#state_field').val('');
      }
  }

  function init_context_help() {
      /* move help text just right of connecting gfx bubble */
      var contextualHelpMessage = $('#contextual_help').find('.help_message');
      contextualHelpMessage.offset({top: -30})
      contextualHelpMessage.offset({left: 40})
  }
  function close_context_help() {
      //alert('close called');
      $('#contextual_help').hide();
      $('#contextual_help').css({top: '', left: ''}); // fix for 'drifting' on IE/Chrome
  }
  function bind_help(input_element, message) {
      input_element.focus(function () {
          close_context_help();
          var contextualHelp = $('#contextual_help');
          var contextualHelpMessage = $('#contextual_help').find('.help_message');
          contextualHelpMessage.html(message);
          var inputOffset = $(this).offset(); // top, left
          var scrollTop = $(window).scrollTop(); // how much should we offset if the user has scrolled down the page?
          contextualHelp.offset({
              //top: (inputOffset.top + scrollTop + .5 * $(this).height()) - .5 * contextualHelp.height(),
              top: inputOffset.top + scrollTop,
              //left: (inputOffset.left + .5 * $(this).width()) - .5 * contextualHelp.width()
              left: inputOffset.left + $(this).width() + 20
              //left: inputOffset.left + 20
          });
          contextualHelp.show();
      });
  }
""" % {'password_min_len': password_min_len,
       'password_max_len': password_max_len,
       'peers_mandatory': ("%s" % configuration.site_peers_mandatory).lower(),
       'peers_explicit_fields': "%s" % configuration.site_peers_explicit_fields,
       }
    add_init += """
  function validate_form() {
      //alert('validate form');
"""
    # NOTE: dynamically add checks for all explicit peers fields configured
    checks = [] + fields
    for field_name in configuration.site_peers_explicit_fields:
        checks.append("peers_%s" % field_name)
    add_init += """
      var status = %s""" % ' && '.join(['check_%s()' % name for name in checks])
    add_init += """
      //alert('old validate form: ' +status);
      return status;
  }

"""
    add_ready = """
      init_context_help();

"""
    # TODO: add help for peers fields here?
    for name in fields:
        add_ready += """
      bind_help($('#%s_field'), $('#%s_help').html());
""" % (name, name)
    return (add_import, add_init, add_ready)


def account_request_template(configuration, password=True, default_values={}):
    """A general form template used for various account requests"""

    # Require user to explicitly accept terms of use unless overriden
    default_values['accepted_terms'] = default_values.get('accepted_terms', '')
    if default_values['accepted_terms'].lower() in ('checked', 'true', 'yes'):
        default_values['accepted_terms'] = 'checked'
    # Hide certain fields if used from password reset
    for show_field in ('show_comment', 'show_peers_full_name',
                       'show_peers_email'):
        default_values[show_field] = default_values.get(show_field, '')

    html = """
<div id='account-request-grid' class='form_container'>

<!-- use post here to avoid field contents in URL -->
<form method='%(form_method)s' action='%(target_op)s.py' onSubmit='return validate_form();' class='needs-validation' novalidate>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
"""
    # A few cert backends require cert_id as well
    cert_id = default_values.get('cert_id', '')
    if cert_id:
        html += """
<input type='hidden' name='cert_id' value='%(cert_id)s' />
"""
    # Password reset requests include a reset token to forward
    reset_token = default_values.get('reset_token', '')
    if reset_token:
        html += """
<input type='hidden' name='reset_token' value='%(reset_token)s' />
"""

    html += """
<div class='form-row'>
    <div class='col-md-4 mb-3 form-cell'>
      <label for='validationCustom01'>Full name</label>
      <input type='text' class='form-control' id='full_name_field' type=text name='cert_name' value='%(full_name)s' placeholder='Firstname Middlenames Lastname' required pattern='[^ ]+([ ][^ ]+)+' %(readonly_full_name)s title='Your full name, i.e. two or more names separated by space' />
      <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        Please enter your full name.
      </div>
    </div>
    <div class='col-md-4 mb-3 form-cell'>
      <label for='validationCustom02'>Email address</label>
      <input class='form-control' id='email_field' type=email name='email' value='%(email)s' placeholder='username@organization.org' required %(readonly_email)s title='Email address should match your organization - and you need to read mail sent there' />
      <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        Please enter your email address matching your organization/company.
      </div>
    </div>
    <div class='col-md-4 mb-3 form-cell'>
      <label for='validationCustom01'>Organization</label>
      <input class='form-control' id='organization_field' type=text name='org' value='%(organization)s' placeholder='Organization or company' required pattern='[^ ]+([ ][^ ]+)*' %(readonly_organization)s title='Name of your organization or company: one or more words or abbreviations separated by space' />
      <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        Please enter the name of your organization or company.
      </div>
    </div>
  </div>
  <div class='form-row two-entries'>
    <div class='col-md-8 mb-3 form-cell'>
      <label for='validationCustom03'>Country</label>
    """
    # Generate drop-down of countries and codes if available, else simple input
    sorted_countries = list_country_codes(configuration)
    if sorted_countries and not default_values.get('readonly_country', ''):
        html += """
        <select class='form-control themed-select html-select' id='country_field' name='country' minlength=2 maxlength=2 value='%(country)s' placeholder='Two letter country-code' required pattern='[A-Z]{2}' title='Please select your country from the list' onChange='toggle_state();'>
"""
        # TODO: detect country based on browser info?
        # Start out without a country selection
        for (name, code) in [('', '')] + sorted_countries:
            selected = ''
            if default_values.get('country', '') == code:
                selected = 'selected'
            html += "        <option value='%s' %s>%s</option>\n" % \
                    (code, selected, name)
        html += """
        </select>
    """
    else:
        html += """
        <input class='form-control' id='country_field' type=text name='country' value='%(country)s' placeholder='Two letter country-code' required pattern='[A-Z]{2}' %(readonly_country)s minlength=2 maxlength=2 title='The two capital letters used to abbreviate your country' onBlur='toggle_state();' />
        """

    html += """
        <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        Please select your country or provide your two letter country-code in line with
        https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2.
      </div>
    </div>
    <div class='col-md-4 mb-3 form-cell'>
      <label for='validationCustom04'>Optional state code</label>
      <input class='form-control' id='state_field' type=text name='state' value='%(state)s' placeholder='NA' pattern='([A-Z]{2})?' %(readonly_state)s maxlength=2 title='Mainly for U.S. users - please just leave empty if in doubt' readonly>
    </div>
  </div>
    """

    if password:
        html += """
  <div class='form-row two-entries'>
    <div class='col-md-6 mb-3 form-cell'>
      <label for='validationCustom01'>Password</label>
      <input type='password' class='form-control' id='password_field' type=password name='password' minlength=%(password_min_len)d maxlength=%(password_max_len)d value='%(password)s' placeholder='Your password' required pattern='.{%(password_min_len)d,%(password_max_len)d}' title='Password of your choice - site policies about password strength apply and will give you feedback below if refused' />
      <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        Please provide a valid and sufficiently strong password.<br/>
        I.e. %(password_min_len)d to %(password_max_len)d characters from at least %(password_min_classes)d of the 4 different character classes: lowercase, uppercase, digits, other.
      </div>
    </div>
    <div class='col-md-6 mb-3 form-cell'>
      <label for='validationCustom03'>Verify password</label>
      <input type='password' class='form-control' id='verifypassword_field' type=password name='verifypassword' minlength=%(password_min_len)d maxlength=%(password_max_len)d value='%(verifypassword)s' placeholder='Repeat password' required pattern='.{%(password_min_len)d,%(password_max_len)d}' title='Repeat your chosen password to rule out most simple typing errors' />
      <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        Please repeat your chosen password to verify.
      </div>
    </div>
  </div>
        """

    email_text_pattern = '.*[^ ]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+.*'
    if configuration.site_peers_explicit_fields:
        # NOTE: dedicated peers field(s) instead of legacy Comment use
        comment_add = ''
        comment_required = ''
        comment_pattern = ''
    elif configuration.site_peers_mandatory:
        comment_add = ' AND the name + email of your peer contact(s) %(peers_contact_hint)s'
        comment_required = 'required'
        comment_pattern = email_text_pattern
    elif configuration.site_enable_peers:
        # NOTE: no peers field(s) instead of legacy Comment use
        comment_add = ' and the name + email of any peer contact(s) %(peers_contact_hint)s'
        comment_required = 'required'
        comment_pattern = ''
    else:
        # NOTE: peers disabled
        comment_add = ''
        comment_required = ''
        comment_pattern = ''

    if 'full_name' in configuration.site_peers_explicit_fields:
        html += """
  <div class='form-row single-entry %(show_peers_full_name)s'>
    <div class='col-md-12 mb-3 form-cell'>
      <!-- NOTE: this simple form control just looks for one or more full names.
      -->
      <label for='validationCustom11'>Peer contact full name(s)</label>
      <input type='text' class='form-control' id='peers_full_name_field' type=text name='peers_full_name' value='%(peers_full_name)s' placeholder='Contact1 Name, Contact2 Name, ... %(peers_contact_hint)s' required %(readonly_peers_full_name)s pattern='(\D\D+(\s+\D+)+)(\s*(,| & | and )\s*(\D\D+(\s+\D+)+))*' title='One or more full names of your %(site)s peer contacts %(peers_contact_hint)s' />
      <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        Please enter the full name of your peer contact(s) %(peers_contact_hint)s.
      </div>
    </div>
  </div>
        """
    if 'email' in configuration.site_peers_explicit_fields:
        html += """
  <div class='form-row single-entry %(show_peers_email)s'>
    <div class='col-md-12 mb-3 form-cell'>
      <!-- NOTE: this simple form control just looks for one or more emails.
           Using 'multiple' renders 'required' useless so we set minlength.
      -->
      <label for='validationCustom12'>Peer contact email(s)</label>
      <input type='text' class='form-control' id='peers_email_field' type=email name='peers_email' value='%(peers_email)s' placeholder='contact1@email.org, contact2@email.org, ... %(peers_contact_hint)s' multiple minlength=5 required %(readonly_peers_email)s pattern='^([^@\s]+@[^@\s]+(\.[^@\s]+)+)(\s*,?\s*([^@\s]+@[^@\s]+(\.[^@\s]+)+))*$' title='One or more email address of your %(site)s peer contacts %(peers_contact_hint)s' />
      <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        Please enter the email of your peer contact(s) %(peers_contact_hint)s.
      </div>
    </div>
  </div>
        """

    html += """
  <div class='form-row single-entry %(show_comment)s'>
    <div class='col-md-12 mb-3 form-cell'>
      <!-- IMPORTANT: textarea does not generally support the pattern attribute
                      so for HTML5 validation we have to mimic it with explicit
                      javascript checking.
      -->
      <label for='validationCustom03'>Comment with reason why you should be granted a %(site)s account:</label>
      <textarea class='form-control' id='comment_field' rows=4 name='comment' placeholder='Typically which collaboration, project or course you need the account for__COMMENT_ADD__' __COMMENT_REQUIRED__ pattern='__COMMENT_PATTERN__' title='A free-form comment to justify your account needs'>%(comment)s</textarea>
      <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        Please mention collaboration, project or course you need the account for__COMMENT_ADD__.
      </div>
    </div>
  </div>
  <div class='form-group'>
    <div class='form-check'>
      <span class='switch-label'>I accept the %(site)s <a href='/public/terms.html' target='_blank'>terms and conditions</a></span>
      <label class='form-check-label switch' for='acceptTerms'>
      <input class='form-check-input' type='checkbox' name='accept_terms' id='acceptTerms' required>
      <span class='slider round small' title='Required to get an account'></span>
      <br/>
      <div class='valid-feedback'>
        Looks good!
      </div>
      <div class='invalid-feedback'>
        You <em>must</em> agree to terms and conditions before sending.
      </div>
      </label>
    </div>
  </div>
  <div class='vertical-spacer'></div>
  <input id='submit_button' type=submit value=Send />
</form>

</div>
""".replace('__COMMENT_ADD__', comment_add).replace('__COMMENT_REQUIRED__', comment_required).replace('__COMMENT_PATTERN__', comment_pattern)
    return html


def account_pw_reset_template(configuration, default_values={}):
    """A general form template used for various password reset requests"""

    html = """
<div id='account-pw-reset-grid' class='form_container'>
"""

    _logger = configuration.logger
    auth_map = auth_type_description(configuration)
    show_auth_types = [(key, auth_map[key]) for key in
                       default_values.get('show', auth_map.keys())]
    filtered_auth_types = [i for i in show_auth_types if i[0] in
                           configuration.site_signup_methods]
    _logger.debug("show_auth_types %s filtered_auth_types %s" %
                  (show_auth_types, filtered_auth_types))
    if not filtered_auth_types:
        html += """<p class='warningtext'>
No matching local authentication methods enabled on this site, so no passwords
to reset here. In case you rely on a central or external identity provider you
can probably also change your password with the corresponding ID provider.
</p>
"""
    else:
        html += """
<p>
Please enter the full ID or email address for your %(short_title)s account
and select which authentication method you want to change password for.
</p>
<!-- use post here to avoid field contents in URL -->
<form method='%(form_method)s' action='%(target_op)s.py'>
    <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
    <!-- NOTE: cert_id field to allow either full DN or email -->
    <input type='text' name='cert_id' required />
    <select class='form-control themed-select html-select' id='reset_auth_type'
        name='auth_type' minlength=3 maxlength=4
        placeholder='The kind of authentication for which to reset password'
        required pattern='[a-z]{3,4}' title='Please select type from the list'>
"""
        for (auth_type, name) in filtered_auth_types:
            selected = ''
            if default_values.get('auth_type', '') == auth_type:
                selected = 'selected'
            html += "        <option value='%s' %s>%s</option>\n" % \
                    (auth_type, selected, name)
        html += """
    </select>
    <input id='submit_button' type=submit value='Request Password Reset'/>
</form>
"""

    html += """
</div>
"""
    return html


def build_accountreqitem_object(configuration, accountreq_dict):
    """Build a accountreq object based on input accountreq_dict"""

    created_epoch = accountreq_dict['created']
    created_asctime = time.ctime(created_epoch)
    accountreq_obj = {
        'object_type': 'accountreq',
        'auth': accountreq_dict.get('auth', ['unknown']),
        'id': accountreq_dict['id'],
        'full_name': accountreq_dict['full_name'],
        'email': accountreq_dict['email'],
        'organization': accountreq_dict['organization'],
        'country': accountreq_dict['country'],
        'state': accountreq_dict['state'],
        'comment': accountreq_dict['comment'],
        'created': "<div class='sortkey'>%d</div>%s" % (created_epoch,
                                                        created_asctime),
    }
    if configuration.site_enable_peers:
        for name in configuration.site_peers_explicit_fields:
            field = 'peers_%s' % name
            accountreq_obj[field] = accountreq_dict.get(field, '')
    return accountreq_obj


def list_account_reqs(configuration):
    """Find all pending certificate/OpenID accounts requests"""
    logger = configuration.logger
    accountreq_list = []
    dir_content = []

    try:
        dir_content = os.listdir(configuration.user_pending)
    except Exception:
        if not os.path.isdir(configuration.user_pending):
            try:
                os.mkdir(configuration.user_pending)
            except Exception as err:
                logger.error(
                    'accountreq.py: not able to create directory %s: %s' %
                    (configuration.accountreq_home, err))
                return (False, "account request setup is broken")
            dir_content = []

    for entry in dir_content:

        # Skip dot files/dirs

        if entry.startswith('.'):
            continue
        if is_account_req(entry, configuration):
            accountreq_list.append(entry)
        else:
            logger.warning(
                '%s in %s is not a file, move it?'
                % (entry, configuration.user_pending))
    return (True, accountreq_list)


def is_account_req(req_id, configuration):
    """Check that req_id is an existing account request"""
    req_path = os.path.join(configuration.user_pending, req_id)
    if os.path.isfile(req_path):
        return True
    else:
        return False


def get_account_req(req_id, configuration):
    """Helper to fetch dictionary for a pending account request"""
    req_path = os.path.join(configuration.user_pending, req_id)
    req_dict = load(req_path)
    if not req_dict:
        return (False, 'Could not open account request %s' % req_id)
    else:
        req_dict['id'] = req_id
        req_dict['created'] = os.path.getctime(req_path)
        return (True, req_dict)


def accept_account_req(req_id, configuration, peer_id, user_copy=True,
                       admin_copy=True, auth_type='oid', default_renew=False):
    """Helper to accept a pending account request"""
    _logger = configuration.logger
    _logger.info('accept account %s with peer %s' % (req_id, peer_id))
    # NOTE: conf_path accepts configuration object
    conf_path = configuration
    db_path = default_db_path(configuration)
    req_path = os.path.join(configuration.user_pending, req_id)
    expire = None
    user_id = None
    user_dict = {}
    override_fields = {}

    if expire is None:
        expire = default_account_expire(configuration, auth_type)

    if peer_id:
        override_fields['peer_pattern'] = peer_id
        override_fields['status'] = 'temporal'

    try:
        req_dict = load(req_path)
    except Exception as err:
        err_msg = 'peer account request %s extraction failed: %s' % \
                  (req_id, err)
        _logger.error(err_msg)
        return (False, err_msg)
    # IMPORTANT: do NOT log credentials
    _logger.debug('accept request: %s' % mask_creds(req_dict))
    if 'distinguished_name' not in req_dict:
        fill_distinguished_name(req_dict)
    fill_user(req_dict)
    user_id = req_dict['distinguished_name']

    user_dict.update(req_dict)
    operation_type = 'create'
    saved = load_user_dict(_logger, user_id, db_path, False)
    if saved:
        _logger.info('updating existing user in user db: %s' % user_id)
        operation_type = 'update'
        # NOTE: don't update with saved here as it truncates request values.
        #       It will be properly handled in the create_user call below.

    # Make sure account expire is set with local certificate or OpenID login

    if 'expire' not in user_dict:
        override_fields['expire'] = expire

    # Now all user fields are set and we can create and notify the user
    # NOTE: let non-ID command line values override loaded values
    for (key, val) in list(override_fields.items()):
        user_dict[key] = val

    _logger.info('%s %s in user database and in file system' %
                 (operation_type.title(), user_dict['distinguished_name']))
    try:
        create_user(user_dict, conf_path, db_path, False, False, False,
                    default_renew, verify_peer=peer_id)
    except Exception as exc:
        err_msg = "%s user %s failed: %s" % (operation_type.title(),
                                             user_dict['distinguished_name'],
                                             exc)
        _logger.error(err_msg)
        return (False, err_msg)

    _logger.info('%sd %s in user database and in file system' %
                 (operation_type.title(), user_dict['distinguished_name']))

    if user_copy or admin_copy:
        extra_copies = []
        # Default to inform mail used in request
        raw_targets = {}
        raw_targets['email'] = raw_targets.get('email', [])
        if user_copy:
            raw_targets['email'].append(keyword_auto)

        (_, username, full_name, addresses, errors) = user_account_notify(
            user_id, raw_targets, conf_path, db_path, False, admin_copy,
            extra_copies)
        if errors:
            _logger.warning("account intro address lookup errors for %s: %s" %
                            (user_id, '\n'.join(errors)))

        if not addresses:
            _logger.warning("no email targets for %s account intro" % user_id)
        else:
            _logger.debug('send account intro to %s' % addresses)
            notify_dict = {'JOB_ID': 'NOJOBID',
                           'USER_CERT': user_id, 'NOTIFY': []}
            for (proto, address_list) in addresses.items():
                for address in address_list:
                    notify_dict['NOTIFY'].append('%s: %s' % (proto, address))

            _logger.info("send account intro for '%s' to:\n%s" %
                         (user_id, '\n'.join(notify_dict['NOTIFY'])))
            (send_status, send_errors) = notify_user(
                notify_dict, [user_id, username, full_name], 'ACCOUNTINTRO',
                _logger, '', configuration)
            if send_status:
                _logger.debug("sent account intro for '%s' to:\n%s" %
                              (user_id, '\n'.join(notify_dict['NOTIFY'])))
            else:
                _logger.warning('send account intro failed for recipient(s): %s'
                                % '\n'.join(send_errors))
    else:
        _logger.error('one or more account intro messages failed for %s' %
                      req_path)

    if not delete_file(req_path, _logger):
        err_msg = 'failed to clean up request %s after user %s' % \
                  (req_path, operation_type)
        _logger.errors(err_msg)
        return (False, err_msg)
    return (True, '')


def peer_account_req(req_id, configuration, target_id, user_copy=False,
                     admin_copy=True, auth_type='oid'):
    """Helper to request peer accept for a pending account request"""
    # TODO: enable user_copy if it can be clearly marked only CC?
    _logger = configuration.logger
    _logger.info('request account peer for %s with peer %s' %
                 (req_id, target_id))
    # NOTE: conf_path accepts configuration object
    conf_path = configuration
    db_path = default_db_path(configuration)
    req_path = os.path.join(configuration.user_pending, req_id)
    regex_keys = []
    search_filter = default_search()
    # IMPORTANT: Default to nobody to avoid spam if called without target_id
    search_filter['distinguished_name'] = ''
    try:
        req_dict = load(req_path)
    except Exception as err:
        err_msg = 'peer account request %s extraction failed: %s' % \
            (req_id, err)
        _logger.error(err_msg)
        return (False, err_msg)
    # IMPORTANT: do NOT log credentials
    _logger.debug('peer account request: %s' % mask_creds(req_dict))
    if 'distinguished_name' not in req_dict:
        fill_distinguished_name(req_dict)
    fill_user(req_dict)
    peer_id = req_dict['distinguished_name']
    if target_id == keyword_auto:
        if 'email' in configuration.site_peers_explicit_fields:
            # Try peers_email with fallback to comment
            target_str = req_dict.get('peers_email', req_dict['comment'])
        else:
            target_str = req_dict['comment']
    else:
        target_str = target_id
    peer_emails = valid_email_addresses(configuration, target_str)
    if peer_emails[1:]:
        regex_keys.append('email')
        search_filter['email'] = '(' + '|'.join(peer_emails) + ')'
    elif peer_emails:
        search_filter['email'] = peer_emails[0]
    elif search_filter['distinguished_name']:
        search_filter['email'] = '*'
    else:
        search_filter['email'] = ''

    # If email is provided or detected DN may be almost anything
    if search_filter['email'] and not search_filter['distinguished_name']:
        search_filter['distinguished_name'] = '*emailAddress=*'

    # Use email from user DB by default
    raw_targets = {}
    raw_targets['email'] = [keyword_auto]

    extra_copies = []
    if user_copy and req_dict.get('email', ''):
        extra_copies.append(req_dict['email'])

    _logger.debug('handling peer %s request to users matching %s' %
                  (peer_id, search_filter))

    # Lookup users to request formal acceptance from
    (_, hits) = search_users(search_filter, conf_path,
                             db_path, False, regex_match=regex_keys)
    gdp_prefix = "%s=" % gdp_distinguished_field
    if len(hits) < 1:
        # IMPORTANT: do NOT log credentials
        _logger.error("no target users to request peer acceptance from: %s" %
                      mask_creds(req_dict))
        return (False, "no valid target peer acceptance users")
    elif len(hits) > 3:
        # IMPORTANT: do NOT log credentials
        _logger.error("refuse to request peer acceptance from %d users for %s"
                      % (len(hits), mask_creds(req_dict)))
        return (False, "too many requested peer acceptance users")
    else:
        _logger.debug("request peer acceptance from users: %s" %
                      '\n'.join([i[0] for i in hits]))

    notify_count, all_sent, all_errors = 0, True, []
    for (user_id, user_dict) in hits:
        _logger.debug('request peer - check for %s' % user_id)
        if configuration.site_enable_gdp and \
                user_id.split('/')[-1].startswith(gdp_prefix):
            _logger.debug("skip peer request for GDP project account: %s" %
                          user_id)
            continue
        if peer_id == user_id:
            _logger.warning("skip peer request for self: %s" % user_id)
            continue
        if not peers_permit_allowed(configuration, user_dict):
            _logger.warning("skip peer request for %s without permission" %
                            user_id)
            continue
        if not manage_pending_peers(configuration, user_id, "add",
                                    [(peer_id, req_dict)]):
            _logger.error("Failed to forward accept peer %s to %s" %
                          (peer_id, user_id))
            continue

        _logger.info("added peer request from %s to %s" % (peer_id, user_id))

        (_, _, full_name, addresses, errors) = user_account_notify(
            user_id, raw_targets, conf_path, db_path, False, admin_copy,
            extra_copies)
        if errors:
            _logger.warning("peer accept address lookup errors for %s: %s" %
                            (user_id, '\n'.join(errors)))
            continue

        notify_dict = {'JOB_ID': 'NOJOBID', 'USER_CERT': user_id, 'NOTIFY': []}
        for (proto, address_list) in addresses.items():
            for address in address_list:
                notify_dict['NOTIFY'].append('%s: %s' % (proto, address))

        # Don't actually send unless requested
        if not raw_targets and not admin_copy:
            _logger.warning("no targets for request accept peer %s from %s" %
                            (peer_id, user_id))
            continue
        _logger.info("send request accept peer message for '%s' to:\n%s"
                     % (peer_id, '\n'.join(notify_dict['NOTIFY'])))
        notify_count += 1
        peers_details = ''
        for peers_field in configuration.site_peers_explicit_fields:
            field_name = 'peers_%s' % peers_field
            peers_details += """Peers contact %s(s): %s
""" % (peers_field.replace('_', ' '), req_dict.get(field_name, ''))
        peers_details += """Comment: %(comment)s
""" % req_dict
        (send_status, send_errors) = notify_user(
            notify_dict, [peer_id, configuration.short_title, 'peeraccount',
                          peers_details, req_dict['email'], user_id],
            'SENDREQUEST', _logger, '', configuration)

        if send_status:
            _logger.debug("sent accept peer request for '%s' to:\n%s" %
                          (user_id, req_dict['email']))
        else:
            _logger.warning('notify failed for peer request recipient(s): %s' %
                            '\n'.join(send_errors))
            all_sent = False
            all_errors += send_errors

    if notify_count < 1:
        err_msg = 'no valid actual peers found for %s' % req_path
        _logger.warning(err_msg)
        return (False, err_msg)
    elif all_sent:
        _logger.info('sent %d accept peer requests for %s' % (notify_count,
                                                              req_path))
        return (True, '')
    else:
        err_msg = 'one or more accept peer requests failed for %s' % \
                  req_path
        _logger.warning(err_msg)
        return (False, err_msg)


def reject_account_req(req_id, configuration, reject_reason,
                       user_copy=True, admin_copy=True, auth_type='oid'):
    """Helper to reject a pending account request"""
    _logger = configuration.logger
    _logger.info('reject account request %s with msg %s' %
                 (req_id, reject_reason))
    # NOTE: conf_path accepts configuration object
    conf_path = configuration
    db_path = default_db_path(configuration)
    req_path = os.path.join(configuration.user_pending, req_id)
    try:
        req_dict = load(req_path)
    except Exception as err:
        err_msg = 'peer account request %s extraction failed: %s' % \
                  (req_id, err)
        _logger.error(err_msg)
        return (False, err_msg)
    # IMPORTANT: do NOT log credentials
    _logger.debug('reject request: %s' % mask_creds(req_dict))
    if 'distinguished_name' not in req_dict:
        fill_distinguished_name(req_dict)
    fill_user(req_dict)
    user_id = req_dict['distinguished_name']
    # Default to inform mail used in request
    raw_targets = {}
    raw_targets['email'] = raw_targets.get('email', [])
    if user_copy:
        raw_targets['email'].append(req_dict.get('email', keyword_auto))
    if reject_reason == keyword_auto:
        msg = "invalid or missing mandatory info"
    else:
        msg = reject_reason
    # Now all user fields are set and we can reject and warn the user
    (configuration, addresses, errors) = \
        user_request_reject(user_id, raw_targets, conf_path,
                            db_path, False, admin_copy)
    if errors:
        err_msg = "reject request address lookup errors: %s" % \
                  '\n'.join(errors)
        _logger.error(err_msg)
        return (False, err_msg)
    if not addresses:
        err_msg = "reject request found no suitable addresses"
        _logger.error(err_msg)
        return (False, err_msg)
    _logger.debug('reject request notify: %s' % addresses)
    notify_dict = {'JOB_ID': 'NOJOBID', 'USER_CERT': user_id, 'NOTIFY': []}
    all_sent, all_errors = True, []
    for (proto, address_list) in addresses.items():
        for address in address_list:
            notify_dict['NOTIFY'].append('%s: %s' % (proto, address))
            _logger.info("send reject account request for '%s' to:\n%s" %
                         (user_id, '\n'.join(notify_dict['NOTIFY'])))
            (send_status, send_errors) = notify_user(notify_dict,
                                                     [user_id, req_dict,
                                                      auth_type, msg],
                                                     'ACCOUNTREQUESTREJECT',
                                                     _logger, '',
                                                     configuration)
            if send_status:
                _logger.debug("sent reject account request for '%s' to:\n%s" %
                              (user_id, '\n'.join(notify_dict['NOTIFY'])))
            else:
                _logger.warning('notify failed for reject recipient(s): %s' %
                                '\n'.join(send_errors))
                all_sent = False
                all_errors += send_errors

    if all_sent:
        _logger.info('reject request cleaning up tmp file: %s' % req_path)
        if not delete_file(req_path, _logger):
            err_msg = 'failed to clean up request %s' % req_path
            _logger.error(err_msg)
            return (False, err_msg)
        return (True, '')
    else:
        err_msg = 'one or more reject messages failed - keeping %s' % \
                  req_path
        _logger.warning(err_msg)
        return (False, err_msg)


def existing_country_code(country_code, configuration):
    """Check that country_code matches an existing code in line with ISO3166"""

    logger = configuration.logger
    if iso3166 is None:
        logger.info("iso3166 module not available - accept all countries")
        return True
    try:
        country = iso3166.countries.get(country_code)
        logger.debug("found country %s for code %s" % (country, country_code))
        # Country object has 2-letter code in alpha2 attribute
        return (country and country.alpha2 == country_code)
    except KeyError:
        logger.warning("no country found for code %s" % country_code)
        return False


def list_country_codes(configuration):
    """Get a sorted list of available countries and their 2-letter ISO3166
    country code for use in country selection during account sign up.
    """
    logger = configuration.logger
    if iso3166 is None:
        logger.info("iso3166 module not available - manual country code entry")
        return False
    country_list = []
    for entry in iso3166.countries:
        name, code = force_utf8(entry.name), force_utf8(entry.alpha2)
        # logger.debug("found country %s for code %s" % (name, code))
        country_list.append((name, code))
    return country_list


def forced_org_email_match(org, email, configuration):
    """Check that email and organization follow the required policy"""

    logger = configuration.logger
    # Policy regexps: prioritized order with most general last
    force_org_email = [('DIKU', ['^[a-zA-Z0-9_.+-]+@diku.dk$',
                                 '^[a-zA-Z0-9_.+-]+@di.ku.dk$']),
                       ('NBI', ['^[a-zA-Z0-9_.+-]+@nbi.ku.dk$',
                                '^[a-zA-Z0-9_.+-]+@nbi.dk$',
                                '^[a-zA-Z0-9_.+-]+@fys.ku.dk$']),
                       ('IMF', ['^[a-zA-Z0-9_.+-]+@math.ku.dk$']),
                       # Keep this KU catch-all last and do not generalize it!
                       ('KU', ['^[a-zA-Z0-9_.+-]+@(alumni.|)ku.dk$']),
                       ]
    force_org_email_dict = dict(force_org_email)
    is_forced_email = False
    is_forced_org = False
    if org.upper() in force_org_email_dict:
        is_forced_org = True
        # Consistent casing
        org = org.upper()
    email_hit = '__BOGUS__'
    for (forced_org, forced_email_list) in force_org_email:
        for forced_email in forced_email_list:
            # Consistent casing
            if re.match(forced_email, email.lower()):
                is_forced_email = True
                email_hit = forced_email
                logger.debug('email match on %s vs %s' % (email, forced_email))
                break

        # Use first hit to avoid catch-all overriding specific hits
        if is_forced_email or is_forced_org and org == forced_org:
            break
    if is_forced_org != is_forced_email or \
            not email_hit in force_org_email_dict.get(org, ['__BOGUS__']):
        logger.error('Illegal email and organization combination: %s' %
                     ([email, org, is_forced_org, is_forced_email,
                       email_hit, force_org_email_dict.get(org,
                                                           ['__BOGUS__'])]))
        return False
    else:
        return True


def save_account_request(configuration, req_dict):
    """Save req_dict account request as pickle in configured user_pending
    location.
    Returns a tuple of save status and output, where the latter is the request
    path on success or the error message otherwise. 
    """
    req_path = None
    try:
        # NOTE: mkstemp opens in binary mode and dumps forces req to utf8
        (os_fd, req_path) = make_temp_file(dir=configuration.user_pending)
        os.write(os_fd, dumps(req_dict))
        os.close(os_fd)
    except Exception as err:
        return (False, "save account req failed: %s" % err)
    return (True, req_path)


def user_manage_commands(configuration, mig_user, req_path, user_id, user_dict,
                         kind):
    """Generate user create and delete commands for sign up backends"""
    cmd_helpers = {}
    if configuration.site_enable_peers:
        peers = '-p AUTO'
    else:
        peers = ''
    # NOTE: peers are not yet exposed in gdp_mode so don't try automatic check
    if configuration.site_enable_gdp:
        peers = ''
    if not configuration.ca_fqdn or not configuration.ca_user:
        cmd_helpers['command_cert_create'] = '[Disabled On This Site]'
        cmd_helpers['command_cert_revoke'] = '[Disabled On This Site]'
    else:
        cmd_helpers['command_cert_create'] = """on CA host (%s):
sudo su - %s
rsync -aP %s@%s:%s ~/
./ca-scripts/createusercert.py -a '%s' -d ~/%s -r '%s' -s '%s' -u '%s'""" % \
            (configuration.ca_fqdn, configuration.ca_user, mig_user,
             configuration.server_fqdn, default_db_path(configuration),
             configuration.admin_email, user_db_filename, configuration.ca_smtp,
             configuration.server_fqdn, user_id)
        cmd_helpers['command_cert_revoke'] = """on CA host (%s):
sudo su - %s
./ca-scripts/revokeusercert.py -a '%s' -d ~/%s -r '%s' -u '%s'""" % \
            (configuration.ca_fqdn, configuration.ca_user,
             configuration.admin_email, user_db_filename, configuration.ca_smtp,
             user_id)

    if kind == 'cert':
        cmd_helpers['command_user_notify'] = '[Automatic for certificates]'
    else:
        cmd_helpers['command_user_notify'] = """As '%s' on %s:
./mig/server/notifymigoid.py -a -C -I '%s'""" % \
            (mig_user, configuration.server_fqdn, user_id)

    cmd_helpers['command_user_create'] = """As '%s' on %s:
./mig/server/createuser.py -a %s %s -u '%s'""" % \
        (mig_user, configuration.server_fqdn, kind, peers, req_path)
    cmd_helpers['command_user_suspend'] = """As '%s' on %s:
./mig/server/editmeta.py '%s' status suspended""" % \
        (mig_user, configuration.server_fqdn, user_id)
    cmd_helpers['command_user_delete'] = """As '%s' on %s:
./mig/server/deleteuser.py -i '%s'""" % \
        (mig_user, configuration.server_fqdn, user_id)
    cmd_helpers['command_user_reject'] = """As '%s' on %s:
./mig/server/rejectuser.py -a %s -C -u '%s' -r 'missing required info'""" % \
        (mig_user, configuration.server_fqdn, kind, req_path)
    return cmd_helpers


def auto_add_user_allowed(configuration, user_dict):
    """Check if user with user_dict is allowed to sign up without operator
    approval e.g. using autocreate based on optional configuration limits.
    """

    for (key, val) in configuration.auto_add_user_permit:
        if not re.match(val, user_dict.get(key, 'NO SUCH FIELD')):
            return False
    return True


def peers_permit_allowed(configuration, user_dict):
    """Check if user with user_dict is allowed to manage peers based on
    optional configuration limits.
    """
    for (key, val) in configuration.site_peers_permit:
        if not re.match(val, user_dict.get(key, 'NO SUCH FIELD')):
            return False
    return True


def parse_peers_form(configuration, raw_lines, csv_sep):
    """Parse CSV form of peers into a list of peers"""
    _logger = configuration.logger
    header = None
    peers = []
    err = []
    for line in raw_lines.split('\n'):
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        parts = [i.strip() for i in line.split(csv_sep)]
        if not header:
            missing = [i for i in peers_fields if i not in parts]
            if missing:
                err.append("Parsed peers did NOT contain required field(s): %s"
                           % ', '.join(missing))
            header = parts
            continue
        if len(header) != len(parts):
            _logger.warning('skip peers line with mismatch in field count: %s'
                            % line)
            err.append("Skip peers line not matching header format: %s" %
                       html_escape(line + ' vs ' + csv_sep.join(header)))
            continue
        raw_user = dict(zip(header, parts))
        # IMPORTANT: extract ONLY peers fields and validate to avoid abuse
        peer_user = dict([(i, raw_user.get(i, '')) for i in peers_fields])
        defaults = dict([(i, REJECT_UNSET) for i in peer_user])
        (accepted, rejected) = validated_input(peer_user, defaults,
                                               list_wrap=True)
        if rejected:
            _logger.warning('skip peer with invalid value(s): %s (%s)'
                            % (line, rejected))
            unsafe_err = ' , '.join(
                ['%s=%r' % pair for pair in peer_user.items()])
            unsafe_err += '. Rejected values: ' + ', '.join(rejected)
            err.append("Skip peer user with invalid value(s): %s" %
                       html_escape(unsafe_err))
            continue
        peers.append(canonical_user(configuration, peer_user, peers_fields))
    _logger.debug('parsed form into peers: %s' % peers)
    return (peers, err)


def parse_peers_userid(configuration, raw_entries):
    """Parse list of user IDs into a list of peers"""
    _logger = configuration.logger
    peers = []
    err = []
    for entry in raw_entries:
        raw_user = distinguished_name_to_user(entry.strip())
        missing = [i for i in peers_fields if i not in raw_user]
        if missing:
            err.append("Parsed peers did NOT contain required field(s): %s"
                       % ', '.join(missing))
            continue
        # IMPORTANT: extract ONLY peers fields and validate to avoid abuse
        peer_user = dict([(i, raw_user.get(i, '').strip())
                          for i in peers_fields])
        defaults = dict([(i, REJECT_UNSET) for i in peer_user])
        (accepted, rejected) = validated_input(peer_user, defaults,
                                               list_wrap=True)
        if rejected:
            _logger.warning('skip peer with invalid value(s): %s : %s'
                            % (entry, rejected))
            unsafe_err = ' , '.join(
                ['%s=%r' % pair for pair in peer_user.items()])
            unsafe_err += '. Rejected values: ' + ', '.join(rejected)
            err.append("Skip peer user with invalid value(s): %s" %
                       html_escape(unsafe_err))
            continue
        peers.append(canonical_user(configuration, peer_user, peers_fields))
    _logger.debug('parsed user id into peers: %s' % peers)
    return (peers, err)


def parse_peers(configuration, peers_content, peers_format, csv_sep=';'):
    """Parse provided peer formats into a list of peer users.
    Please note that peers_content is the accepted list of input values.
    """
    _logger = configuration.logger
    if "userid" == peers_format:
        # NOTE: Enter Peers packs fields into full DNs handled here
        raw_peers = peers_content
        return parse_peers_userid(configuration, raw_peers)
    elif "csvform" == peers_format:
        # NOTE: first merge the individual textarea(s) from Import Peers
        raw_peers = '\n'.join(peers_content)
        return parse_peers_form(configuration, raw_peers, csv_sep)
    elif "csvupload" == peers_format:
        # TODO: extract upload
        raw_peers = ''
        return parse_peers_form(configuration, raw_peers, csv_sep)
    elif "csvurl" == peers_format:
        # TODO: fetch URL contents
        raw_peers = ''
        return parse_peers_form(configuration, raw_peers, csv_sep)
    elif "fields" == peers_format:
        # TODO: extract fields
        raw_peers = []
        return parse_peers_userid(configuration, raw_peers)
    else:
        _logger.error("unknown peers format: %s" % peers_format)
        return ([], "unknown peers format: %s" % peers_format)


def manage_pending_peers(configuration, client_id, action, change_list):
    """Helper to manage changes to pending peers list of client_id"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    pending_peers_path = os.path.join(configuration.user_settings, client_dir,
                                      pending_peers_filename)
    try:
        pending_peers = load(pending_peers_path)
    except Exception as exc:
        if os.path.exists(pending_peers_path):
            _logger.warning("could not load pending peers from %s: %s" %
                            (pending_peers_path, exc))
        pending_peers = []
    change_dict = dict(change_list)
    # NOTE: always remove old first to replace any existing and move them last
    pending_peers = [(i, j)
                     for (i, j) in pending_peers if not i in change_dict]
    if action == "add":
        pending_peers += change_list
    elif action == "remove":
        pass
    else:
        _logger.error(
            "unsupported action in manage pending peers: %s" % action)
        return False
    try:
        dump(pending_peers, pending_peers_path)
        return True
    except Exception as exc:
        _logger.warning("could not save pending peers to %s: %s" %
                        (pending_peers_path, exc))
        return False
