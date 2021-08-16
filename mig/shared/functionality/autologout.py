#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# autologout - auto-force-expire local login session
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Automatic logout to force login session expiry"""

from __future__ import absolute_import

import os

from mig.shared.auth import expire_twofactor_session
from mig.shared import returnvalues
from mig.shared.defaults import csrf_field
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import trust_handler, get_csrf_limit
from mig.shared.httpsclient import extract_client_openid
from mig.shared.init import initialize_main_variables
from mig.shared.pwhash import make_csrf_token
from mig.shared.useradm import expire_oid_sessions, find_oid_sessions
from mig.shared.url import base32urldecode


def signature():
    """Signature of the main function"""

    defaults = {'redirect_to': ['']}
    return ['text', defaults]


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=False)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    logger.debug('Accepted arguments: %s' % accepted)

    status = returnvalues.OK
    unpacked_url = unpacked_query = ''
    packed_url = accepted['redirect_to'][-1].strip()
    if packed_url:
        # IMPORTANT: further validate that packed redirect_to is signed and safe
        try:
            (unpacked_url, unpacked_query) = base32urldecode(configuration,
                                                             packed_url)
        except Exception as exc:
            logger.error('base32urldecode failed: %s' % exc)
            output_objects.append({'object_type': 'error_text', 'text':
                                   '''failed to unpack redirect_to value!'''
                                   })
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Validate trust on unpacked url and query

    if (unpacked_url or unpacked_query) \
            and not trust_handler(configuration, 'get', unpacked_url, unpacked_query,
                                  client_id, get_csrf_limit(configuration), environ):
        logger.error('validation of unpacked url %s and query %s failed!' %
                     (unpacked_url, unpacked_query))
        output_objects.append({'object_type': 'error_text', 'text': '''Only
accepting fully signed GET requests to prevent unintended redirects'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # NOTE: from this point it's safe to use unpacked_url and unpacked_query
    redirect_url, redirect_query_dict = unpacked_url, unpacked_query

    output_objects.append({'object_type': 'header',
                           'text': 'Auto logout'})
    (oid_db, identity) = extract_client_openid(configuration, environ,
                                               lookup_dn=False)
    logger.info('%s from %s with identity %s' % (op_name, client_id,
                                                 identity))
    if client_id and client_id == identity:
        output_objects.append({'object_type': 'warning',
                               'text':
                               """You're accessing %s with a user certificate and should never
            end up at this auto logout page.
            Please refer to your browser and system documentation for details."""
                               % configuration.short_title})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if redirect_url:
        msg = 'Auto log out first to avoid '
        if redirect_url.find('autocreate') != -1:
            msg += 'sign up problems ...'
        else:
            msg += 'stale sessions ...'
        output_objects.append({'object_type': 'html_form', 'text':
                               '''<p class="spinner iconleftpad">%s</p>''' % msg})

    # OpenID requires logout on provider and in local mod-auth-openid database.
    # IMPORTANT: some browsers like Firefox may inadvertently renew the local
    # OpenID session while loading the resources for this page (in parallel).

    logger.info('expiring active sessions for %s in %s' % (identity,
                                                           oid_db))
    (success, _) = expire_oid_sessions(configuration, oid_db, identity)
    logger.info('verifying no active sessions left for %s' % identity)
    (found, remaining) = find_oid_sessions(configuration, oid_db,
                                           identity)
    if success and found and not remaining:

        # Expire twofactor session

        expire_twofactor_session(
            configuration, client_id, environ, allow_missing=True)

        if redirect_url:
            # Generate HTML and submit redirect form

            csrf_limit = get_csrf_limit(configuration, environ)
            csrf_token = make_csrf_token(configuration, 'post',
                                         op_name, client_id, csrf_limit)
            html = \
                """
            <form id='return_to_form' method='post' action='%s'>
                <input type='hidden' name='%s' value='%s'>""" % \
                (redirect_url, csrf_field, csrf_token)
            for key in redirect_query_dict:
                for value in redirect_query_dict[key]:
                    html += \
                        """
                    <input type='hidden' name='%s' value='%s'>""" \
                        % (key, value)
            html += \
                """
            </form>
            <script type='text/javascript'>
                document.getElementById('return_to_form').submit();
            </script>"""
            output_objects.append({'object_type': 'html_form',
                                   'text': html})
        else:
            text = """You are now logged out of %s""" \
                % configuration.short_title
            output_objects.append({'object_type': 'text',
                                   'text': text})
    else:
        logger.error('remaining active sessions for %s: %s'
                     % (identity, remaining))
        status = returnvalues.CLIENT_ERROR

    if status == returnvalues.CLIENT_ERROR:
        output_objects.append({'object_type': 'error_text',
                               'text': 'Could not automatically log you out of %s!'
                               % configuration.short_title})

    return (output_objects, status)
