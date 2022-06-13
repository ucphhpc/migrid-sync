#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# functional - functionality backend helpers
# Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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

"""This module contains general functions used by the modules in
the functionality dir.
"""

from __future__ import absolute_import

from past.builtins import basestring
import os
import time

# REJECT_UNSET is not used directly but exposed to functionality

from mig.shared.accountstate import check_account_status, \
    check_update_account_expire
from mig.shared.base import requested_page, force_native_str, get_site_base_url
from mig.shared.defaults import csrf_field, auth_openid_ext_db
from mig.shared.findtype import is_user
from mig.shared.httpsclient import extract_client_cert, extract_client_openid, \
    extract_base_url
from mig.shared.init import find_entry, make_title_entry, make_header_entry
from mig.shared.safeinput import validated_input, REJECT_UNSET
from mig.shared.useradm import expire_oid_sessions


def warn_on_rejects(rejects, output_objects):
    """Helper to fill in output_objects in case of rejects"""
    if rejects:
        for (key, err_list) in rejects.items():
            for err in err_list:
                output_objects.append({'object_type': 'error_text',
                                       'text': 'input parsing error: %s: %s: %s'
                                       % (key, force_native_str(err[0]),
                                          force_native_str(err[1]))})


def merge_defaults(user_input, defaults):
    """Merge default values from defaults dict into user_input so
    that any missing fields get the default value and the rest
    remain untouched.
    """

    for (key, val) in defaults.items():
        if key not in user_input:
            user_input[key] = val


def prefilter_input(user_arguments_dict, prefilter_map):
    """Apply filters from filter_map to user_arguments_dict values inline"""
    for (key, prefilter) in prefilter_map.items():
        if key in user_arguments_dict:
            orig = user_arguments_dict[key]
            if isinstance(orig, basestring):
                res = prefilter(orig)
            else:
                res = [prefilter(i) for i in orig]
            user_arguments_dict[key] = res


def validate_input(
    user_arguments_dict,
    defaults,
    output_objects,
    allow_rejects,
    prefilter_map=None,
    typecheck_overrides={}
):
    """A wrapper used by most back end functionality.
    The optional typecheck_overrides argument can be passed a dictionary of
    input variable names and their validator function if needed. This is
    particularly useful in relation to overriding the default simple path value
    checks in cases where a path pattern with wildcards is allowed.
    We want all such exceptions to be explicit to avoid opening up by mistake.
    """

    # always allow output_format, csrf_field, stray modauthopenid nonces and
    # underscore cache-prevention dummy - we don't want redundant lines in all
    # scripts for that.
    # NOTE: use AllowMe to avoid input validation errors from e.g. underscore

    defaults['output_format'] = ['AllowMe']
    defaults[csrf_field] = ['AllowMe']
    # This sometimes appears from modauthopenid and would otherwise cause e.g.
    # input parsing error: modauthopenid.nonce: YDHZzoBtgI: unexpected field
    defaults['modauthopenid.nonce'] = ['AllowMe']
    defaults['_'] = ['AllowMe']
    if prefilter_map:
        prefilter_input(user_arguments_dict, prefilter_map)
    (accepted, rejected) = validated_input(user_arguments_dict,
                                           defaults,
                                           type_override=typecheck_overrides)
    warn_on_rejects(rejected, output_objects)
    if rejected and not allow_rejects:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Input arguments were rejected - not allowed for this script!'
             })
        output_objects.append(
            {'object_type': 'link', 'text': 'Go back to try again',
             'destination': 'javascript:history.back();',
             })
        return (False, output_objects)
    return (True, accepted)


