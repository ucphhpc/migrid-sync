#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# functional - [insert a few words of module description on this line]
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

"""This module contains general functions used by the modules in
the functionality dir.
"""

import os

# REJECT_UNSET is not used directly but exposed to functionality

from shared.safeinput import validated_input, valid_user_path, \
     html_escape, REJECT_UNSET
from shared.findtype import is_user

def warn_on_rejects(rejects, output_objects):
    if rejects:
        for (key, err_list) in rejects.items():
            for err in err_list:
                output_objects.append({'object_type': 'error_text',
                        'text': 'input parsing error: %s: %s: %s'
                         % (key, err[0], err[1])})


def merge_defaults(user_input, defaults):
    """Merge default values from defaults dict into user_input so
    that any missing fields get the default value and the rest
    remain untouched.
    """

    for (key, val) in defaults.items():
        if not user_input.has_key(key):
            user_input[key] = val


def validate_input(
    user_arguments_dict,
    defaults,
    output_objects,
    allow_rejects,
    ):
    """A wrapper used by most back end functionality"""

    # always allow output_format, we don't want to use
    # unnecessary lines in all scripts to specify this

    defaults['output_format'] = ['allow_me']
    (accepted, rejected) = validated_input(user_arguments_dict,
            defaults)
    warn_on_rejects(rejected, output_objects)
    if len(rejected.keys()) > 0:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Input arguments were rejected - not allowed for this script!'
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
    ):
    """A wrapper used by most back end functionality"""
    
    cert_error = ''
    if not client_id:
        cert_error = "Invalid or missing user certificate"
    elif require_user and not is_user(client_id, configuration.user_home):
        cert_error = "No such user (%s)" % html_escape(client_id)

    if cert_error:
        output_objects.append({'object_type': 'error_text', 'text'
                              : cert_error
                              })

        # Redirect to req or ext cert page with suitable certificate requirement
        # but without changing access method (CGI vs. WSGI).

        certreq_url = os.environ['REQUEST_URI'].replace('-bin', '-sid')
        certreq_url = os.path.join(os.path.dirname(certreq_url), 'reqcert.py')
        extcert_url = os.environ['REQUEST_URI'].replace('-sid', '-bin')
        extcert_url = os.path.join(os.path.dirname(extcert_url), 'extcert.py')

        certreq_link = {'object_type': 'link', 'destination': certreq_url,
                        'text': 'Request a new user certificate'}
        extcert_link = {'object_type': 'link', 'destination': extcert_url,
                        'text': 'Sign up with existing certificate'}
        if not client_id:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'Apparently you do not have a suitable user certificate, but you can request one:'
                                  })
            output_objects.append(certreq_link)
            output_objects.append({'object_type': 'text', 'text'
                                  : 'However, if you own a suitable certificate you can sign up with it:'
                                  })
            output_objects.append(extcert_link)
        else:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'Apparently you already have a suitable certificate you can sign up with:'
                                  })
            output_objects.append(extcert_link)
            output_objects.append({'object_type': 'text', 'text'
                                  : 'However, you can still request a dedicated user certificate if you prefer:'
                                  })
            output_objects.append(certreq_link)

        output_objects.append({'object_type': 'text', 'text'
                              : 'If you already received a user certificate you probably just need to import it in your browser.'
                              })
        output_objects.append({'object_type': 'text', 'text': ''})
        return (False, output_objects)
    (status, retval) = validate_input(user_arguments_dict, defaults,
            output_objects, allow_rejects)

    return (status, retval)
