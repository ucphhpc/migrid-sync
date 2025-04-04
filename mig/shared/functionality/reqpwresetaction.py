#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqpwresetaction - handle account password reset requests and send email to user
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

"""Request account password reset action back end"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import auth_type_description, canonical_user_with_peers, \
    cert_field_map, is_gdp_user, mask_creds
from mig.shared.defaults import RESET_TOKEN_TTL, keyword_auto
from mig.shared.functional import REJECT_UNSET, validate_input
from mig.shared.griddaemons.https import default_proto_abuse_hits, \
    default_user_abuse_hits, expire_rate_limit, hit_rate_limit, \
    validate_auth_attempt
from mig.shared.handlers import get_csrf_limit, safe_handler
from mig.shared.htmlgen import themed_scripts, themed_styles
from mig.shared.init import initialize_main_variables
from mig.shared.notification import send_email
from mig.shared.pwcrypto import generate_reset_token
from mig.shared.url import urlencode
from mig.shared.useradm import default_search, search_users


def signature(configuration):
    """Signature of the main function"""

    defaults = {
        'cert_id': REJECT_UNSET,
        'auth_type': REJECT_UNSET,
    }
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_title=False,
                                  op_menu=False)
    # IMPORTANT: no title in init above so we MUST call it immediately here
    #            or basic styling will break on e.g. the check user result.
    styles = themed_styles(configuration)
    scripts = themed_scripts(configuration, logged_in=False)
    title_entry = {'object_type': 'title',
                   'text': '%s reset account password request' %
                   configuration.short_title,
                   'skipmenu': True, 'style': styles, 'script': scripts}
    output_objects.append(title_entry)
    output_objects.append({'object_type': 'header', 'text':
                           '%s reset account password request' %
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

    # Seconds to delay next reset attempt after hitting rate limit
    delay_retry = 900
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
    smtp_server = configuration.smtp_server

    cert_id = accepted['cert_id'][-1].strip()
    auth_type = accepted['auth_type'][-1].strip()
    auth_type_name = auth_type_description(configuration, auth_type)
    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not cert_id:
        output_objects.append({'object_type': 'error_text', 'text':
                               'You must provide an email or complete ID!'})
        output_objects.append(
            {'object_type': 'link', 'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Try again"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if auth_type not in configuration.site_login_methods:
        output_objects.append({'object_type': 'error_text', 'text':
                               'You must provide a supported auth_type!'})
        output_objects.append(
            {'object_type': 'link', 'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Try again"})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif auth_type.startswith('ext'):
        output_objects.append({'object_type': 'text', 'text': """
