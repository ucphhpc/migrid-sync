#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addvgridres - [insert a few words of module description on this line]
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

import os

from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_resource, \
     vgrid_list_subvgrids, vgrid_add_resources
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'unique_resource_name': REJECT_UNSET}
    return ['', defaults]


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

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    vgrid_name = accepted['vgrid_name'][-1]
    unique_resource_name = accepted['unique_resource_name'][-1].lower()

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, client_id,
                                  unique_resource_name, 'resource',
                                  configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif msg:

        # In case of warnings, msg is non-empty while ret_val remains True

        output_objects.append({'object_type': 'warning', 'text': msg})

    # don't add if already in vgrid or parent vgrid

    if vgrid_is_resource(vgrid_name, unique_resource_name,
                         configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is already a resource in the vgrid'
                               % unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't add if already in subvgrid

    (status, subvgrids) = vgrid_list_subvgrids(vgrid_name,
            configuration)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting list of subvgrids: %s'
                               % subvgrids})
        return (output_objects, returnvalues.SYSTEM_ERROR)
    for subvgrid in subvgrids:
        if vgrid_is_resource(subvgrid, unique_resource_name,
                             configuration):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '%s is already in a sub-vgrid (%s). Remove the resource from the subvgrid and try again'
                                   % (unique_resource_name, subvgrid)})
            return (output_objects, returnvalues.CLIENT_ERROR)

    base_dir = os.path.abspath(configuration.vgrid_home + os.sep
                                + vgrid_name) + os.sep
    resources_file = base_dir + 'resources'

    # Add to list and pickle

    (add_status, add_msg) = vgrid_add_resources(configuration, vgrid_name,
                                                [unique_resource_name])
    if not add_status:
        output_objects.append({'object_type': 'error_text', 'text': '%s'
                               % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : 'New resource %s successfully added to %s vgrid!'
                           % (unique_resource_name, vgrid_name)})
    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)


