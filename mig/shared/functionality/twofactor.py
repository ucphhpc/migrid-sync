#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# twofactor - handle two-factor authentication with per-user shared key
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

"""Take care of the second authentication step in relation to two-factor auth.
Keeps track of active sessions and saves state files for apache to use.

Inspired by the apache google authenticator example at:
https://github.com/itemir/apache_2fa
but completely rewritten to fit our infrastructure and on-disk layout.
"""

import Cookie
import base64
import os
import re
import sys
import time
import urllib
import urlparse

import shared.returnvalues as returnvalues
from shared.auth import twofactor_available, load_twofactor_key, \
    get_twofactor_token, verify_twofactor_token
from shared.base import force_utf8
from shared.defaults import twofactor_cookie_bytes, twofactor_cookie_ttl
from shared.fileio import delete_file, make_symlink, write_file
from shared.functional import validate_input
from shared.init import initialize_main_variables
from shared.settings import load_twofactor
from shared.useradm import client_id_dir
from shared.twofactorkeywords import get_keywords_dict as twofactor_defaults


def html_tmpl(configuration):
    """Render html for 2FA token input - similar to the template used in the
    apache_2fa example but with a few custumizations to include our own logo
    and force input focus on load.
    """
    html = '''<!-- make sure content div covers any background pattern -->
<div class="twofactorbg">
<div id="twofactorbox" class="staticpage">
<img class="sitelogo" src="%(skin_base)s/logo-left.png"><br/>
<img class="authlogo" src="https://lh3.googleusercontent.com/HPc5gptPzRw3wFhJE1ZCnTqlvEvuVFBAsV9etfouOhdRbkp-zNtYTzKUmUVPERSZ_lAL=w300"><br/>
  <form method="POST">
    <input class="tokeninput" type="text" id="token" name="token"
        placeholder="Authentication Token" autocomplete="off" autofocus><br/>
    <input class="submit" type="submit" value="Submit">
  </form>
</div>
</div>
''' % {'skin_base': configuration.site_skin_base}
    return html


def signature():
    """Signature of the main function"""

    defaults = {'token': [None], 'redirect_url': ['']}
    return ['text', defaults]


