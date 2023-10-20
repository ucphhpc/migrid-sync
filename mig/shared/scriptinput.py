#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# scriptinput - Handles html form style input from user
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

"""This module contains CGI/WSGI/... specific functions for
handling user input.
"""

from __future__ import print_function
from __future__ import absolute_import

# Expose some safeinput functions here, too

from mig.shared.safeinput import validated_boolean, validated_string, \
    validated_path, validated_fqdn, validated_commonname, \
    validated_integer, validated_job_id, html_escape
from mig.shared.safeinput import InputException as CgiInputException


def parse_input(user_arguments_dict, fields):
    """A user input parser"""

    parsed_input = {}
    error = ''
    for (name, settings) in fields.items():
        parsed_entry = {}
        if 'kind' not in settings:
            error += 'missing kind for %s in parse_input!\n' % name
            continue

        kind = settings['kind']
        if 'first' == kind:
            if 'default' in settings:
                try:
                    parsed_entry['raw'] = user_arguments_dict[name][0]
                except:
                    parsed_entry['raw'] = settings['default']
            else:
                parsed_entry['raw'] = user_arguments_dict[name][0]
        elif 'last' == kind:
            if 'default' in settings:
                try:
                    parsed_entry['raw'] = \
                        user_arguments_dict[name][len(user_arguments_dict[name])
                                                  - 1]
                except:
                    parsed_entry['raw'] = settings['default']
            else:
                parsed_entry['raw'] = \
                    user_arguments_dict[name][len(user_arguments_dict[name])
                                              - 1]
        elif 'list' == kind:
            if 'default' in settings:
                try:
                    parsed_entry['raw'] = user_arguments_dict[name]
                except:
                    parsed_entry['raw'] = settings['default']
            else:
                parsed_entry['raw'] = user_arguments_dict[name]
        else:
            error += 'unknown kind %s for %s in parse_input!' % (kind,
                                                                 name)
            continue

        # Check that input is valid

        if 'check' not in settings:
            error += 'missing check for %s in parse_input!' % name
            continue

        check = settings['check']
        try:
            check(parsed_entry['raw'])
        except ValueError as verr:
            error += 'invalid contents of %s in parse_input! (%s)'\
                % (name, verr)
            continue

        # Finally add to parsed input dictionary if we got this far

        parsed_input[name] = parsed_entry

    return (parsed_input, error)


def parse_argument(
    user_arguments_dict,
    name,
    kind,
    check,
    required=False,
    default=-1,
):
    """Parse user_arguments_dict for argument(s) with supplied name. The kind
    string defines which strategy to use in the value extraction (select
    first, last or list of all). If required is true, the parse will
    return an error if no such argument is found. The check argument must
    be a function that verifies the contents. If a default string is
    supplied it will be used in case no such argument is found.

    The result is a 3-tuple of raw data, html escaped data and an error
    string. An empty error string means success.
    """

    error = ''
    raw = ''

    if required and name not in user_arguments_dict:
        error = '%s argument required but not found!' % name
        return ('', '', error)

    if 'first' == kind:
        raw = user_arguments_dict[name][0]
    elif 'last' == kind:
        raw = user_arguments_dict[name][len(user_arguments_dict[name]
                                            - 1)]
    elif 'list' == kind:
        raw = user_arguments_dict[name]
    else:
        error = 'unknown kind %s for %s in parse_argument!' % (kind,
                                                               name)
        return ('', '', error)

    try:
        check(raw)
    except ValueError as verr:
        error = 'invalid contents of %s in parse_argument! (%s)'\
            % (name, verr)

    if 'list' == kind:
        safe = [html_escape(item) for item in raw]
    else:
        safe = html_escape(raw)
    return (raw, safe, error)


def fieldstorage_to_dict(fieldstorage, fields=[]):
    """Get a plain dictionary, rather than the '.value' system used by
    the cgi module. Please note that all values are on list form even
    if only a single value is provided.
    If the fields list is provided, only the provided fields are read.
    This may be necessary in PUT requests where fieldstorage key listing is
    not supported.
    """

    params = {}
    if not fields and fieldstorage:
        fields = list(fieldstorage)
    for key in fields:
        try:
            params[key] = fieldstorage.getlist(key)

            # Upload forms store the filename in a special way, fetch it
            # if available!
            # do not overwrite

            filename_key = key + 'filename'
            if filename_key not in params:
                try:
                    if fieldstorage[key].filename is not None:
                        params[filename_key] = \
                            fieldstorage[key].filename
                except Exception as exc:
                    pass
        except Exception as err:
            print('Warning: failed to extract values for %s: %s'
                  % (key, err))
    return params
