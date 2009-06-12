#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# updateresconfig - [insert a few words of module description on this line]
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

import shared.confparser as confparser
from shared.findtype import is_owner
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET,
                'resconfig': REJECT_UNSET}
    return ['text', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
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
    resconfig = accepted['resconfig'][-1]

    output_objects.append({'object_type': 'header', 'text'
                          : 'Trying to Update resource configuration'})

    if not is_owner(cert_name_no_spaces, unique_resource_name,
                    configuration.resource_home, logger):
        logger.error(cert_name_no_spaces + ' is not an owner of '
                      + unique_resource_name + ': update rejected!')
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'You must be an owner of '
                               + unique_resource_name
                               + ' to update the configuration!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # TODO: race if two confs are uploaded concurrently!

    tmp_path = configuration.resource_home + os.sep\
         + unique_resource_name + os.sep + 'config.tmp'

    # write new proposed config file to disk

    try:
        fh = open(tmp_path, 'w')
        fh.write(resconfig)
        fh.close()
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'File: %s was not written! %s'
                               % (tmp_path, err)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    (status, msg) = confparser.run(tmp_path, unique_resource_name)
    if not status:

        # leave existing config alone

        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    accepted_path = configuration.resource_home + os.sep\
         + unique_resource_name + os.sep + 'config.MiG'

    # truncate old conf with new accepted file

    try:
        os.rename(tmp_path, accepted_path)
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Accepted config, but failed to save it! %s'
                               % err})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # everything ok

    output_objects.append({'object_type': 'text', 'text': 'Success: %s'
                           % msg})
    return (output_objects, returnvalues.OK)


