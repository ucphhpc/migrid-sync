#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# functional - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

# -*- coding: iso-8859-1 -*-

"""This module contains general functions used by the modules in
the functionality dir.
"""

from shared.safeinput import validated_input, valid_user_path, \
    REJECT_UNSET
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

    # always allow output_format, we dont want to use unnecesary
    # lines in all scripts to specify this

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
    ):
    """A wrapper used by most back end functionality"""

    if not is_user(client_id, configuration.user_home):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Invalid certificate or no such MiG user (distinguished name)'
                              })
        return (False, output_objects)
    (status, retval) = validate_input(user_arguments_dict, defaults,
            output_objects, allow_rejects)
    return (status, retval)