Please contact the %s providers if you want to reset your associated password.
""" % auth_type_name})
        output_objects.append(
            {'object_type': 'link', 'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Back"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    client_addr = os.environ.get('REMOTE_ADDR', None)
    tcp_port = int(os.environ.get('REMOTE_PORT', '0'))
    anon_migoid_url = configuration.migserver_https_sid_url

    status = returnvalues.OK

    # Rate limit password reset attempts for any cert_id from source addr
    # to prevent excessive requests spamming users or overloading server.
    # We do so no matter if cert_id matches a valid user to prevent disclosure.
    # Rate limit does not affect reset for another ID from same address as
    # that may be perfectly valid e.g. if behind a shared NAT-gateway.
    proto = 'https'
    disconnect, exceeded_rate_limit = False, False
    # Clean up expired entries in persistent rate limit cache
    expire_rate_limit(configuration, proto, fail_cache=delay_retry,
                      expire_delay=delay_retry)
    if hit_rate_limit(configuration, proto, client_addr, cert_id,
                      max_user_hits=1):
        exceeded_rate_limit = True
    # Update rate limits and write to auth log
    (authorized, disconnect) = validate_auth_attempt(
        configuration,
        proto,
        "passwordreset",
        cert_id,
        client_addr,
        tcp_port,
        secret=None,
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
                       (op_name, cert_id, client_addr))
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
    if '/' in cert_id:
        search_filter['distinguished_name'] = cert_id
    else:
        # Registered emails are automatically lowercased
        search_filter['email'] = cert_id.lower()
    (_, hits) = search_users(search_filter, configuration, keyword_auto, False)
    user_dict = None
    for (uid, user_dict) in hits:
        if is_gdp_user(configuration, uid):
            logger.debug("skip password reset for gdp sub-user %r" % cert_id)
            continue

        # NOTE: we generate a password reset token and send a reset password
        #       link including the token in the query to the registered email.
        #       Then the resulting create_user call can verify the proper owner
        #       authenticity of the reset request.
        #       The token is time limited and contains information to match the
        #       old saved password (or hash) in order to verify owner received
        #       and used the reset email link and to prevent replay/reuse.
        try:
            reset_token = generate_reset_token(configuration, user_dict,
                                               auth_type)
        except ValueError:
            logger.info("skip password reset for %r without matching auth" %
                        cert_id)
            continue

        user_id = user_dict['distinguished_name']
        user_dict['authorized'] = (user_id == client_id)
        logger.info('got account %s password reset request from: %s' %
                    (auth_type_name, mask_creds(user_dict)))

        # Only include actual values in query
        req_fields = [i for i in cert_field_map if user_dict.get(i, '')]
        user_req = canonical_user_with_peers(
            configuration, user_dict, req_fields)
        user_req['reset_token'] = reset_token
        user_req['comment'] = 'Password update with token\n%s ... %s' % \
                              (reset_token[:32], reset_token[-32:])
        # Mark ID fields as readonly in the form to limit errors
        user_req['ro_fields'] = keyword_auto
        id_query = '%s' % urlencode(user_req)
        req_script = 'req%s.py' % auth_type.replace('mig', '')
        change_pw_url = '%s/cgi-sid/%s?%s' % \
                        (anon_migoid_url, req_script, id_query)
        user_dict['change_pw_url'] = change_pw_url
        user_dict['short_title'] = configuration.short_title
        user_dict['auth_type_name'] = auth_type_name
        user_dict['reset_token_ttl'] = RESET_TOKEN_TTL

        email_to = user_dict['email']
        email_header = '%s %s password reset request for %s' % \
                       (configuration.short_title, auth_type_name, cert_id)
        email_msg = """
*** IMPORTANT: direct replies to this automated message will NOT be read! ***
This is an automatic email in response to an %(auth_type_name)s password reset
request for the %(short_title)s account registered to this email address. You
can change your password within the next %(reset_token_ttl)d seconds by opening
%(change_pw_url)s
in a web browser and choosing a new password in the resulting semi-filled
account update form. 
"""
        email_msg += """
In case you did NOT request a %s password reset or if you just changed your
mind about it you can safely just ignore this message.
""" % auth_type_name
        email_msg = email_msg % user_dict

        logger.info('Sending email: to: %s, header: %s, msg: %s, smtp_server: %s'
                    % (email_to, email_header, email_msg, smtp_server))
        if not send_email(email_to, email_header, email_msg, logger,
                          configuration):
            output_objects.append({'object_type': 'error_text', 'text':
                                   """An error occurred trying to send the email
for an account %s password reset request. Please contact %s site support at %s
if this problem persists.""" % (auth_type_name, configuration.short_title,
                                       configuration.support_email)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

    if not hits:
        # NOTE: only log failed lookups without user output to prevent probing
        logger.warning("no local users matched %r" % cert_id)

    output_objects.append(
        {'object_type': 'text', 'text': """
Account password reset information sent to the owner of the account identified
by %r - if any such account exists.
If you are the account owner you should receive an email shortly with a link
to reset your %s password on %s. Please make sure to also check spam filters
if it doesn't show up.""" % (cert_id, auth_type_name,
                             configuration.short_title)})
    output_objects.append(
        {'object_type': 'link', 'destination': 'javascript:history.back();',
         'class': 'genericbutton', 'text': "Back"})
    return (output_objects, status)
