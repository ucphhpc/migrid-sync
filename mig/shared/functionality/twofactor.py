#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# twofactor - handle two-factor authentication with per-user shared key
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

"""Take care of the second authentication step in relation to two-factor auth.
Keeps track of active sessions and saves state files for apache to use.

Inspired by the apache google authenticator example at:
https://github.com/itemir/apache_2fa
but completely rewritten to fit our infrastructure and on-disk layout.
"""

from __future__ import absolute_import

import Cookie
import os
import time

from mig.shared import returnvalues
from mig.shared.auth import twofactor_available, load_twofactor_key, \
    get_twofactor_token, verify_twofactor_token, generate_session_key, \
    save_twofactor_session, expire_twofactor_session
from mig.shared.base import requested_backend, requested_page, extract_field, \
    verify_local_url
from mig.shared.defaults import twofactor_cookie_ttl, AUTH_MIG_OID, \
    AUTH_EXT_OID, AUTH_MIG_OIDC, AUTH_EXT_OIDC
from mig.shared.functional import validate_input
from mig.shared.griddaemons.openid import default_max_user_hits, \
    default_user_abuse_hits, default_proto_abuse_hits, hit_rate_limit, \
    expire_rate_limit, validate_auth_attempt
from mig.shared.init import initialize_main_variables
from mig.shared.html import twofactor_token_html, themed_styles, themed_scripts
from mig.shared.httpsclient import detect_client_auth, require_twofactor_setup
from mig.shared.settings import load_twofactor
from mig.shared.twofactorkeywords import get_keywords_dict as twofactor_defaults
from mig.shared.url import urlencode, unquote, parse_qs


def signature(configuration, setup_mode=False):
    """Signature of the main function"""

    defaults = {'action': ['auth'], 'token': [None], 'redirect_url': ['']}
    if setup_mode:
        defaults['topic'] = ['']
        setup_defaults = twofactor_defaults(configuration)
        for key in setup_defaults:
            defaults[key] = ['']
    return ['text', defaults]