def validate_input_and_cert(
    user_arguments_dict,
    defaults,
    output_objects,
    client_id,
    configuration,
    allow_rejects,
    require_user=True,
    filter_values=None,
    environ=None,
    typecheck_overrides={},
):
    """A wrapper used by most back end functionality - redirects to sign up
    if client_id is missing.
    The optional typecheck_overrides dictionary is passed directly to the base
    validate_input and can be used to loosen input validation. Please refer to
    the validate_input doc. 
    """

    logger = configuration.logger
    if environ is None:
        environ = os.environ
    creds_error = ''
    pending_expire, account_expire = True, 0
    account_accessible, account_status = True, 'active'
    user_dict = None
    if not client_id:
        creds_error = "Invalid or missing user credentials"
    elif not is_user(client_id, configuration):
        if require_user:
            creds_error = "No such user (%s)" % client_id
    else:
        (account_accessible, account_status, _) = check_account_status(
            configuration, client_id)
        # logger.debug("account status said %s , %s" %
        #             (account_accessible, account_status))
        if not account_accessible:
            creds_error = "User account is %s!" % account_status
        else:
            # Attempt auto renew if past or close to the time account expires
            (pending_expire, account_expire, _) = check_update_account_expire(
                configuration, client_id, environ)
            if not pending_expire:
                creds_error = "User account expired!"

    # NOTE: users with a certificate but without an account can use extcert.
    #       Expired users can still log out or use their login to access the
    #       (unprivileged) account request pages to renew their account with
    #       auto-fill of fields.
    if creds_error and not os.path.basename(requested_page()) in \
            ['logout.py', 'autologout.py', 'reqoid.py', 'reqcert.py',
             'extcert.py']:
        # Simple init to get page preamble even where initialize_main_variables
        # was called with most things disabled because no or limited direct
        # output was expected.
        title = find_entry(output_objects, 'title')
        if not title:
            output_objects.append(make_title_entry(
                'Account Error', skipmenu=True, skipwidgets=True,
                skipuserstyle=True, skipuserprofile=True))
        else:
            title['text'] = 'Account Error'
        output_objects.append(make_header_entry('Account Error'))

        output_objects.append({'object_type': 'error_text', 'text': creds_error
                               })

        if configuration.site_enable_gdp:
            main_url = get_site_base_url(configuration)
            output_objects.append(
                {'object_type': 'text', 'text': '''Apparently you do not
                        have access to this page, please return to:'''})

            output_objects.append({'object_type': 'link', 'text': main_url,
                                   'destination': main_url})
        else:
            # Redirect to sign-up cert page trying to guess relevant choices

            signup_url = os.path.join(configuration.migserver_https_sid_url,
                                      'cgi-sid', 'signup.py')
            signup_query = ''

            if not client_id:
                output_objects.append(
                    {'object_type': 'text', 'text': '''Apparently you do not
    already have access to %s, but you can sign up:''' % configuration.short_title
                     })
                output_objects.append({'object_type': 'link', 'text':
                                       '%s sign up page' %
                                       configuration.short_title,
                                       'destination': signup_url + signup_query})
                output_objects.append(
                    {'object_type': 'text', 'text': '''If you already signed up and
    received a user certificate you probably just need to import it in your
    browser.'''})
            else:
                if not account_accessible:
                    output_objects.append(
                        {'object_type': 'text', 'text':
                         '''Please contact the %s admins about access: %s''' %
                         (configuration.short_title,
                          configuration.admin_email)})
                elif not pending_expire:
                    output_objects.append(
                        {'object_type': 'text', 'text':
                         '''You probably just need to renew %s account access
by repeating the steps on the''' % configuration.short_title})
                else:
                    output_objects.append(
                        {'object_type': 'text', 'text':
                         '''Apparently you already have suitable credentials
and just need to sign up for a local %s account on the''' %
                         configuration.short_title})

                base_url = extract_base_url(configuration, environ)
                if base_url == configuration.migserver_https_ext_cert_url and \
                        'extcert' in configuration.site_login_methods:
                    signup_query = '?show=extcert'
                elif base_url in (configuration.migserver_https_ext_oid_url,
                                  configuration.migserver_https_mig_oid_url):
                    # Force logout/expire session cookie here to support signup
                    (oid_db, identity) = extract_client_openid(configuration,
                                                               environ,
                                                               lookup_dn=False)
                    if oid_db and identity:
                        logger.info("openid expire user %s in %s" % (identity,
                                                                     oid_db))
                        (success, _) = expire_oid_sessions(configuration, oid_db,
                                                           identity)
                        if oid_db == auth_openid_ext_db and \
                                'extoid' in configuration.site_signup_methods:
                            signup_query = '?show=extoid'
                        else:
                            logger.error("unknown migoid client_id %s on %s"
                                         % ([client_id], base_url))
                else:
                    logger.warning("unexpected client_id %s on %s" %
                                   (client_id, base_url))

                output_objects.append({'object_type': 'link', 'text':
                                       '%s sign up page' %
                                       configuration.short_title,
                                       'destination':
                                       signup_url + signup_query})
        return (False, output_objects)

    (status, retval) = validate_input(user_arguments_dict, defaults,
                                      output_objects, allow_rejects,
                                      filter_values,
                                      typecheck_overrides=typecheck_overrides)

    return (status, retval)
