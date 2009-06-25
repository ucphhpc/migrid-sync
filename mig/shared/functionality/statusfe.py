#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# statusfe - [insert a few words of module description on this line]
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

""" Get frontend status """

import os
import sys
import cgitb
cgitb.enable()

from shared.findtype import is_owner
from shared.resadm import status_resource
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()

    output_objects.append({'object_type': 'text', 'text'
                          : '--------- Trying to get STATUS for frontend ----------'
                          })

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

    logger.info('%s attempts to get status for frontend at %s',
                client_id, unique_resource_name)

    if not is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'You must be an owner of '
                               + unique_resource_name
                               + ' to get status for the resource frontend!'
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    (status, msg) = status_resource(unique_resource_name,
                                    configuration.resource_home, logger)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s. Error getting resource status.'
                               % msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # everything ok

    output_objects.append({'object_type': 'text', 'text': '%s' % msg})
    return (output_objects, returnvalues.OK)