def query_args(environ):
    """Helper to provide a very lax and dynamic signature based on the actual
    query string from environ. Used to allow and pass any additional args to
    the requested redirect URL without ever using them here.
    """
    env_args = parse_qs(environ.get('QUERY_STRING', ''))
    return env_args


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(
        client_id, op_header=False, op_title=False, op_menu=client_id)
    # IMPORTANT: no title in init above so we MUST call it immediately here
    #            or basic styling will break on e.g. the check token result.
    styles = themed_styles(configuration)
    scripts = themed_scripts(configuration, logged_in=False)
    output_objects.append(
        {'object_type': 'title', 'text': '2-Factor Authentication',
         'skipmenu': True, 'style': styles, 'script': scripts})

    # Extract raw data first
    if environ is None:
        environ = os.environ
    request_url = requested_page(environ, fallback='/')
    user_agent = environ.get('HTTP_USER_AGENT', '')
    user_addr = environ.get('REMOTE_ADDR', '')
    auth_type, auth_flavor = detect_client_auth(configuration, environ)
    proto = 'https'

    # IMPORTANT: use all actual args as base and override with real signature
    all_args = query_args(environ)
    # TODO: detect save settings and differentiate here
    defaults = signature(configuration, setup_mode=True)[1]
    all_args.update(defaults)
    var_filters = {}
    # NOTE: args get URL-encoded which e.g. translates '@' to %40' and breaks
    #       email address verification for authenticated renew links in expire
    #       warning emails. Manually unquote any such values here.
    # TODO: integrate extend account access and change pw buttons on user pages
    #       e.g. in a Profile tab at Settings and link to that in expire mails.
    for name in ('email', 'peers_email', ):
        if name in all_args:
            var_filters[name] = unquote
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 all_args, output_objects,
                                                 allow_rejects=False,
                                                 prefilter_map=var_filters)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    action = accepted['action'][-1]
    token = accepted['token'][-1]
    redirect_url = accepted['redirect_url'][-1]
    check_only = False
    client_addr = environ.get('REMOTE_ADDR', None)
    tcp_port = int(environ.get('REMOTE_PORT', '0'))

    script_name = requested_backend(environ, "%s.py" % op_name,
                                    strip_ext=False)

    logger.debug("User: %s executing %s with redirect url %r" %
                 (client_id, op_name, redirect_url))
    # logger.debug("env: %s" % environ)

    # Seconds to delay next 2FA attempt after hitting rate limit
    delay_retry = 300
    scripts['init'] += '''
function update_reload_counter(cnt, delay) {
    var remain = (delay - cnt);
    $("#reload_counter").html(remain.toString());
    if (cnt >= delay) {
        /* Load page again without re-posting last attempt */
        location = location
    } else {
        setTimeout(function() { update_reload_counter(cnt+1, delay); }, 1000);
    }
}
    '''

    if not configuration.site_enable_twofactor:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''2FA is not enabled on the system'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not verify_local_url(configuration, redirect_url):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''The requested redirect_url is not a valid local destination'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if configuration.site_twofactor_strict_address \
            and not expire_twofactor_session(configuration,
                                             client_id,
                                             environ,
                                             allow_missing=True,
                                             not_user_addr=user_addr):
        logger.error("could not expire old 2FA sessions for %s"
                     % client_id)
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "Internal error: could not expire old 2FA sessions!"})
        return (output_objects, returnvalues.ERROR)

    status = returnvalues.OK

    # check that the user is already authenticated (does state file exist?)
    # or run through validation of provided time-based one-time password

    if redirect_url:
        # Build forward query string from any real non-local args
        forward_args = {}
        for (key, val) in accepted.items():
            if key not in defaults and val != ['AllowMe']:
                forward_args[key] = val
        redirect_location = redirect_url
        if forward_args:
            redirect_location += '?%s' % urlencode(forward_args, True)
        # Manual url decoding required for e.g. slashes
        redirect_location = unquote(redirect_location)
        headers = [('Status', '302 Moved'),
                   ('Location', redirect_location)]
        logger.debug("redirect_url %s and args %s gave %s" %
                     (redirect_url, forward_args, redirect_location))
    else:
        headers = []
    twofactor_dict = load_twofactor(client_id, configuration,
                                    allow_missing=True)
    logger.debug("found twofactor_dict for %s : %s" %
                 (client_id, twofactor_dict))
    if not twofactor_dict:
        logger.warning("fall back to twofactor defaults for %s" % client_id)
        twofactor_dict = dict([(i, j['Value']) for (i, j) in
                               twofactor_defaults(configuration).items()])

    check_missing_setup = False
    # NOTE: twofactor_defaults field availability depends on configuration
    if action == 'auth' and not redirect_url:
        # This is the 2FA setup check mode
        require_twofactor = True
        # We also get here on no action and no redirect_url after setup
        check_missing_setup = True
    elif action == 'check':
        check_only = True
        require_twofactor = True
    elif action == 'renew':
        require_twofactor = True
    elif auth_flavor == AUTH_MIG_OID and \
            twofactor_dict.get('MIG_OID_TWOFACTOR', False):
        require_twofactor = True
    elif auth_flavor == AUTH_EXT_OID and \
            twofactor_dict.get('EXT_OID_TWOFACTOR', False):
        require_twofactor = True
    # NOTE: we share OID and OIDC 2FA setting for now
    elif auth_flavor == AUTH_MIG_OIDC and \
            twofactor_dict.get('MIG_OID_TWOFACTOR', False):
        require_twofactor = True
    elif auth_flavor == AUTH_EXT_OIDC and \
            twofactor_dict.get('EXT_OID_TWOFACTOR', False):
        require_twofactor = True
    else:
        require_twofactor = False
        check_missing_setup = True

    pending_setup = False
    if check_missing_setup:
        # logger.debug("checking for pending 2FA setup")
        #  No twofactor requirement detected - mandatory setup may be pending
        pending_setup = require_twofactor_setup(configuration, script_name,
                                                client_id, environ)
        if pending_setup:
            logger.debug("send %s to required 2FA setup" % client_id)
            require_twofactor = True

    # Fail hard if twofactor dependencies are unavailable but requested
    if require_twofactor and not twofactor_available(configuration):
        logger.error("required dependencies are missing for 2FA support")
        output_objects.append({'object_type': 'error_text', 'text':
                               "Internal error: invalid site 2FA requirement!"})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # NOTE: GDP: gdpman handles pending setup until GDP V3 is in place
    # TODO: Remove 'and not configuration.site_enable_gdp'
    #       when GDP V3 is in place
    if pending_setup and not configuration.site_enable_gdp:
        if redirect_url:
            logger.info("send %s through required 2FA setup wizard" %
                        client_id)
            from mig.shared.functionality.setup import main as setup
            user_arguments_dict = {'topic': ['twofactor']}
            # Point setup back here for handling save below
            return setup(client_id, user_arguments_dict, target_op=op_name)
        else:
            logger.info("save result of required 2FA setup for %s" % client_id)
            from mig.shared.functionality.settingsaction import main as save
            # Inform save operation that it's called from here for CSRF check
            return save(client_id, user_arguments_dict, called_as=op_name)
    # NOTE: GDP: gdpman handles pending setup until GDP V3 is in place
    # TODO: Remove 'not pending_setup and'
    #       when GDP V3 is in place
    elif not pending_setup and require_twofactor:
        logger.info("detected 2FA requirement for %s on %s" % (client_id,
                                                               request_url))

        b32_secret = None
        valid_password, authorized = False, False
        disconnect, exceeded_rate_limit = False, False
        # Clean up expired entries in persistent rate limit cache
        expire_rate_limit(configuration, proto, fail_cache=delay_retry,
                          expire_delay=delay_retry)
        if hit_rate_limit(configuration, proto, client_addr, client_id,
                          max_user_hits=default_max_user_hits):
            exceeded_rate_limit = True
        elif token:
            b32_secret = load_twofactor_key(client_id, configuration)
            if not b32_secret:
                logger.warning("found no saved 2FA secret for %s" % client_id)
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     "Please contact the %s admins to get your 2FA secret" %
                     configuration.short_title})
                return (output_objects, returnvalues.ERROR)

            # Check that user provided matching token and set cookie on success
            if verify_twofactor_token(configuration, client_id, b32_secret,
                                      token):
                valid_password = True

        if token:
            # Update rate limits and write to auth log
            (authorized, disconnect) = validate_auth_attempt(
                configuration,
                proto,
                op_name,
                client_id,
                client_addr,
                tcp_port,
                secret=token,
                valid_twofa=valid_password,
                authtype_enabled=True,
                valid_auth=valid_password,
                exceeded_rate_limit=exceeded_rate_limit,
                user_abuse_hits=default_user_abuse_hits,
                proto_abuse_hits=default_proto_abuse_hits,
                max_secret_hits=1,
            )

        if exceeded_rate_limit or disconnect:
            logger.warning('Throttle twofactor from %s (%s) - past rate limit'
                           % (client_id, client_addr))
            # NOTE: we keep actual result in plain text for json extract
            output_objects.append({'object_type': 'html_form', 'text': '''
<div class="vertical-spacer"></div>
<div class="twofactorresult">
<div class="error leftpad errortext">
'''})
            output_objects.append({'object_type': 'text', 'text': """
Incorrect twofactor token provided and rate limit exceeded - please wait %d
seconds before retrying.
""" % delay_retry
                                   })
            output_objects.append({'object_type': 'html_form', 'text': '''
</div>
<div class="vertical-spacer"></div>
<div class="info leftpad">
Page will reload automatically in <span id="reload_counter">%d</span> seconds.
</div>
</div>
''' % delay_retry})
            scripts['ready'] += '''
    setTimeout(function() { update_reload_counter(1, %d); }, 1000);
''' % delay_retry
            return (output_objects, status)
        elif authorized:
            logger.info('Accepted valid auth token from %s at %s' %
                        (client_id, client_addr))
        else:
            if not client_id:
                client_short = "unspecified user"
            else:
                client_short = extract_field(client_id, 'email')
            support_html = '''
<p class="info leftpad">Twofactor authentication problems?</p>
<p>
Please
<a href="mailto:%s?subject=%s twofactor report from %s">contact support</a>
with details.
</p>
''' % (configuration.support_email, configuration.short_title, client_short)
            output_objects.append({'object_type': 'html_form', 'text':
                                   twofactor_token_html(configuration, support_html)})
            if token:
                logger.warning('Invalid token for %s (%s vs %s) - try again' %
                               (client_id, token,
                                get_twofactor_token(configuration, client_id,
                                                    b32_secret)))
                # NOTE: we keep actual result in plain text for json extract
                output_objects.append({'object_type': 'html_form', 'text': '''
<div class="twofactorresult">
<div class="error leftpad errortext">
'''})
                output_objects.append({'object_type': 'text', 'text':
                                       'Incorrect token provided - please try again'})
                output_objects.append({'object_type': 'html_form', 'text': '''
</div>
</div>'''})

            return (output_objects, status)
    else:
        logger.info("no 2FA requirement for %s on %s" % (client_id,
                                                         request_url))

    # If we get here we either got correct token or verified 2FA to be disabled

    if check_only:
        logger.info("skip session init in setup check for %s" % client_id)
    else:
        cookie = Cookie.SimpleCookie()
        # TODO: reuse any existing session?
        # create a secure session cookie
        session_key = generate_session_key(configuration, client_id)
        session_start = time.time()
        cookie['2FA_Auth'] = session_key
        cookie['2FA_Auth']['path'] = '/'
        # NOTE: SimpleCookie translates expires ttl to actual date from now
        cookie['2FA_Auth']['expires'] = twofactor_cookie_ttl
        cookie['2FA_Auth']['secure'] = True
        cookie['2FA_Auth']['httponly'] = True

        # GDP only allow one active 2FA-session
        if configuration.site_enable_gdp:
            if not expire_twofactor_session(configuration,
                                            client_id,
                                            environ,
                                            allow_missing=True):
                logger.error("could not expire old 2FA sessions for %s"
                             % client_id)
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     "Internal error: could not expire old 2FA sessions!"})
                return (output_objects, returnvalues.ERROR)

        # Create the state file to inform apache (rewrite) about auth
        # We save user info to be able to monitor and expire active sessions
        if not save_twofactor_session(configuration, client_id, session_key,
                                      user_addr, user_agent, session_start):
            logger.error("could not create 2FA session for %s"
                         % client_id)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "Internal error: could not create 2FA session!"})
            return (output_objects, returnvalues.ERROR)

        logger.info("saved 2FA session for %s in %s"
                    % (client_id, session_key))

    if (action == 'auth' and redirect_url) \
            or action == 'renew':
        headers.append(tuple(("%s" % cookie).split(': ', 1)))
        output_objects.append({'object_type': 'start', 'headers': headers})
        output_objects.append({'object_type': 'script_status'})
    if (action == 'auth' and redirect_url):
        reply_status = ""
        reply_msg = ""
    elif action == 'auth' and not redirect_url:
        reply_status = "error"
        reply_msg = "Missing redirect_url"
    elif action == 'check':
        reply_status = "ok"
        reply_msg = "Correct token provided!"
    elif action == 'renew':
        reply_status = "ok"
        reply_msg = "Twofactor session renewed!"
    else:
        reply_status = "error"
        reply_msg = "Unknown action: %r" % action
    if reply_status:
        output_objects.append({'object_type': 'html_form', 'text': '''
<!-- Keep similar spacing -->
<div class="twofactorbg">
<div id="twofactorstatus" class="twofactorresult">
<div class="%s leftpad">
''' % reply_status})
        # NOTE: we keep actual result in plain text for json extract
        output_objects.append({'object_type': 'text', 'text': reply_msg})
        output_objects.append({'object_type': 'html_form', 'text': '''
</div>'''})
        if action == 'check':
            output_objects.append({'object_type': 'html_form', 'text': '''
<p>
<a href="?action=check">Test again</a> or <a href="javascript:close();">close</a> this
tab/window and proceed.
</p>'''})
        output_objects.append({'object_type': 'html_form', 'text': '''
</div>
</div>'''})
    # logger.debug("return from %s for %s with headers: %s" %
    #             (op_name, client_id, headers))
    return (output_objects, status)
