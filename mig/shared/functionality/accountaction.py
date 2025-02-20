#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# accountaction - handle account actions like change pw and renew access
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Account actions backend for password change and account renewal."""

from __future__ import absolute_import

import os
import time

from mig.shared import returnvalues
from mig.shared.base import is_gdp_user
from mig.shared.defaults import keyword_auto, AUTH_MIG_CERT, AUTH_MIG_OID, \
     AUTH_MIG_OIDC #, AUTH_EXT_CERT, AUTH_EXT_OID, AUTH_EXT_OIDC
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.gdp.all import ensure_gdp_user
from mig.shared.griddaemons.https import default_user_abuse_hits, \
     default_proto_abuse_hits, hit_rate_limit, expire_rate_limit, \
     validate_auth_attempt
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.htmlgen import themed_styles, themed_scripts
from mig.shared.httpsclient import detect_client_auth, find_auth_type_and_label
from mig.shared.init import initialize_main_variables #, find_entry
#from mig.shared.notification import send_email
from mig.shared.pwcrypto import make_hash
from mig.shared.userdb import default_db_path
from mig.shared.useradm import default_search, search_users, create_user

SUPPORTED_ACTIONS = ["RENEW_ACCESS",
                     #"CHANGE_PASSWORD"
                     ]

def allow_renew_access(configuration, client_id, user_dict, auth_flavor):
    """Helper to check prerequisites for the RENEW_ACCESS requests."""
    _logger = configuration.logger
    allow_renew, renew_err = False, 'Not fully implemented, yet'
    if auth_flavor in (AUTH_MIG_CERT, AUTH_MIG_OID, AUTH_MIG_OIDC):
        _logger.debug("Account renew for %r is allowed to proceed" % client_id)
        allow_renew, renew_err = True, ""
    else:
        _logger.warning("Account renew for %r with %s auth unsupported" % \
                       (client_id, auth_flavor))
        renew_err = "Account access renew refused - invalid auth flavor!"
    return (allow_renew, renew_err)


def renew_access(configuration, client_id, user_dict, auth_flavor):
    """Helper to actually renew access for the RENEW_ACCESS requests."""
    _logger = configuration.logger
    renew_status, renew_err = False, 'Not fully implemented yet'
    peer_pattern = keyword_auto
    db_path = default_db_path(configuration)
    old_expire = user_dict.get('expire', -1)
    if auth_flavor == AUTH_MIG_CERT:
        extend_days = configuration.cert_valid_days
    elif auth_flavor == AUTH_MIG_OID:
        extend_days = configuration.oid_valid_days
    elif auth_flavor == AUTH_MIG_OIDC:
        extend_days = configuration.oidc_valid_days
    else:
        extend_days = configuration.generic_valid_days
    max_extend_secs = extend_days * 24 * 3600
    new_expire = max(old_expire, time.time() + max_extend_secs)
    user_dict['expire'] = new_expire
    try:
        _logger.info("Renew %(distinguished_name)r with expire at %(expire)d" \
                     % user_dict)
        updated = create_user(user_dict, configuration, db_path,
                              ask_renew=False, default_renew=True,
                              verify_peer=peer_pattern, auto_create_db=False)
        if configuration.site_enable_gdp:
            (gdp_success, msg) = ensure_gdp_user(configuration,
                                                  "127.0.0.1",
                                                  user_dict['distinguished_name'])
            if not gdp_success:
                raise Exception("Failed to renew GDP user: %s" % msg)
        renewed_expire = updated.get('expire', -1)
        _logger.info("Renewed %(distinguished_name)r to expire at %(expire)d" % \
                    updated)
        if renewed_expire > old_expire:
            renew_status, renew_err = True, ""
        else:
            renew_err = "Renew could not extend account expire value (no peer?)"
    except Exception as exc:
        _logger.warning("Error renewing user %r: %s" % (client_id, exc))
    
    # TODO: send email on renew?
    return (renew_status, renew_err)


def allow_change_password(configuration, client_id, user_dict, auth_flavor,
                    curpassword, password, verifypassword):
    """Helper to check prerequisites for the CHANGE_PASSWORD requests."""
    _logger = configuration.logger
    allow_change, change_err = False, 'Not allowed'
    saved_password = user_dict['password']
    saved_password_hash = user_dict.get('password_hash', '')
    # MiG OpenID users without password recovery have empty
    # password value and on renew we then leave any saved cert
    # password alone.
    # External OpenID users do not provide a password so again any
    # existing password should be left alone on renewal.
    # The password_hash field is not guaranteed to exist.
    if auth_flavor == AUTH_MIG_CERT:
        if saved_password != curpassword:
            _logger.warning("reject %r password change - wrong password" % \
                           client_id)
            change_err = "Password change refused - password mismatch!"
            return (allow_change, change_err)
    elif auth_flavor in (AUTH_MIG_OID, AUTH_MIG_OIDC):
        if not saved_password_hash:
            _logger.warning("reject %r password change - no saved hash" % \
                           client_id)
            change_err = "Password change refused - password auth disabled!"
            return (allow_change, change_err)

        curpassword_hash = make_hash(configuration, curpassword)
        if saved_password_hash != curpassword_hash:
            _logger.warning("reject %r password change - wrong password" % \
                           client_id)
            change_err = "Password change refused - password mismatch!"
            return (allow_change, change_err)
    else:
        _logger.warning("Invalid password change for %r with %s auth" % \
                       (client_id, auth_flavor))
        change_err = "Password change refused - invalid auth flavor!"
        return (allow_change, change_err)

    if password != verifypassword:
        _logger.warning("Password change for %r rejected with verify diff" % \
                       client_id)
        change_err = "Password change refused - password and verify differ!"
        return (allow_change, change_err)

    _logger.debug("Password change for %r is allowed to proceed" % client_id)
    allow_change, change_err = True, ""
    return (allow_change, change_err)


def change_password(configuration, client_id, user_dict, auth_flavor,
                    curpassword, password, verifypassword):
    """Helper to actually change password for the RENEW_ACCESS requests."""
    _logger = configuration.logger
    # TODO: implement
    change_status, change_err = False, 'Not implemented'
    # TODO: send email on renew
    return (change_status, change_err)


def signature(configuration):
    """Signature of the main function"""

    defaults = {
        'action': REJECT_UNSET,
        'curpassword': [''],
        'password': [''],
        'verifypassword': [''],
    }
    return ['text', defaults]


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_title=False,
                                  op_menu=False)
    # IMPORTANT: no title in init above so we MUST call it immediately here
    #            or basic styling will break on e.g. the check user result.
    styles = themed_styles(configuration)
    scripts = themed_scripts(configuration, logged_in=False)
    title_entry = {'object_type': 'title',
                   'text': '%s account action' %
                   configuration.short_title,
                   'skipmenu': True, 'style': styles, 'script': scripts}
    output_objects.append(title_entry)
    output_objects.append({'object_type': 'header', 'text':
                           '%s account action' %
                           configuration.short_title
                           })

    defaults = signature(configuration)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        # NOTE: 'accepted' is a non-sensitive error string here
        logger.warning('%s invalid input: %s' % (op_name, accepted))
        return (accepted, returnvalues.CLIENT_ERROR)

    action = accepted['action'][-1].strip()    
    curpassword = accepted['curpassword'][-1].strip()
    password = accepted['password'][-1].strip()
    verifypassword = accepted['verifypassword'][-1].strip()

    # Seconds to delay next attempt after hitting rate limit
    if action == "RENEW_ACCESS":
        delay_retry = 3600
    elif action == "CHANGE_PASSWORD":
        delay_retry = 900
    else:
        delay_retry = 300
    scripts['init'] += '''
function update_reload_counter(cnt, delay) {
    var remain = (delay - cnt);
    $("#reload_counter").html(remain.toString());
    if (cnt >= delay) {
        /* Load previous page again without re-posting last attempt */
        location = history.back();
    } else {
        setTimeout(function() { update_reload_counter(cnt+1, delay); }, 1000);
    }
}
    '''

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action not in SUPPORTED_ACTIONS:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Unsupported account action: %r' % action})
        output_objects.append(
            {'object_type': 'link', 'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Try again"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    (auth_type_name, auth_flavor) = detect_client_auth(configuration, environ)
    (auth_type, auth_label) = find_auth_type_and_label(configuration,
                                                       auth_type_name,
                                                       auth_flavor)
    if auth_type not in configuration.site_login_methods:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Site does not support %r authentication' %
                               auth_type_name})
        output_objects.append(
            {'object_type': 'link', 'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Try again"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    logger.info('got %s account %s request from %r' % (auth_type_name, action,
                                                       client_id))

    client_addr = os.environ.get('REMOTE_ADDR', None)
    tcp_port = int(os.environ.get('REMOTE_PORT', '0'))

    status = returnvalues.OK

    # Rate account action attempts for any client_id from source addr to prevent
    # excessive requests spamming users or overloading server.
    # We do so no matter if client_id matches a valid user to prevent disclosure.
    # Rate limit does not affect action for another ID from same address as
    # that may be perfectly valid e.g. if behind a shared NAT-gateway.
    proto = 'https'
    disconnect, exceeded_rate_limit = False, False
    # Clean up expired entries in persistent rate limit cache
    expire_rate_limit(configuration, proto, fail_cache=delay_retry,
                      expire_delay=delay_retry)
    if hit_rate_limit(configuration, proto, client_addr, client_id,
                      max_user_hits=1):
        exceeded_rate_limit = True
    # Update rate limits and write to auth log
    (authorized, disconnect) = validate_auth_attempt(
        configuration,
        proto,
        "accountupdate",
        client_id,
        client_addr,
        tcp_port,
        secret=curpassword,
        authtype_enabled=True,
        modify_account=True,
        exceeded_rate_limit=exceeded_rate_limit,
        user_abuse_hits=default_user_abuse_hits,
        proto_abuse_hits=default_proto_abuse_hits,
        max_secret_hits=1,
        skip_notify=True,
    )

    if exceeded_rate_limit or disconnect:
        logger.warning('Throttle %s for %s from %s - past rate limit' %
                       (op_name, client_id, client_addr))
        # NOTE: we keep actual result in plain text for json extract
        output_objects.append({'object_type': 'html_form', 'text': '''
<div class="vertical-spacer"></div>
<div class="error leftpad errortext">
'''})
        output_objects.append({'object_type': 'text', 'text': """
