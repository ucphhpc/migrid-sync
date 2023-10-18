#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# updateresconfig - save updated resource configuration
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

"""Update resource configuration"""

from __future__ import absolute_import

import os

from mig.shared import confparser
from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.fileio import write_file
from mig.shared.findtype import is_owner
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables
from mig.shared.resource import update_resource


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET,
                'resconfig': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
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
    resconfig = accepted['resconfig'][-1]

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'header', 'text':
                           'Trying to Update resource configuration'})

    if not is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):
        logger.error('%s is not an owner of %s: update rejected!' %
                     (client_id, unique_resource_name))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Only owners of %s can update the configuration!' %
             unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # TODO: race if two confs are uploaded concurrently!

    host_url, host_identifier = unique_resource_name.rsplit('.', 1)
    pending_file = os.path.join(configuration.resource_home,
                                unique_resource_name, 'config.tmp')

    # write new proposed config file to disk
    logger.info('write res conf to file: %s' % pending_file)
    if not write_file(resconfig, pending_file, logger):
        output_objects.append({'object_type': 'error_text', 'text':
                               'Could not write resource configuration!'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    (update_status, msg) = update_resource(configuration, client_id,
                                           host_url, host_identifier,
                                           pending_file)
    if not update_status:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Resource update failed:'})
        output_objects.append({'object_type': 'html_form', 'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'text', 'text':
                           'Updated %s resource configuration!' %
                           unique_resource_name})
    output_objects.append({'object_type': 'link', 'text':
                           'Manage resource', 'destination':
                           'resadmin.py?unique_resource_name=%s' %
                           unique_resource_name
                           })
    return (output_objects, returnvalues.OK)