def query_args(environ):
    """Helper to provide a very lax and dynamic signature based on the actual
    query string from environ. Used to allow and pass any additional args to
    the requested redirect URL without ever using them here.
    """
    env_args = urlparse.parse_qs(environ.get('QUERY_STRING', ''))
    return env_args


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = initialize_main_variables(
        client_id, op_header=False, op_title=False, op_menu=client_id)

    # Extract raw data first
    if environ is None:
        environ = os.environ
    request_url = environ.get('REQUEST_URI', '/')
    user_agent = environ.get('HTTP_USER_AGENT', '')
    user_addr = environ.get('REMOTE_ADDR', '')
    user_id = environ.get('REMOTE_USER', '')

    # IMPORTANT: use all actual args as base and override with real signature
    all_args = query_args(environ)
    defaults = signature()[1]
    all_args.update(defaults)
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 all_args, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    token = accepted['token'][-1]
    redirect_url = accepted['redirect_url'][-1]
    check_only = False

    # logger.debug("User: %s executing %s with redirect url %s" %
    #             (client_id, op_name, redirect_url))
    # logger.debug("env: %s" % environ)

    if not configuration.site_enable_twofactor:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''2FA is not enabled on the system'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    status = returnvalues.OK

    # check that the user is already authenticated (does state file exist?)
    # or run through validation of provided time-based one-time password

    client_dir = client_id_dir(client_id)
    if redirect_url:
        # Build forward query string from any real non-local args
        forward_args = {}
        for (key, val) in accepted.items():
            if key not in defaults.keys() and val != ['AllowMe']:
                forward_args[key] = val
        redirect_location = redirect_url
        if forward_args:
            redirect_location += '?%s' % urllib.urlencode(forward_args, True)
        # Manual url decoding required for e.g. slashes
        redirect_location = urllib.unquote(redirect_location)
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

    # NOTE: twofactor_defaults field availability depends on configuration
    if not redirect_url:
        # This is the 2FA setup check mode
        check_only = True
        require_twofactor = True
    elif user_id.startswith(configuration.user_mig_oid_provider) and \
            twofactor_dict.get('MIG_OID_TWOFACTOR', False):
        require_twofactor = True
    elif user_id.startswith(configuration.user_ext_oid_provider) \
            and twofactor_dict.get('EXT_OID_TWOFACTOR', False):
        require_twofactor = True
    else:
        require_twofactor = False

    # Fail gently if twofactor dependencies are unavailable
    if require_twofactor and not twofactor_available(configuration):
        logger.error("Required dependencies are missing for 2FA support")
        require_twofactor = False

    if require_twofactor:
        logger.info("detected 2FA requirement for %s on %s" % (client_id,
                                                               request_url))
        b32_secret = None
        if token:
            b32_secret = load_twofactor_key(client_id, configuration)
            if not b32_secret:
                logger.warning("found no saved 2FA secret for %s" % client_id)
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     "Please contact the %s admins to get your 2FA secret" %
                     configuration.short_title})
                return (output_objects, returnvalues.ERROR)
        # Check that user provided matching token and set cookie on success
        if token and b32_secret and verify_twofactor_token(
                configuration, client_id, b32_secret, token):
            logger.info('Accepted valid auth token from %s' % client_id)
        else:
            output_objects.append(
                {'object_type': 'title', 'text': '2-Factor Authentication',
                 'skipmenu': True})
            output_objects.append({'object_type': 'html_form', 'text':
                                   html_tmpl(configuration)})
            if token:
                logger.warning('Invalid token for %s (%s vs %s) - try again' %
                               (client_id, token,
                                get_twofactor_token(configuration, client_id,
                                                    b32_secret)))
                output_objects.append({'object_type': 'html_form', 'text': '''
<div class="twofactorstatus">
<span class="error leftpad errortext">
Incorrect token provided - please try again
</span></div>'''})
                # TODO: proper rate limit source / user here?
                time.sleep(3)
            return (output_objects, status)
    else:
        logger.info("no 2FA requirement for %s on %s" % (client_id,
                                                         request_url))
        session_key = 'DISABLED'

    # If we get here we either got correct token or verified 2FA to be disabled

    if check_only:
        logger.info("skip session init in setup check for %s" % client_id)
    else:
        cookie = Cookie.SimpleCookie()
        # create a secure session cookie
        session_key = os.urandom(twofactor_cookie_bytes)
        session_key = re.sub(r'[=+/]+', '', base64.b64encode(session_key))
        cookie['2FA_Auth'] = session_key
        cookie['2FA_Auth']['path'] = '/'
        cookie['2FA_Auth']['expires'] = twofactor_cookie_ttl
        cookie['2FA_Auth']['secure'] = True
        cookie['2FA_Auth']['httponly'] = True

        # Create the state file to inform apache (rewrite) about auth
        session_path = os.path.join(configuration.twofactor_home, session_key)
        client_link_path = os.path.join(
            configuration.twofactor_home, client_dir)
        # We save user info just to be able to monitor and expire active
        # sessions
        session_data = '''%s
%s
%s
''' % (user_agent, user_addr, client_id)
        write_status = True
        if not write_file(session_data, session_path, configuration.logger):
            delete_file(session_data, logger, allow_missing=True)
            logger.error("could not create 2FA session for %s"
                         % client_id)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "Internal error: could not create 2FA session!"})
            return (output_objects, returnvalues.ERROR)

        logger.info("saved 2FA session for %s in %s"
                    % (client_id, session_path))

        # NOTE: this make_symlink call may result in a race if non-2FA clients
        #       issue multiple parallel requests to trigger concurrent 2FA init.
        #       Missing clean-up may also cause error in creation on next login.
        # We only need the symlink to 2FA log out so we ignore all such errors.
        if make_symlink(session_key, client_link_path, logger, force=True):
            logger.info("created 2FA session symlink %s -> %s"
                        % (session_path, client_link_path))
        else:
            logger.error("2FA session symlink create %s -> %s failed" %
                         (session_path, client_link_path))

    if redirect_url:
        headers.append(tuple(str(cookie).split(': ', 1)))
        output_objects.append({'object_type': 'start', 'headers': headers})
        output_objects.append({'object_type': 'script_status'})
    else:
        output_objects.append(
            {'object_type': 'title', 'text': '2FA', 'skipmenu': True})
        output_objects.append({'object_type': 'html_form', 'text': '''
<!-- Keep similar spacing -->
<div class="twofactorbg">
<div class="twofactorstatus">
<p class="centertext">
<span class="ok leftpad">
Correct token provided!
</span>
</p>
<p>
<a href="">Test again</a> or <a href="javascript:close();">close</a> this
tab/window and proceed.
</p>
</div>
</div>'''})
    # logger.debug("return from %s for %s with headers: %s" %
    #             (op_name, client_id, headers))
    return (output_objects, status)