Invalid input or rate limit exceeded - please wait %d seconds before retrying.
""" % delay_retry
                               })
        output_objects.append({'object_type': 'html_form', 'text': '''
</div>
<div class="vertical-spacer"></div>
<div class="info leftpad">
Origin will reload automatically in <span id="reload_counter">%d</span> seconds.
</div>
</div>
''' % delay_retry})
        scripts['ready'] += '''
    setTimeout(function() { update_reload_counter(1, %d); }, 1000);
''' % delay_retry
        return (output_objects, status)

    search_filter = default_search()
    search_filter['distinguished_name'] = client_id
    (_, hits) = search_users(search_filter, configuration, keyword_auto, False)
    # Filter out any gdp project users
    hits = [i for i in hits if not is_gdp_user(configuration, i[0])]
    if len(hits) != 1:
        logger.warning("%d local users unexpectedly matched %r" % (len(hits),
                                                                   client_id))
        output_objects.append({
            'object_type': 'error_text', 'text':
            """Account action failed with internal error. Please report to
support if the problem persists.
            """})
        status = returnvalues.SYSTEM_ERROR
        return (output_objects, status)

    logger.debug('handle %s account %s request from %r' % (auth_type_name,
                                                           action, client_id))
    (uid, user_dict) = hits[0]
    if action == "CHANGE_PASSWORD":
       allowed, err = allow_change_password(configuration, client_id,
                                            user_dict, auth_flavor,
                                            curpassword, password,
                                            verifypassword)
       if not allowed:
           output_objects.append(
               {'object_type': 'error_text', 'text':
                'Refused account password change: %s' % err})
           output_objects.append(
               {'object_type': 'link', 'destination':
                'javascript:history.back();',
                'class': 'genericbutton', 'text': "Try again"})
           return (output_objects, returnvalues.CLIENT_ERROR)

       changed, err = change_password(configuration, client_id, user_dict,
                                      auth_flavor, curpassword, password,
                                      verifypassword)
       if not changed:
           output_objects.append(
               {'object_type': 'error_text', 'text':
                'Failed account password change: %s' % err})
           output_objects.append(
               {'object_type': 'link', 'destination':
                'javascript:history.back();',
                'class': 'genericbutton', 'text': "Try again"})
           return (output_objects, returnvalues.CLIENT_ERROR)            

       output_objects.append(
           {'object_type': 'text', 'text':
            'Your account password was successfully changed'})

    elif action == "RENEW_ACCESS":
        allowed, err = allow_renew_access(configuration, client_id,
                                          user_dict, auth_flavor)
        if not allowed:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Refused account access renew: %s' % err})
            output_objects.append(
                {'object_type': 'link', 'destination':
                 'javascript:history.back();',
                 'class': 'genericbutton', 'text': "Try again"})
            return (output_objects, returnvalues.CLIENT_ERROR)

        renewed, err = renew_access(configuration, client_id, user_dict,
                                    auth_flavor)
        if not renewed:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Failed to renew account access: %s' % err})
            output_objects.append(
                {'object_type': 'link', 'destination':
                 'javascript:history.back();',
                 'class': 'genericbutton', 'text': "Try again"})
            return (output_objects, returnvalues.CLIENT_ERROR)

        output_objects.append(
            {'object_type': 'text', 'text':
                 'Your account access was successfully renewed.'})
    else:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Unsupported account action: %s' % action})
            output_objects.append(
                {'object_type': 'link', 'destination':
                 'javascript:history.back();',
                 'class': 'genericbutton', 'text': "Try again"})
            return (output_objects, returnvalues.CLIENT_ERROR)
    
    logger.debug("Account %s %s completed" % (auth_type_name, action))
    output_objects.append(
        {'object_type': 'link', 'destination': 'account.py',
         'class': 'genericbutton', 'text': "Show Account Info"})
    return (output_objects, status)
