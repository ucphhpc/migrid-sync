#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmresowner - [insert a few words of module description on this line]
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

"""Add a CN to the list of administrators for a given resource. The CN is
not required to be that of an existing MiG user.
"""

import os
import sys

from shared.validstring import cert_name_format
from shared.listhandling import remove_item_from_pickled_list
from shared.findtype import is_user, is_owner
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""
    defaults = {'unique_resource_name': REJECT_UNSET,
                'cert_name': REJECT_UNSET}
    return ['text', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()

    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        cert_name_no_spaces,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    unique_resource_name = accepted['unique_resource_name'][-1]
    cert_name = accepted['cert_name'][-1]
    cert_name = cert_name_format(cert_name)

    if not is_owner(cert_name_no_spaces, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'You must be an owner of %s to remove another owner!'
                               % unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # is_owner incorporates unique_resource_name verification - no need to
    # specifically check for illegal directory traversal

    if not is_user(cert_name, configuration.user_home):
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is not a valid MiG user!'
                               % cert_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    base_dir = os.path.abspath(configuration.resource_home + os.sep
                                + unique_resource_name) + os.sep

    # Add owner

    owners_file = base_dir + 'owners'
    (status, msg) = remove_item_from_pickled_list(owners_file,
            cert_name, logger, False)

    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not remove owner, reason: %s'
                               % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : '%s was successfully removed and is no longer an owner of %s!'
                           % (cert_name, unique_resource_name)})
    return (output_objects, returnvalues.OK)


