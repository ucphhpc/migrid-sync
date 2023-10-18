#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# lsresowners - simple list of resource owners for a resource with access
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

"""List all CNs in the list of administrators for a given resource if user is
an owner.
"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.findtype import is_owner
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.init import initialize_main_variables
from mig.shared.listhandling import list_items_in_pickled_list


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET}
    return ['list', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)

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

    unique_resource_name = accepted['unique_resource_name'][-1]

    if not is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Only owners of %s can get the list of owners!''' %
             unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # is_owner incorporates unique_resource_name verification - no need to
    # specifically check for illegal directory traversal

    base_dir = os.path.abspath(os.path.join(configuration.resource_home,
                                            unique_resource_name)) + os.sep
    owners_file = os.path.join(base_dir, 'owners')

    (list_status, msg) = list_items_in_pickled_list(owners_file, logger)
    if not list_status:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Could not get list of owners, reason: %s' % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'list', 'list': msg})
    return (output_objects, returnvalues.OK)
