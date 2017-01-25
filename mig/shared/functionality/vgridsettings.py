#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridsettings - save vgrid settings
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

from shared.defaults import keyword_owners, keyword_members, keyword_all, \
     keyword_auto, default_vgrid_settings_limit
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables
from shared.vgrid import init_vgrid_script_add_rem, allow_settings_adm, \
     vgrid_set_settings
import shared.returnvalues as returnvalues

_valid_visible = (keyword_owners, keyword_members, keyword_all)
_valid_sharelink = (keyword_owners, keyword_members)
_keyword_auto_int = '0'

def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'description': [keyword_auto],
                'visible_owners': [keyword_auto],
                'visible_members': [keyword_auto],
                'visible_resources': [keyword_auto],
                'create_sharelink': [keyword_auto],
                'request_recipients': [_keyword_auto_int],
                'restrict_settings_adm': [_keyword_auto_int],
                'restrict_owners_adm': [_keyword_auto_int],
                'restrict_members_adm': [_keyword_auto_int],
                'restrict_resources_adm': [_keyword_auto_int],
                'read_only': [keyword_auto],
                'hidden': [keyword_auto],
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

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    vgrid_name = accepted['vgrid_name'][-1].strip()

    new_settings = {'vgrid_name': vgrid_name}

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, client_id,
                                  new_settings.items(), 'settings',
                                  configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif msg:

        # In case of warnings, msg is non-empty while ret_val remains True

        output_objects.append({'object_type': 'warning', 'text': msg})

    # Check if this owner is allowed to change settings

    (allow_status, allow_msg) = allow_settings_adm(configuration, vgrid_name,
                                                   client_id)
    if not allow_status:
        output_objects.append({'object_type': 'error_text', 'text': allow_msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Build current settings, leaving out unset ones for default/inherit
    if not keyword_auto in accepted['description']:
        new_settings['description'] = '\n'.join(accepted['description']).strip()
    if not keyword_auto in accepted['visible_owners']:
        visible_owners = accepted['visible_owners'][-1]
        if visible_owners in _valid_visible:
            new_settings['visible_owners'] = visible_owners
        else:
            msg = "invalid visible_owners value: %s" % visible_owners
            logger.warning(msg)
            output_objects.append({'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
    if not keyword_auto in accepted['visible_members']:
        visible_members = accepted['visible_members'][-1]
        if visible_members in _valid_visible:
            new_settings['visible_members'] = visible_members
        else:
            msg = "invalid visible_members value: %s" % visible_members
            logger.warning(msg)
            output_objects.append({'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
    if not keyword_auto in accepted['visible_resources']:
        visible_resources = accepted['visible_resources'][-1]
        if visible_resources in _valid_visible:
            new_settings['visible_resources'] = visible_resources
        else:
            msg = "invalid visible_resources value: %s" % visible_resources
            logger.warning(msg)
            output_objects.append({'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
    if not keyword_auto in accepted['create_sharelink']:
        create_sharelink = accepted['create_sharelink'][-1]
        if create_sharelink in _valid_sharelink:
            new_settings['create_sharelink'] = create_sharelink
        else:
            msg = "invalid create_sharelink value: %s" % create_sharelink
            logger.warning(msg)
            output_objects.append({'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
    if not _keyword_auto_int in accepted['request_recipients']:
        try:
            request_recipients = accepted['request_recipients'][-1]
            request_recipients = int(request_recipients)
            new_settings['request_recipients'] = request_recipients
        except ValueError:
            msg = "invalid request_recipients value: %s" % request_recipients
            logger.warning(msg)
            output_objects.append({'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
    if not _keyword_auto_int in accepted['restrict_settings_adm']:
        try:
            restrict_settings_adm = accepted['restrict_settings_adm'][-1]
            restrict_settings_adm = int(restrict_settings_adm)
            new_settings['restrict_settings_adm'] = restrict_settings_adm
        except ValueError:
            msg = "invalid restrict_settings_adm value: %s" % \
                  restrict_settings_adm
            logger.warning(msg)
            output_objects.append({'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
    else:
        restrict_settings_adm = default_vgrid_settings_limit
    if not _keyword_auto_int in accepted['restrict_owners_adm']:
        try:
            restrict_owners_adm = accepted['restrict_owners_adm'][-1]
            restrict_owners_adm = int(restrict_owners_adm)
            new_settings['restrict_owners_adm'] = restrict_owners_adm
        except ValueError:
            msg = "invalid restrict_owners_adm value: %s" % restrict_owners_adm
            logger.warning(msg)
            output_objects.append({'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
    else:
        restrict_owners_adm = default_vgrid_settings_limit
    if not _keyword_auto_int in accepted['restrict_members_adm']:
        try:
            restrict_members_adm = accepted['restrict_members_adm'][-1]
            restrict_members_adm = int(restrict_members_adm)
            new_settings['restrict_members_adm'] = restrict_members_adm
        except ValueError:
            msg = "invalid restrict_members_adm value: %s" % \
                  restrict_members_adm
            logger.warning(msg)
            output_objects.append({'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
    if not _keyword_auto_int in accepted['restrict_resources_adm']:
        try:
            restrict_resources_adm = accepted['restrict_resources_adm'][-1]
            restrict_resources_adm = int(restrict_resources_adm)
            new_settings['restrict_resources_adm'] = restrict_resources_adm
        except ValueError:
            msg = "invalid restrict_resources_adm value: %s" % \
                  restrict_resources_adm
            logger.warning(msg)
            output_objects.append({'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
    if not keyword_auto in accepted['read_only']:
        read_only = accepted['read_only'][-1]
        is_read_only = False
        if read_only.lower() in ("true", "1", "yes"):
            # TODO: enable when we support read-only
            #is_read_only = True
            #new_settings['read_only'] = is_read_only
            msg = 'read-only option is not yet supported'
            output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
            return (output_objects, returnvalues.CLIENT_ERROR)
    if not keyword_auto in accepted['hidden']:
        hidden = accepted['hidden'][-1]
        is_hidden = False
        if hidden.lower() in ("true", "1", "yes"):
            is_hidden = True
        new_settings['hidden'] = is_hidden

    if restrict_settings_adm > restrict_owners_adm:
        output_objects.append({'object_type': 'html_form', 'text': '''
<span class="warningtext">Warning: Restrict owner administration may still be
circumvented by some owners unless Restrict settings administration is set to
a lower or equal number.</span>'''})

    # format as list of tuples to fit usual form and then pickle

    (set_status, set_msg) = vgrid_set_settings(configuration, vgrid_name,
                                               new_settings.items())
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
