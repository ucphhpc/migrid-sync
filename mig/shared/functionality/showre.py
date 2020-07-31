#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showre - Display a runtime environment
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Get info about a runtime environtment"""
from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.base import valid_dir_input
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.refunctions import is_runtime_environment, get_re_dict, \
    build_reitem_object
from mig.shared.vgridaccess import resources_using_re


def signature():
    """Signature of the main function"""

    defaults = {'re_name': REJECT_UNSET}
    return ['runtimeenvironment', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Show Runtime Environment Details'
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
    re_name = accepted['re_name'][-1]

    output_objects.append(
        {'object_type': 'header', 'text': 'Show runtime environment details'})

    if not valid_dir_input(configuration.re_home, re_name):
        logger.warning(
            "possible illegal directory traversal attempt re_name '%s'"
            % re_name)
        output_objects.append({'object_type': 'error_text', 'text': 'Illegal runtime environment name: "%s"'
                               % re_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not is_runtime_environment(re_name, configuration):
        output_objects.append({'object_type': 'error_text', 'text': "'%s' is not an existing runtime environment!"
                               % re_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Runtime environment details'

    (re_dict, msg) = get_re_dict(re_name, configuration)
    if not re_dict:
        output_objects.append(
            {'object_type': 'error_text', 'text': 'Could not read details for "%s"' % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Set providers explicitly after build_reitem_object to avoid import loop
    re_item = build_reitem_object(configuration, re_dict)
    re_name = re_item['name']
    re_item['providers'] = resources_using_re(configuration, re_name)
    re_item['resource_count'] = len(re_item['providers'])

    output_objects.append(re_item)

    return (output_objects, returnvalues.OK)
