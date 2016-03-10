#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridsettings - save vgrid settings
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

"""Save settings for a given vgrid"""

import os

from shared.defaults import keyword_owners, keyword_members, keyword_all
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
     vgrid_set_settings
import shared.returnvalues as returnvalues

_valid_visible = (keyword_owners, keyword_members, keyword_all)

def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'description': [''],
                'visible_owners': [keyword_owners],
                'visible_members': [keyword_owners],
                'visible_resources': [keyword_owners],
                'request_recipients': ['42'],
                'read_only': ['False'],
                'hidden': ['False'],
                }
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Save settings for %s' % \
                           configuration.site_vgrid_label})
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

    vgrid_name = accepted['vgrid_name'][-1].strip()
    description = accepted['description'][-1].strip()
    visible_owners = accepted['visible_owners'][-1]
    visible_members = accepted['visible_members'][-1]
    visible_resources = accepted['visible_resources'][-1]
    request_recipients = accepted['request_recipients'][-1]
    read_only = accepted['read_only'][-1]
    hidden = accepted['hidden'][-1]

    # Check value sanity and set conservative defaults
    
    if not visible_owners in _valid_visible:
        visible_owners = keyword_owners
    if not visible_members in _valid_visible:
        visible_members = keyword_owners
    if not visible_resources in _valid_visible:
        visible_resources = keyword_owners
    try:
        request_recipients_val = int(request_recipients)
    except ValueError:
        request_recipients_val = 42

    is_read_only = False
    if read_only.lower() in ("true", "1", "yes"):
        # TODO: ennable when we support read-only
        #is_read_only = True
        msg = 'read-only option is not yet supported'
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)
    is_hidden = False
    if hidden.lower() in ("true", "1", "yes"):
        is_hidden = True

    vgrid_settings = {'vgrid_name': vgrid_name,
                      'description': description,
                      'visible_owners': visible_owners,
                      'visible_members': visible_members,
                      'visible_resources': visible_resources,
                      'request_recipients': request_recipients_val,
                      'read_only': is_read_only,
                      'hidden': is_hidden,
                      }
    
    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, client_id,
                                  vgrid_settings.items(), 'settings',
                                  configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif msg:

        # In case of warnings, msg is non-empty while ret_val remains True

        output_objects.append({'object_type': 'warning', 'text': msg})


    # format as list of tuples to fit usual form and then pickle

    (set_status, set_msg) = vgrid_set_settings(configuration, vgrid_name,
                                                vgrid_settings.items())
    if not set_status:
        output_objects.append({'object_type': 'error_text', 'text': '%s'
                               % set_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : 'Settings saved for %s %s!'
                           % (vgrid_name, configuration.site_vgrid_label)})
    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)
