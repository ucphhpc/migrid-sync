#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# functional - functionality backend helpers
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

import os

# REJECT_UNSET is not used directly but exposed to functionality

from shared.base import requested_page, force_utf8
from shared.defaults import csrf_field
from shared.findtype import is_user
from shared.httpsclient import extract_client_cert, extract_client_openid
from shared.safeinput import validated_input, REJECT_UNSET
from shared.useradm import expire_oid_sessions

def warn_on_rejects(rejects, output_objects):
    """Helper to fill in output_objects in case of rejects"""
    if rejects:
        for (key, err_list) in rejects.items():
            for err in err_list:
                output_objects.append({'object_type': 'error_text',
                        'text': 'input parsing error: %s: %s: %s'
                         % (key, force_utf8(err[0]), force_utf8(err[1]))})


def merge_defaults(user_input, defaults):
    """Merge default values from defaults dict into user_input so
    that any missing fields get the default value and the rest
    remain untouched.
    """

    for (key, val) in defaults.items():
        if not user_input.has_key(key):
            user_input[key] = val


def prefilter_input(user_arguments_dict, prefilter_map):
    """Apply filters from filter_map to user_arguments_dict values inline"""
    for (key, prefilter) in prefilter_map.items():
        if user_arguments_dict.has_key(key):
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
    ):
    """A wrapper used by most back end functionality"""

    # always allow output_format, csrf_field and underscore cache-prevention
    # dummy - we don't want redundant lines in all scripts for that.
    # NOTE: use AllowMe to avoid input validation errors from e.g. underscore

    defaults['output_format'] = ['AllowMe']
    defaults[csrf_field] = ['AllowMe']
    defaults['_'] = ['AllowMe']
    if prefilter_map:
        prefilter_input(user_arguments_dict, prefilter_map)
    (accepted, rejected) = validated_input(user_arguments_dict,
            defaults)
    warn_on_rejects(rejected, output_objects)
    if rejected.keys() and not allow_rejects:
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Input arguments were rejected - not allowed for this script!'
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
    ):
    """A wrapper used by most back end functionality - redirects to sign up
    if client_id is missing.
    """

    logger = configuration.logger
    if environ is None:
        environ = os.environ
    creds_error = ''
    if not client_id:
        creds_error = "Invalid or missing user credentials"
    elif require_user and not is_user(client_id, configuration.mig_server_home):
        creds_error = "No such user (%s)" % client_id

    if creds_error and not requested_page().endswith('logout.py'):
        output_objects.append({'object_type': 'error_text', 'text'
                              : creds_error
                              })

        if configuration.site_enable_gdp:
            main_url = configuration.migserver_http_url
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
                output_objects.append({'object_type': 'link', 'text': signup_url,
                                       'destination': signup_url + signup_query})
                output_objects.append(
                    {'object_type': 'text', 'text': '''If you already signed up and
    received a user certificate you probably just need to import it in your
    browser.'''})
            else:
                output_objects.append(
                    {'object_type': 'text', 'text': '''Apparently you already have
    suitable credentials and just need to sign up for a local %s account on:''' % \
                     configuration.short_title})

                if extract_client_cert(configuration, environ) is None:
                    # Force logout/expire session cookie here to support signup
                    (oid_db, identity) = extract_client_openid(configuration,
                                                               environ,
                                                               lookup_dn=False)
                    if oid_db and identity:
                        logger.info("expire openid user %s in %s" % (identity,
                                                                     oid_db))
                        (success, _) = expire_oid_sessions(configuration, oid_db,
                                                           identity)
                    else:
                        logger.info("no openid user logged in")
                 
                output_objects.append({'object_type': 'link', 'text': signup_url,
                                       'destination': signup_url + signup_query})
        return (False, output_objects)

    (status, retval) = validate_input(user_arguments_dict, defaults,
            output_objects, allow_rejects, filter_values)

    return (status, retval)
