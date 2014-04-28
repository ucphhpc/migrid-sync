#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# certreq - helpers for certificate requests
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""This module contains various helper contents for the certificate request
handlers"""

import os
import time

from fileio import delete_file
# Expose some helper variables for functionality backends
from safeinput import name_extras, password_extras, password_min_len, \
    password_max_len, valid_password_chars, valid_name_chars, dn_max_len
from shared.serial import load, dump


def cert_css_helpers():
    """Stylesheets to include in the cert/ext req page header"""
    css = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.custom.css" media="screen"/>
'''
    return css

def cert_js_helpers(fields):
    """Javascript to include in the cert/ext req page header"""
    js = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
'''
    js += """
  <script type='text/javascript'>
  function rtfm_warn(message) {
      return confirm(message + ': Proceed anyway? (If you read and followed the instructions!)');
  }
  
  function check_cert_id() {
      //alert('#cert_id_help');
      if ($('#cert_id_field').val().indexOf('/') == -1) {
          return rtfm_warn('Cert DN does not look like a proper DN');
      }
      return true;
  }
  function check_cert_name() {
      //alert('#cert_name_help');
      if ($('#cert_name_field').val().indexOf(' ') == -1) {
          return rtfm_warn('Full name does not look like a real name');
      }
      return true;
  }
  function check_full_name() {
      //alert('#full_name_help');
      if ($('#full_name_field').val().indexOf(' ') == -1) {
          return rtfm_warn('Full name does not look like a real name');
      }
      return true;
  }
  function check_email() {
      //alert('#email_help');
      if ($('#email_field').val().search('@') == -1) {
          return rtfm_warn('Email is invalid');
      }
      if ($('#email_field').val().search('@gmail.com') != -1 || $('#email_field').val().search('@yahoo.com') != -1 || $('#email_field').val().search('@hotmail.com') != -1) {
          return rtfm_warn('Email does not look like a organization address');
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
      return true;
  }
  function check_state() {
      //alert('#state_help');
      if ($('#country_field').val().search('US') == -1) {
          if ($('#state_field').val() && $('#state_field').val() != 'NA') {
              return rtfm_warn('State only makes sense for US users');
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
  function check_comment() {
      //alert('#comment_help');
      return true;
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
""" % {'password_min_len': password_min_len, 'password_max_len': password_max_len}
    js += """
  function validate_form() {
      //alert('validate form');
"""
    js += """
      var status = %s""" % ' && '.join(['check_%s()' % name for name in fields])
    js += """
      //alert('validate form: ' +status);
      return status;
  }

"""
    js += """
  $(document).ready( function() {
      init_context_help();
"""
    for name in fields:
        js += """
      bind_help($('#%s_field'), $('#%s_help').html());
""" % (name, name)
    js += """
  });
</script>
"""
    return js

def build_certreqitem_object(configuration, certreq_dict):
    """Build a certreq object based on input certreq_dict"""

    certreq_obj = {
        'object_type': 'certreq',
        'id': certreq_dict['id'],
        'full_name': certreq_dict['full_name'],
        'email': certreq_dict['email'],
        'organization': certreq_dict['organization'],
        'country': certreq_dict['country'],
        'state': certreq_dict['state'],
        'comment': certreq_dict['comment'],
        'created': time.ctime(certreq_dict['created']),
        }
    return certreq_obj

def list_cert_reqs(configuration):
    """Find all pending certificate requests"""
    logger = configuration.logger
    certreq_list = []
    dir_content = []

    try:
        dir_content = os.listdir(configuration.user_pending)
    except Exception:
        if not os.path.isdir(configuration.user_pending):
            try:
                os.mkdir(configuration.user_pending)
            except Exception, err:
                logger.error(
                    'certreqfunctions.py: not able to create directory %s: %s'
                    % (configuration.certreq_home, err))
                return (False, "archive setup is broken")
            dir_content = []

    for entry in dir_content:

        # Skip dot files/dirs

        if entry.startswith('.'):
            continue
        if is_cert_req(entry, configuration):
            certreq_list.append(entry)
        else:
            logger.warning(
                '%s in %s is not a file, move it?'
                % (entry, configuration.user_pending))
    return (True, certreq_list)

def is_cert_req(req_id, configuration):
    """Check that req_id is an existing certificate request"""
    req_path = os.path.join(configuration.user_pending, req_id)
    if os.path.isfile(req_path):
        return True
    else:
        return False

def get_cert_req(req_id, configuration):
    """Helper to fetch dictionary for a pending certificate request"""
    req_path = os.path.join(configuration.user_pending, req_id)
    req_dict = load(req_path)
    if not req_dict:
        return (False, 'Could not open certificate request %s' % req_id)
    else:
        req_dict['id'] = req_id
        req_dict['created'] = os.path.getctime(req_path)
        return (True, req_dict)

def accept_cert_req(req_id, configuration):
    """Helper to accept a pending certificate request"""
    req_path = os.path.join(configuration.user_pending, req_id)
    # TODO: run createuser
    return False

def delete_cert_req(req_id, configuration):
    """Helper to delete a pending certificate request"""
    req_path = os.path.join(configuration.user_pending, req_id)
    return delete_file(req_path, configuration.logger)

